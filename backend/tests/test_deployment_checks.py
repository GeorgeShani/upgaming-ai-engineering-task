import importlib.util
from pathlib import Path

import httpx
import pytest
from app.providers import BudgetExceeded, UsageLedger

spec = importlib.util.spec_from_file_location(
    "deployment_checks", Path("scripts/deployment_checks.py")
)
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


@pytest.mark.parametrize(
    "origin",
    [
        "http://demo.onrender.com",
        "https://user:password@demo.onrender.com",
        "https://demo.onrender.com/?key=secret",
        "https://demo.onrender.com/path",
        "https://demo.onrender.com/#secret",
    ],
)
def test_remote_origins_require_https_and_cannot_embed_credentials_or_paths(origin):
    with pytest.raises(ValueError):
        checks.origin(origin)


def test_local_loopback_is_allowed_but_redirects_do_not_forward_admin_tokens():
    assert checks.origin("http://127.0.0.1:8010/") == "http://127.0.0.1:8010"
    seen = []

    def transport(request):
        seen.append(request)
        return httpx.Response(307, headers={"Location": "https://untrusted.example/"})

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        probe = checks.DeploymentChecks(client, "https://demo.onrender.com", "fixture-admin")
        with pytest.raises(AssertionError):
            probe.upload("Unique source.", "source.txt")
    assert len(seen) == 1
    assert seen[0].url.host == "demo.onrender.com"


def test_duplicate_upload_is_never_owned_or_deleted_by_the_probe():
    def transport(request):
        return httpx.Response(200, json={"document": {"document_id": "existing"}})

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        probe = checks.DeploymentChecks(client, "http://127.0.0.1:8010", "fixture-admin")
        with pytest.raises(AssertionError, match="new"):
            probe.upload("Unique source.", "source.txt")
        assert probe.owned == set()


def test_document_revision_header_survives_a_proxy_weakened_etag():
    response = httpx.Response(
        200,
        headers={
            "ETag": 'W/"compressed"',
            "X-Document-ETag": '"revision"',
        },
    )
    assert checks.document_etag(response) == '"revision"'


def test_paid_container_usage_is_imported_once_and_budget_failure_is_atomic(tmp_path):
    ledger = UsageLedger(tmp_path / "usage.db", 0.025)
    row = {
        "id": 1,
        "kind": "generation",
        "reserved": 0.02,
        "created": "2026-10-28T00:00:00Z",
        "input_tokens": 100,
        "output_tokens": 10,
        "actual_usd": 0.001,
    }
    assert checks.import_container_usage(ledger, "a" * 64, [row]) == 1
    assert checks.import_container_usage(ledger, "a" * 64, [row]) == 0
    assert ledger.summary()["calls"] == 1
    with pytest.raises(BudgetExceeded):
        checks.import_container_usage(ledger, "b" * 64, [row])
    assert ledger.summary()["calls"] == 1
    assert ledger.summary()["estimated_actual_usd"] == 0.001
