import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest
from app.providers import UsageLedger

sys.path.insert(0, str(Path("scripts").resolve()))
spec = importlib.util.spec_from_file_location(
    "cloud_verification", Path("scripts/verify_cloud_persistence.py")
)
cloud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cloud)


def state():
    return {
        "url": "https://demo.onrender.com",
        "marker": "CLOUD-" + "a" * 32,
        "phase": "prepared",
        "before": {"instance_id": "b" * 32, "release_revision": "c" * 40},
        "spending": {},
        "owned": {},
        "updated": {"document_id": "live", "revision_id": "new"},
        "deleted": {"document_id": "deleted"},
    }


def result():
    hit = {
        "document_id": "live",
        "revision_id": "new",
        "evidence_id": "E1",
        "text": "The recovery time was 21 minutes.",
    }
    return {
        "status": "answered",
        "answer": "21 minutes",
        "evidence": [hit],
        "search_trace": [{"evidence": [hit]}],
        "claims": [{"citations": [{"evidence_id": "E1", "quote": "21 minutes"}]}],
    }


@pytest.mark.parametrize(
    "bad_hit",
    [
        {"document_id": "deleted", "revision_id": "old"},
        {"document_id": "live", "revision_id": "old"},
    ],
)
def test_inactive_evidence_in_any_search_round_fails_even_with_a_correct_final_citation(bad_hit):
    report = result()
    cloud.check_result(report, state())
    report["search_trace"][0]["evidence"].append(bad_hit)
    with pytest.raises(AssertionError):
        cloud.check_result(report, state())


def test_unchanged_boot_is_rejected_before_a_paid_request(tmp_path):
    seen = []

    def transport(request):
        seen.append(request.method)
        return httpx.Response(
            200,
            headers={
                "x-investigation-instance": "b" * 32,
                "x-release-revision": "c" * 40,
            },
        )

    path = tmp_path / "state.json"
    path.write_text(json.dumps(state()))
    ledger = UsageLedger(tmp_path / "usage.db", 1)
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        probe = cloud.DeploymentChecks(client, "https://demo.onrender.com", "fixture")
        with pytest.raises(AssertionError, match="No actual restart"):
            cloud.CloudCheck(probe, ledger, path).verify(None)
    assert seen == ["GET"] and ledger.summary()["calls"] == 0


def test_cleanup_refuses_externally_edited_sources(tmp_path):
    checkpoint = state()
    checkpoint["owned"]["live"] = checkpoint["updated"]
    document = {
        "document_id": "live",
        "revision_id": "external",
        "filename": checkpoint["marker"] + "-source.txt",
        "text": checkpoint["marker"],
    }
    seen = []

    def transport(request):
        seen.append(request.method)
        return httpx.Response(200, json=document)

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        probe = cloud.DeploymentChecks(client, checkpoint["url"], "fixture")
        check = cloud.CloudCheck(probe, UsageLedger(tmp_path / "usage.db", 1), tmp_path / "state")
        with pytest.raises(AssertionError, match="edited externally"):
            check.cleanup(checkpoint)
    assert seen == ["GET"]


def test_paid_steps_are_checkpointed_and_cannot_be_resubmitted(tmp_path):
    ledger = UsageLedger(tmp_path / "usage.db", 1)
    path = tmp_path / "state.json"
    check = cloud.CloudCheck(None, ledger, path)
    checkpoint = state()
    check.reserve(checkpoint, "question-before", 0.06)
    assert "question-before" in json.loads(path.read_text())["spending"]
    with pytest.raises(AssertionError, match="already attempted"):
        check.reserve(checkpoint, "question-before", 0.06)
    assert ledger.summary()["calls"] == 1


def test_duplicate_public_upload_is_never_adopted(tmp_path):
    checkpoint = state()
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"document": {"document_id": "existing"}})
        )
    ) as client:
        probe = cloud.DeploymentChecks(client, checkpoint["url"], "fixture")
        check = cloud.CloudCheck(probe, UsageLedger(tmp_path / "usage.db", 1), tmp_path / "state")
        with pytest.raises(AssertionError, match="not adopting"):
            check.upload(checkpoint, "new", "fictional text")
    assert checkpoint["owned"] == {}
