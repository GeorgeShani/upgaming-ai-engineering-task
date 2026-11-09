"""Free, isolated worked demonstrations for George's learning checklist.

Uses existing HTTP fakes, not real credentials/providers. It records observable behavior;
it cannot certify George's personal understanding, human review or no-AI performance.
"""

import argparse
import difflib
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path("backend/tests").resolve()))
sys.path.insert(0, str(Path("backend").resolve()))
from app.datasets.fixtures import load_fixtures, render_review
from app.evaluation.metrics import document_scores
from app.investigations.models import AnswerDraft, quote_catalog, validate_evidence
from app.investigations.tools import evidence_context
from app.main import create_app
from app.retrieval.fusion import fuse
from fake_services import fake_services
from fastapi.testclient import TestClient
from test_document_management import AUTH, replace, settings, upload


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def lifecycle():
    storage, transport = fake_services()
    with TemporaryDirectory(prefix="learning-checkpoint-") as temporary:
        config = settings(openai_api_key="fixture-openai", usage_db=Path(temporary) / "first.db")
        app = create_app(config, transport=transport)
        with TestClient(app) as client:
            before = client.get("/api/live")
            health = client.get("/api/health")
            assert before.status_code == health.status_code == 200
            assert health.json()["status"] == "ready"
            created = upload(client)
            assert created.status_code == 201
            source = created.json()["document"]
            key, original = source["document_id"], source["revision_id"]
            duplicate = upload(client)
            assert duplicate.status_code == 200 and duplicate.json()["duplicate"]
            changed = replace(
                client, key, created.headers["x-document-etag"], b"A changed source fact."
            )
            assert changed.status_code == 200
            current = changed.json()["document"]["revision_id"]
            assert current != original
            stale = replace(client, key, created.headers["x-document-etag"], b"Stale edit.")
            assert stale.status_code == 412
            answer = client.post(
                "/api/investigations", json={"question": "What does the source say?"}
            )
            assert answer.status_code == 200 and answer.json()["status"] == "answered"
            result = answer.json()
            validate_evidence_result(result)
            assert all(hit["revision_id"] == current for hit in result["evidence"])
            storage.response_mode = "provider_error"
            failure = client.post(
                "/api/investigations", json={"question": "Provider failure example?"}
            )
            assert failure.status_code == 502 and "answer" not in failure.json()
            storage.response_mode = "valid"
            second = upload(client, b"A disposable second source.", "delete-me.txt")
            deleted = second.json()["document"]["document_id"]
            assert (
                client.delete(
                    "/api/documents/" + deleted,
                    headers={
                        **AUTH,
                        "If-Match": second.headers["x-document-etag"],
                    },
                ).status_code
                == 204
            )
        # Recreate application state while the external fake store remains alive.
        # This is NOT an operating-system restart or a new real cloud restart.
        restarted = create_app(
            config.model_copy(update={"usage_db": Path(temporary) / "second.db"}),
            transport=transport,
        )
        with TestClient(restarted) as client:
            after = client.get("/api/live")
            assert (
                before.headers["x-investigation-instance"]
                != after.headers["x-investigation-instance"]
            )
            read = client.get("/api/documents/" + key)
            assert read.status_code == 200 and read.json()["text"] == "A changed source fact."
            assert read.json()["revision_id"] == current
            assert client.get("/api/documents/" + deleted).status_code == 404
            assert restarted.state.provider.ledger.summary()["calls"] == 0
            assert (
                client.delete(
                    "/api/documents/" + key,
                    headers={
                        **AUTH,
                        "If-Match": read.headers["x-document-etag"],
                    },
                ).status_code
                == 204
            )
            absent = client.post(
                "/api/investigations", json={"question": "What does the deleted source say?"}
            )
            assert absent.status_code == 200
            assert absent.json()["status"] == "insufficient_evidence"
            assert not absent.json()["claims"] and not absent.json()["evidence"]
        return {
            "scope": "real local API routes; in-memory HTTP fakes; application recreation only",
            "liveness_http": before.status_code,
            "health_http": health.status_code,
            "duplicate_reported": True,
            "document_trace": {
                "document_id": key,
                "created_revision": original,
                "active_revision_after_replace": current,
                "original_text": "A fictional source fact.",
                "updated_text": "A changed source fact.",
                "returned_answer": result["answer"],
            },
            "revision_changed": True,
            "stale_write_http": stale.status_code,
            "changed_revision_cited": True,
            "provider_failure_http": failure.status_code,
            "new_app_boot_id": True,
            "source_revision_and_deletion_survive_app_recreation": True,
            "new_local_ledger_is_empty": True,
            "deleted_source_abstention": True,
            "real_cloud_restart_performed": False,
        }


def validate_evidence_result(result):
    validate_evidence(
        AnswerDraft.model_validate(
            {key: result[key] for key in ("status", "claims", "conflicting_claims")}
        ),
        result["evidence"],
    )


def practice_change(folder):
    path = Path("backend/app/retrieval/fusion.py")
    original = path.read_text(encoding="utf-8")
    target = "def fuse(rankings, limit=8, per_document=2):"
    assert original.count(target) == 1
    changed = original.replace(target, target.replace("per_document=2", "per_document=1"))
    namespace = {}
    exec(compile(changed, "isolated-practice-fusion.py", "exec"), namespace)
    hits = [
        {"id": key, "payload": {"document_id": doc}}
        for key, doc in (("a", "one"), ("b", "one"), ("c", "two"))
    ]
    baseline, practice = fuse([hits]), namespace["fuse"]([hits])
    assert [h["id"] for h in baseline] == ["a", "b", "c"]
    assert [h["id"] for h in practice] == ["a", "c"]
    assert path.read_text(encoding="utf-8") == original
    patch = "".join(
        difflib.unified_diff(
            original.splitlines(True),
            changed.splitlines(True),
            fromfile="production/fusion.py",
            tofile="practice/fusion.py",
            n=0,
        )
    )
    (folder / "practice-change.patch").write_bytes(patch.encode())
    return {
        "scope": "AI-assisted isolated source-copy experiment, not George's unaided exercise",
        "baseline_ids": [h["id"] for h in baseline],
        "practice_ids": [h["id"] for h in practice],
        "production_source_unchanged": True,
    }


def saved_examples(folder):
    fingerprint = json.loads(Path("docs/grounding-verification.json").read_text(encoding="utf-8"))
    for name, expected in fingerprint["source_sha256_lf_normalized"].items():
        assert sha256(Path(name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == expected, (
            "Grounding source changed; do not label reconstructed context as matching"
        )
    bridge = json.loads(
        Path("docs/grounding-checks/development-bridge-01.json").read_text(encoding="utf-8")
    )
    result = bridge["result"]
    validate_evidence_result(result)
    by_id = {e["evidence_id"]: e for e in result["evidence"]}
    citations = [
        {
            "claim": claim["text"],
            **citation,
            "document_id": by_id[citation["evidence_id"]]["document_id"],
            "title": by_id[citation["evidence_id"]]["title"],
            "literal_quote_valid": citation["quote"] in by_id[citation["evidence_id"]]["text"],
        }
        for claim in result["claims"]
        for citation in claim["citations"]
    ]
    assert len(citations) == 2 and all(c["literal_quote_valid"] for c in citations)
    context = {
        "question": bridge["question"],
        "evidence": evidence_context(result["evidence"]),
        "quote_choices": [
            {"quote_id": key, **quote} for key, quote in quote_catalog(result["evidence"]).items()
        ],
    }
    save(
        folder / "writer-context-reconstructed.json",
        {
            "scope": (
                "Reconstructed from saved evidence and matching writer code; "
                "not a captured wire request"
            ),
            "instructions_source": "backend/app/investigations/service.py:INSTRUCTIONS",
            "context": context,
        },
    )
    examples = {}
    for key, expected in (
        ("development-bridge-01", "answered"),
        ("development-conflict-01", "conflicting_evidence"),
        ("development-unanswerable-01", "insufficient_evidence"),
    ):
        row = json.loads(
            (Path("docs/grounding-checks") / (key + ".json")).read_text(encoding="utf-8")
        )
        assert row["passed"] and row["result"]["status"] == expected
        validate_evidence_result(row["result"])
        examples[key] = {
            "status": expected,
            "answer": row["result"]["answer"],
            "retrieval_rounds": row["result"]["execution"]["retrieval_rounds"],
        }
    for name, expected in (("correct-age", "passed"), ("reversed-age", "withheld")):
        row = json.loads(
            (Path("docs/grounding-checks") / (name + ".json")).read_text(encoding="utf-8")
        )
        assert row["verification"]["outcome"] == expected
        examples[name] = {"outcome": expected, "review": row["review"]}
    restart = json.loads(Path("docs/deployment/cloud-persistence.json").read_text(encoding="utf-8"))
    assert restart["passed"] and all(restart["persisted"].values())
    assert restart["before"]["instance_id"] != restart["after"]["instance_id"]
    return {
        "scope": "offline inspection of historical real-model/cloud receipts, no new live requests",
        "bridge_citations": citations,
        "examples": examples,
        "historical_cloud_restart": {
            "passed": True,
            "recorded_at": restart["finished_at"],
            "persisted": restart["persisted"],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/learning-checkpoints"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases, documents, manifest = load_fixtures(Path("fixtures"))
    (args.output / "gold-reference-worksheet.md").write_bytes(
        render_review(cases, documents).encode()
    )
    metrics = document_scores(["source-one", "unrelated"], {"source-one", "source-two"})
    assert metrics["recall_at_5"] == 0.5 and metrics["mrr_at_10"] == 1
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "scope": "AI-assisted worked learning checkpoints, not a personal competency certificate",
        "script_sha256_lf": sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "fixtures": {
            "cases": len(cases),
            "sources": len(documents),
            "hashes_ids_and_support_quotes_checked": True,
            "reference_review": manifest["reference_review"],
            "semantic_gold_certification": False,
        },
        "local_api": lifecycle(),
        "practice_change": practice_change(args.output),
        "saved_receipts": saved_examples(args.output),
        "hand_metrics": metrics,
        "rrf": {"a": 1 / 61 + 1 / 63, "b": 1 / 62 + 1 / 61, "winner": "b"},
        "paid_calls": 0,
        "real_cloud_writes": 0,
        "george_independent_review": "pending",
        "frozen_fixture_sha256": {
            name: sha256((Path("fixtures") / name).read_bytes()).hexdigest()
            for name in manifest["files"]
        },
    }
    save(args.output / "verification.json", report)
    print(
        json.dumps(
            {
                "fixtures": len(cases),
                "local_api": "passed",
                "practice_change": "passed",
                "historical_receipts": "checked",
                "report": str(args.output / "verification.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
