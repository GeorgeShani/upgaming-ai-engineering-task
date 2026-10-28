"""Paid development-only investigation smoke checks plus a simulated provider failure."""

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path.cwd() / "backend"))
from app.config import Settings
from app.main import create_app
from app.providers import UsageLedger
from fastapi.testclient import TestClient

CASE_IDS = (
    "development-bridge-01",
    "development-bridge-02",
    "development-conflict-01",
    "development-unanswerable-01",
)


def verify_citations(client, result):
    by_id = {e["evidence_id"]: e for e in result["evidence"]}
    documents = {}
    checks = []
    for claim in result["claims"] + result["conflicting_claims"]:
        for citation in claim["citations"]:
            hit = by_id[citation["evidence_id"]]
            key = hit["document_id"]
            if key not in documents:
                response = client.get("/api/documents/" + key)
                assert response.status_code == 200
                documents[key] = response.json()
            source = documents[key]
            assert source["revision_id"] == hit["revision_id"]
            assert source["text"][hit["start"] : hit["end"]] == hit["text"]
            assert citation["quote"] in hit["text"]
            checks.append(
                {
                    "evidence_id": citation["evidence_id"],
                    "document_id": key,
                    "source_and_quote_match": True,
                }
            )
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        action="append",
        choices=CASE_IDS,
        help="Run only these development cases; default is all four.",
    )
    selected_cases = parser.parse_args().case or CASE_IDS
    config = Settings()
    ledger = UsageLedger(config.usage_db, config.api_budget_usd)
    before = ledger.summary()
    cases = {
        case["case_id"]: case
        for case in (
            json.loads(line)
            for line in Path("fixtures/evaluation/development.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
    }
    folder = Path("artifacts/multistep")
    folder.mkdir(parents=True, exist_ok=True)
    reports = []
    app = create_app(config)
    with TestClient(app) as client:
        original_generate = app.state.provider.generate
        for case_id in selected_cases:
            case = cases[case_id]

            async def capture(instructions, context, schema, *, current_case=case_id):
                draft, usage = await original_generate(instructions, context, schema)
                (folder / (current_case + "-context-and-draft.json")).write_text(
                    json.dumps(
                        {"context": json.loads(context), "draft": draft},
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return draft, usage

            app.state.provider.generate = capture
            response = client.post(
                "/api/investigations",
                json={
                    "question": case["question"],
                    "strategy": "a",
                },
            )
            print(case_id, "HTTP", response.status_code, flush=True)
            if response.status_code != 200:
                raise SystemExit(response.json())  # Sanitized API failure, not provider raw output.
            result = response.json()
            (folder / (case_id + ".json")).write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            assert result["status"] == case["expected_status"]
            execution = result["execution"]
            assert execution["retrieval_rounds"] <= 2 and execution["tool_calls"] <= 3
            assert execution["llm_calls"] <= 4 and execution["total_provider_calls"] <= 7
            checks = verify_citations(client, result)
            if case["category"] == "bridge":
                required = {e["document_id"] for e in case["evidence"]}
                assert required.issubset({check["document_id"] for check in checks}), (
                    "Bridge answer did not cite both labelled supporting documents."
                )
            if case_id == "development-bridge-01":
                assert "north atlantic conference" in result["answer"].casefold()
            elif case_id == "development-bridge-02":
                assert "1969" in result["answer"] and "1974" in result["answer"]
            elif case["category"] == "conflict":
                quotes = " ".join(
                    c["quote"] for claim in result["conflicting_claims"] for c in claim["citations"]
                )
                assert all(fact in quotes for fact in case["expected_facts"])
                assert len({check["document_id"] for check in checks}) >= 2
            else:
                assert not result["claims"] and not result["conflicting_claims"]
            report = {
                "case_id": case_id,
                "question": case["question"],
                "answer": result["answer"],
                "status": result["status"],
                "execution": execution,
                "usage": result["usage"],
                "configuration": result["configuration"],
                "latency_ms": result["latency_ms"],
                "checks": checks,
                "searches": [
                    {
                        "round": t["round"],
                        "query": t["query"],
                        "follow_up": t["follow_up"],
                        "executed": t["executed"],
                    }
                    for t in result["search_trace"]
                ],
            }
            reports.append(report)
            (folder / (case_id + "-verification.json")).write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps({"answer": result["answer"], "execution": execution}), flush=True)
    if set(selected_cases) == set(CASE_IDS):
        assert any(t["follow_up"] for report in reports[:2] for t in report["searches"]), (
            "No entity follow-up was observed; inspect traces before claiming multi-hop."
        )
    # Deterministic error probe: no real failed requests, credentials changed, or extra charges.
    failure_config = config.model_copy(update={"usage_db": folder / "failure-probe.sqlite3"})
    with TestClient(
        create_app(
            failure_config,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(503, text="fixture-provider-private-error")
            ),
        )
    ) as client:
        failed = client.post("/api/investigations", json={"question": "Provider failure probe"})
        assert failed.status_code == 502 and "fixture-provider-private-error" not in failed.text
    summary = {
        "scope": "development smoke checks; final evaluation not executed",
        "cases": reports,
        "simulated_provider_failure_http": failed.status_code,
        "usage_before": before,
        "usage_after": ledger.summary(),
    }
    (folder / "verification.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print("Verification report:", folder / "verification.json", flush=True)


if __name__ == "__main__":
    main()
