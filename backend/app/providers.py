"""Small REST boundary with durable local embedding reuse and conservative reservations."""

import asyncio
import json
import math
import sqlite3
from array import array
from datetime import UTC, datetime
from hashlib import sha256

import httpx

from .retrieval.chunking import token_count


class ProviderError(Exception):
    pass


class BudgetExceeded(Exception):
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

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

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
                "UPDATE calls SET input_tokens=?, output_tokens=?, actual_usd=? WHERE id=?",
                (input_tokens, output_tokens, actual_usd, call),
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
        with self.connect() as db:
            row = db.execute("SELECT vector FROM embeddings WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        vector = array("f")
        vector.frombytes(row[0])
        return list(vector)

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

    async def embed(self, texts):
        async with self.embedding_lock:
            unique = {self.cache_key(text): text for text in texts}
            vectors = {key: self.ledger.cached(key) for key in unique}
            missing = [key for key in unique if vectors[key] is None]
            for start in range(0, len(missing), 64):
                keys = missing[start : start + 64]
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
                        "encoding_format": "float",
                        "input": batch,
                    },
                )
                try:
                    rows = sorted(data["data"], key=lambda row: row["index"])
                    if [row["index"] for row in rows] != list(range(len(keys))):
                        raise ValueError("Invalid embedding indexes")
                    for key, row in zip(keys, rows, strict=True):
                        vector = row["embedding"]
                        if len(vector) != self.settings.embedding_dimensions or not all(
                            isinstance(v, (int, float)) and math.isfinite(v) for v in vector
                        ):
                            raise ValueError("Invalid embedding vector")
                        vectors[key] = vector
                    used = int(data["usage"]["prompt_tokens"])
                    self.ledger.complete(
                        call,
                        used,
                        0,
                        used * self.settings.embedding_usd_per_million / 1e6,
                    )
                    self.ledger.cache([(key, vectors[key]) for key in keys])
                except (KeyError, ValueError, TypeError) as error:
                    raise ProviderError from error
            return [vectors[self.cache_key(text)] for text in texts]

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
        # Schema and protocol overhead included, with a margin. This is an estimate,
        # not a provider-enforced account budget. Keep uncertain reservations charged.
        estimate = int(token_count(json.dumps(body)) * 1.2) + 1024
        call = self.ledger.reserve(
            "generation",
            (
                estimate * self.settings.generation_input_usd_per_million
                + 1200 * self.settings.generation_output_usd_per_million
            )
            / 1e6,
        )
        data = await self.post("responses", body)
        try:
            usage = data["usage"]
            input_tokens, output_tokens = int(usage["input_tokens"]), int(usage["output_tokens"])
            actual = (
                input_tokens * self.settings.generation_input_usd_per_million
                + output_tokens * self.settings.generation_output_usd_per_million
            ) / 1e6
            self.ledger.complete(call, input_tokens, output_tokens, actual)
            if data["status"] != "completed":
                raise ValueError("Incomplete response")
            parts = [
                part["text"]
                for item in data["output"]
                if item.get("type") == "message"
                for part in item["content"]
                if part["type"] == "output_text"
            ]
            if len(parts) != 1:
                raise ValueError("Missing or refused response")
            return json.loads(parts[0]), {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": actual,
                "model": self.settings.generation_model,
            }
        except (KeyError, ValueError, TypeError) as error:
            raise ProviderError from error
