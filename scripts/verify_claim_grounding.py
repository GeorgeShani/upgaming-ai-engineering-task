"""Paid development regressions: synthetic draft review, then real development retrieval.

Never reads final fixtures. Writes a pending receipt BEFORE each paid attempt; existing
receipts stop a rerun, including failed/interrupted attempts. Expected outcomes stay local.
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path.cwd() / "backend"))
from app.config import Settings
from app.evaluation.runner import guard_budget
from app.investigations.models import AnswerDraft, validate_evidence
from app.investigations.verification import INSTRUCTIONS, Review, apply_review, review_context
from app.main import create_app
from app.providers import OpenAIProvider, UsageLedger
from fastapi.testclient import TestClient


def synthetic_cases():
    ages = ["Arden was born in 1986.", "Bryn was born in 1972."]
    return [
        ("reversed-age", "Who is older, Arden or Bryn?", "Arden is older than Bryn.", ages, False),
        ("correct-age", "Who is older, Arden or Bryn?", "Bryn is older than Arden.", ages, True),
        (
            "wrong-entity",
            "What is Luma's population?",
            "Luma has 82 million residents.",
            ["Luma has 14 million residents. Neris has 82 million residents."],
            False,
        ),
        (
            "wrong-band",
            "Where did Silver Pier originate?",
            "Silver Pier originated in Luma.",
            ["The band Copper Field originated in Luma."],
            False,
        ),
        (
            "missing-premise",
            "Are Arden and Bryn both Canadian?",
            "Yes, both are Canadian.",
            ["Arden is a Canadian actor. Bryn directed the film Quiet Harbor."],
            False,
        ),
        (
            "nationality-scope",
            "Is Arden English?",
            "Arden is English.",
            ["Arden is a British author."],
            False,
        ),
        (
            "scaled-populations",
            "Which has more residents, Luma or Neris?",
            "Luma has more residents than Neris.",
            ["Luma has 1.2 billion residents.", "Neris has 900 million residents."],
            True,
        ),
        (
            "supported-location",
            "Where did Copper Field originate?",
            "Copper Field originated in Luma.",
            ["The band Copper Field originated in Luma."],
            True,
        ),
    ]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def begin(folder, key, payload, ledger, config):
    path = folder / (key + ".json")
    if path.exists():
        raise SystemExit(f"Receipt already exists: {path}; no automatic paid retry.")
    guard_budget(ledger, config)
    row = {
        "state": "pending",
        "started_at": datetime.now(UTC).isoformat(),
        "ledger_before": ledger.summary(),
        **payload,
    }
    save(path, row)
    return path, row, time.perf_counter()


async def review_cases(config, folder):
    async with httpx.AsyncClient() as client:
        provider = OpenAIProvider(client, config)
        for key, question, claim, quotes, expected in synthetic_cases():
            evidence = [
                {"evidence_id": f"E{i + 1}", "title": f"Fictional source {i + 1}", "text": quote}
                for i, quote in enumerate(quotes)
            ]
            draft = AnswerDraft.model_validate(
                {
                    "status": "answered",
                    "claims": [
                        {
                            "text": claim,
                            "citations": [
                                {"evidence_id": hit["evidence_id"], "quote": hit["text"]}
                                for hit in evidence
                            ],
                        }
                    ],
                    "conflicting_claims": [],
                }
            )
            validate_evidence(draft, evidence)
            context = review_context(question, draft, evidence)
            path, row, started = begin(
                folder,
                key,
                {
                    "scope": "synthetic development regression, not held-out evaluation",
                    "model": config.generation_model,
                    "context": json.loads(context),
                    "expected_pass": expected,
                },
                provider.ledger,
                config,
            )
            try:
                raw, usage = await provider.verify(
                    INSTRUCTIONS, context, Review.model_json_schema()
                )
                safe, metadata = apply_review(draft, raw)
                row.update(
                    state="complete",
                    review=raw,
                    verification=metadata,
                    safe_result=safe.model_dump(),
                    usage=usage,
                    passed=(metadata["outcome"] == "passed") == expected,
                )
            except Exception as error:
                # Persist the safe error type; never serialize provider exception bodies/secrets.
                row.update(state="failed", error_type=type(error).__name__, passed=False)
            row.update(
                elapsed_ms=round((time.perf_counter() - started) * 1000),
                ledger_after=provider.ledger.summary(),
            )
            save(path, row)
            print(key, row["state"], "PASS" if row["passed"] else "FAIL", flush=True)


def pipeline_cases(config, folder):
    cases = {
        row["case_id"]: row
        for row in map(
            json.loads,
            Path("fixtures/evaluation/development.jsonl").read_text(encoding="utf-8").splitlines(),
        )
    }
    ledger = UsageLedger(config.usage_db, config.api_budget_usd)
    with TestClient(create_app(config)) as client:
        for key in (
            "development-bridge-01",
            "development-bridge-02",
            "development-conflict-01",
            "development-unanswerable-01",
        ):
            case = cases[key]
            path, row, started = begin(
                folder,
                key,
                {
                    "scope": "existing development fixture, not held-out evaluation",
                    "question": case["question"],
                    "expected_status": case["expected_status"],
                },
                ledger,
                config,
            )
            response = client.post(
                "/api/investigations", json={"question": case["question"], "strategy": "a"}
            )
            result = response.json()
            passed = response.status_code == 200 and result["status"] == case["expected_status"]
            if passed and case["category"] == "bridge":
                by_id = {e["evidence_id"]: e for e in result["evidence"]}
                cited = {
                    by_id[c["evidence_id"]]["document_id"]
                    for claim in result["claims"]
                    for c in claim["citations"]
                }
                passed = {e["document_id"] for e in case["evidence"]}.issubset(cited)
            if passed:
                execution = result["execution"]
                passed = (
                    execution["llm_calls"] <= 4
                    and execution["searches"] <= 3
                    and execution["retrieval_rounds"] <= 2
                    and execution["total_provider_calls"] <= 7
                )
            row.update(
                state="complete",
                http_status=response.status_code,
                result=result,
                passed=passed,
                elapsed_ms=round((time.perf_counter() - started) * 1000),
                ledger_after=ledger.summary(),
            )
            save(path, row)
            print(key, response.status_code, "PASS" if passed else "FAIL", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["review", "pipeline"])
    parser.add_argument("--output", type=Path, default=Path("artifacts/claim-grounding-v2"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    config = Settings()
    if args.phase == "review":
        asyncio.run(review_cases(config, args.output))
    else:
        pipeline_cases(config, args.output)
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in args.output.glob("*.json")]
    print(json.dumps({"attempts": len(rows), "passed": sum(r.get("passed", False) for r in rows)}))
    if not all(r.get("passed", False) for r in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
