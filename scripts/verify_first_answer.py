"""Paid development smoke check; never reads or executes the final evaluation questions."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "backend"))
from app.main import create_app
from fastapi.testclient import TestClient


def main():
    cases = [
        json.loads(line)
        for line in Path("fixtures/evaluation/development.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    case = next(case for case in cases if case["case_id"] == "development-simple-01")
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/investigations",
            json={
                "question": case["question"],
                "strategy": "a",
            },
        )
        print("Investigation HTTP status:", response.status_code, flush=True)
        if response.status_code != 200:
            print(response.json())  # API dependency errors are deliberately sanitized.
            raise SystemExit(1)
        result = response.json()
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/first-cited-answer.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        assert result["status"] == "answered" and case["gold_answer"] in result["answer"]
        by_id = {e["evidence_id"]: e for e in result["evidence"]}
        checks = []
        for claim in result["claims"]:
            for citation in claim["citations"]:
                evidence = by_id[citation["evidence_id"]]
                document = client.get("/api/documents/" + evidence["document_id"])
                assert document.status_code == 200
                source = document.json()
                assert source["revision_id"] == evidence["revision_id"]
                assert source["text"][evidence["start"] : evidence["end"]] == evidence["text"]
                assert citation["quote"] in evidence["text"]
                checks.append({"evidence_id": citation["evidence_id"], "source_matches": True})
        report = {
            "case_id": case["case_id"],
            "question": case["question"],
            "answer": result["answer"],
            "status": result["status"],
            "configuration": result["configuration"],
            "usage": result["usage"],
            "latency_ms": result["latency_ms"],
            "checks": checks,
            "scope": "one development smoke check, not a final evaluation",
        }
        Path("artifacts/first-answer-verification.json").write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
