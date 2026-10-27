"""Small REST boundary with durable local embedding reuse and conservative reservations."""

import asyncio
import base64
import json
import math
import sqlite3
from array import array
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from hashlib import sha256

import httpx

from .retrieval.chunking import token_count


class ProviderError(Exception):
    pass


class BudgetExceeded(Exception):
    pass


class ContextLimitExceeded(Exception):
    pass


class UsageLedger:
    def __init__(self, path, ceiling):
        self.path, self.ceiling = path, ceiling
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vector BLOB)")
            db.execute("""CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY, kind TEXT, reserved REAL, created TEXT,
                input_tokens INTEGER, output_tokens INTEGER, actual_usd REAL)""")

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            yield db

    def reserve(self, kind, amount):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            spent = db.execute("SELECT COALESCE(SUM(reserved), 0) FROM calls").fetchone()[0]
            if spent + amount > self.ceiling:
                raise BudgetExceeded
            cursor = db.execute(
                "INSERT INTO calls (kind, reserved, created) VALUES (?, ?, ?)",
                (kind, amount, datetime.now(UTC).isoformat()),
            )
            return cursor.lastrowid

    def complete(self, call, input_tokens, output_tokens, actual_usd):
        with self.connect() as db:
            db.execute(
                "UPDATE calls SET input_tokens=?, output_tokens=?, actual_usd=?, "
                "reserved=MAX(reserved, ?) WHERE id=?",
                (input_tokens, output_tokens, actual_usd, actual_usd, call),
            )

    def summary(self):
        with self.connect() as db:
            row = db.execute("""SELECT COUNT(*), COALESCE(SUM(reserved),0),
                COALESCE(SUM(actual_usd),0), COALESCE(SUM(input_tokens),0),
                COALESCE(SUM(output_tokens),0) FROM calls""").fetchone()
        return dict(
            zip(
                ["calls", "reserved_usd", "estimated_actual_usd", "input_tokens", "output_tokens"],
                row,
                strict=True,
            )
        )

    def cached(self, key):
        return self.cached_many([key]).get(key)

    def cached_many(self, keys):
        result = {}
        keys = list(keys)
        with self.connect() as db:
            for start in range(0, len(keys), 500):
                batch = keys[start : start + 500]
                placeholders = ",".join("?" for _ in batch)
                for key, blob in db.execute(
                    f"SELECT key, vector FROM embeddings WHERE key IN ({placeholders})",
                    batch,
                ):
                    vector = array("f")
                    vector.frombytes(blob)
                    result[key] = list(vector)
        return result

    def cache(self, values):
        with self.connect() as db:
            db.executemany(
                "INSERT OR REPLACE INTO embeddings VALUES (?, ?)",
                [(key, array("f", vector).tobytes()) for key, vector in values],
            )


class OpenAIProvider:
    def __init__(self, client, settings):
        self.client, self.settings = client, settings
        self.ledger = UsageLedger(settings.usage_db, settings.api_budget_usd)
        self.embedding_lock = asyncio.Lock()

    async def post(self, endpoint, body):
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/" + endpoint,
                json=body,
                headers={
                    "Authorization": "Bearer " + self.settings.openai_api_key.get_secret_value()
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            # No automatic retries: a timeout may already have incurred a charge.
            raise ProviderError from error

    def cache_key(self, text):
        identity = f"{self.settings.embedding_model}:{self.settings.embedding_dimensions}:{text}"
        return sha256(identity.encode()).hexdigest()

    async def embed(self, texts, *, include_usage=False):
        async with self.embedding_lock:
            unique = {self.cache_key(text): text for text in texts}
            vectors = self.ledger.cached_many(unique)
            missing = [key for key in unique if key not in vectors]
            input_tokens, api_calls = 0, 0
            for start in range(0, len(missing), 512):
                # Indexed chunks are <=256 tokens: <=131,072 tokens per call,
                # below the documented 300,000 aggregate token limit.
                keys = missing[start : start + 512]
                batch = [unique[key] for key in keys]
                tokens = sum(token_count(text) for text in batch)
                call = self.ledger.reserve(
                    "embedding",
                    tokens * self.settings.embedding_usd_per_million / 1e6,
                )
                data = await self.post(
                    "embeddings",
                    {
                        "model": self.settings.embedding_model,
                        "dimensions": self.settings.embedding_dimensions,
                        "encoding_format": "base64",
                        "input": batch,
                    },
                )
                try:
                    rows = sorted(data["data"], key=lambda row: row["index"])
                    if [row["index"] for row in rows] != list(range(len(keys))):
                        raise ValueError("Invalid embedding indexes")
                    for key, row in zip(keys, rows, strict=True):
                        vector = row["embedding"]
                        if isinstance(vector, str):
                            decoded = array("f")
                            decoded.frombytes(base64.b64decode(vector, validate=True))
                            vector = list(decoded)
                        if len(vector) != self.settings.embedding_dimensions or not all(
                            isinstance(v, (int, float)) and math.isfinite(v) for v in vector
                        ):
                            raise ValueError("Invalid embedding vector")
                        vectors[key] = vector
                    used = int(data["usage"]["prompt_tokens"])
                    input_tokens += used
                    api_calls += 1
                    self.ledger.complete(
                        call,
                        used,
                        0,
                        used * self.settings.embedding_usd_per_million / 1e6,
                    )
                    self.ledger.cache([(key, vectors[key]) for key in keys])
                except (KeyError, ValueError, TypeError) as error:
                    raise ProviderError from error
            result = [vectors[self.cache_key(text)] for text in texts]
            usage = {
                "model": self.settings.embedding_model,
                "input_tokens": input_tokens,
                "api_calls": api_calls,
                "cache_hits": len(unique) - len(missing),
                "estimated_cost_usd": input_tokens * self.settings.embedding_usd_per_million / 1e6,
            }
            return (result, usage) if include_usage else result

    async def generate(self, instructions, context, schema):
        body = {
            "model": self.settings.generation_model,
            "store": False,
            "instructions": instructions,
            "input": context,
            "reasoning": {"effort": "none"},
            "max_output_tokens": 1200,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "investigation",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        data, usage = await self.respond(body, "generation")
        try:
            parts = [
                part["text"]
                for item in data["output"]
                if item.get("type") == "message"
                for part in item["content"]
                if part["type"] == "output_text"
            ]
            if len(parts) != 1:
                raise ValueError("Missing response")
            return json.loads(parts[0]), usage
        except (KeyError, ValueError, TypeError) as error:
            raise ProviderError from error

    async def plan_searches(self, instructions, inputs, tool, *, first_round):
        body = {
            "model": self.settings.generation_model,
            "store": False,
            "instructions": instructions,
            "input": inputs,
            "reasoning": {"effort": "none"},
            "max_output_tokens": 600,
            "tools": [tool],
            "tool_choice": "required",
            "parallel_tool_calls": not first_round,
        }
        return await self.respond(body, "planning", output_only=True)

    async def respond(self, body, kind, *, output_only=False):
        # Schema and protocol overhead included, with a margin. Reservations remain
        # charged on uncertain failures, independently of the number of tool rounds.
        request_tokens = token_count(json.dumps(body, ensure_ascii=False))
        if (
            token_count(json.dumps(body["input"], ensure_ascii=False)) > 8000
            or request_tokens > 12000
        ):
            raise ContextLimitExceeded
        estimate = int(request_tokens * 1.2) + 1024
        call = self.ledger.reserve(
            kind,
            (
                estimate * self.settings.generation_input_usd_per_million
                + body["max_output_tokens"] * self.settings.generation_output_usd_per_million
            )
            / 1e6,
        )
        data = await self.post("responses", body)
        try:
            usage = data["usage"]
            input_tokens, output_tokens = usage["input_tokens"], usage["output_tokens"]
            if any(type(value) is not int or value < 0 for value in (input_tokens, output_tokens)):
                raise ValueError("Invalid usage")
            actual = (
                input_tokens * self.settings.generation_input_usd_per_million
                + output_tokens * self.settings.generation_output_usd_per_million
            ) / 1e6
            self.ledger.complete(call, input_tokens, output_tokens, actual)
            if data["status"] != "completed":
                raise ValueError("Incomplete response")
            output = data["output"]
            if (
                not isinstance(output, list)
                or not output
                or not all(isinstance(item, dict) for item in output)
            ):
                raise ValueError("Missing output")
            for item in output:
                if item.get("type") == "message" and (
                    not isinstance(item.get("content"), list)
                    or not all(isinstance(part, dict) for part in item["content"])
                ):
                    raise ValueError("Malformed message content")
            if any(
                part.get("type") == "refusal"
                for item in output
                if item.get("type") == "message"
                for part in item["content"]
            ):
                raise ValueError("Refused response")
            return (output if output_only else data), {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": actual,
                "model": self.settings.generation_model,
            }
        except (KeyError, ValueError, TypeError) as error:
            raise ProviderError from error
