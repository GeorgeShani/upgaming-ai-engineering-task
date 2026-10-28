"""Opt-in live checks against disposable production-image containers and real Qdrant."""

import argparse
import json
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import Settings
from app.evaluation.state import save
from app.providers import UsageLedger
from deployment_checks import DeploymentChecks, import_container_usage

IMAGE = "investigation-engine:slice9"
BASE = "http://127.0.0.1:8010"


def docker(*arguments, script=None):
    result = subprocess.run(["docker", *arguments], input=script, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("Docker command failed; inspect the owned container locally.")
    return result.stdout.strip()


def start(config, marker, budget="0.1"):
    name = f"investigation-slice9-{uuid4().hex[:10]}"
    values = {}
    for key, value in config.model_dump().items():
        if hasattr(value, "get_secret_value"):
            value = value.get_secret_value()
        if value is not None:
            values[key.upper()] = str(value)
    values.update(PORT="10000", USAGE_DB="/tmp/investigation-usage.sqlite3", API_BUDGET_USD=budget)
    # Docker env-file is not dotenv: parse quotes with Settings before writing runtime values.
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".env", dir="artifacts", delete=False
    ) as stream:
        path = Path(stream.name)
        for key, value in values.items():
            assert "\n" not in value and "\r" not in value
            stream.write(f"{key}={value}\n")
    try:
        identifier = docker(
            "run",
            "--detach",
            "--name",
            name,
            "--label",
            f"app.verification={marker}",
            "--memory",
            "512m",
            "--cpus",
            "0.1",
            "--publish",
            "127.0.0.1:8010:10000",
            "--env-file",
            str(path),
            IMAGE,
        )
        return identifier
    finally:
        path.unlink()


def container_json(identifier, script):
    return json.loads(docker("exec", "-i", identifier, ".venv/bin/python", "-", script=script))


def ledger_state(identifier):
    return container_json(
        identifier,
        """
import sys, json
sys.path.insert(0, 'backend')
from app.config import Settings
from app.providers import UsageLedger
config=Settings(); ledger=UsageLedger(config.usage_db,config.api_budget_usd)
with ledger.connect() as db:
    names=['id','kind','reserved','created','input_tokens','output_tokens','actual_usd']
    sql=('SELECT id,kind,reserved,created,input_tokens,output_tokens,actual_usd '
         'FROM calls ORDER BY id')
    calls=[dict(zip(names,row,strict=True)) for row in db.execute(sql)]
    cached=db.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0]
print(json.dumps({'summary':ledger.summary(),'calls':calls,'cached_embeddings':cached}))
""",
    )


def wait_ready(client):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            if client.get(BASE + "/api/live", timeout=2).status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(1)
    raise RuntimeError("Owned container did not become live within 120 seconds.")


def stop_owned(identifier, marker):
    label = docker("inspect", "--format", '{{index .Config.Labels "app.verification"}}', identifier)
    assert label == marker, "Refusing to remove an unowned container."
    docker("rm", "--force", identifier)


def cleanup_sources(config, owned, marker):
    # Cleanup must work even when the disposable container is unavailable.
    from app.main import create_app
    from fastapi.testclient import TestClient

    with TestClient(create_app(config)) as client:
        for key in owned:
            response = client.get(f"/api/documents/{key}")
            if response.status_code == 404:
                continue
            assert response.status_code == 200 and marker in response.json()["text"]
            removed = client.delete(
                f"/api/documents/{key}",
                headers={
                    "Authorization": "Bearer " + config.demo_admin_token.get_secret_value(),
                    "If-Match": response.headers["etag"],
                },
            )
            assert removed.status_code == 204, "Could not clean up an owned probe source."


def verify_persistence():
    config = Settings()
    assert config.demo_admin_token.get_secret_value(), "Configure the demo admin token."
    ledger = UsageLedger(config.usage_db, config.api_budget_usd)
    assert ledger.summary()["reserved_usd"] + 0.1 < ledger.ceiling, (
        "Insufficient conservative budget."
    )
    marker = "DEPLOY-" + uuid4().hex
    Path("artifacts").mkdir(exist_ok=True)
    report = {
        "scope": "local production Docker image; not public Render verification",
        "passed": False,
        "started_at": datetime.now(UTC).isoformat(),
        "case": marker,
        "image": IMAGE,
        "image_id": docker("image", "inspect", "--format", "{{.Id}}", IMAGE),
        "memory_limit_bytes": 512 * 1024 * 1024,
        "cpu_limit": 0.1,
        "ledger_before": ledger.summary(),
        "containers": [],
    }
    identifier = None
    owned = set()
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        probe = DeploymentChecks(
            client,
            BASE,
            config.demo_admin_token.get_secret_value(),
            secrets=(
                config.openai_api_key.get_secret_value(),
                config.qdrant_api_key.get_secret_value(),
                str(config.qdrant_url),
            ),
        )
        owned = probe.owned
        try:
            identifier = start(config, marker)
            wait_ready(client)
            first_state = ledger_state(identifier)
            assert first_state["summary"]["calls"] == 0 and first_state["cached_embeddings"] == 0
            report["public_surface_checks"] = probe.probe_public()
            original = (
                f"Fictional deployment case {marker}. "
                f"The documented recovery time for case {marker} was 13 minutes."
            )
            replacement = original.replace("13 minutes", "21 minutes")
            document, old_etag = probe.upload(original, f"deployment-{marker}.txt")
            save(
                Path("artifacts/deployment-owned.json"),
                {"marker": marker, "owned_ids": sorted(owned)},
            )
            key = document["document_id"]
            deleted, deleted_etag = probe.upload(
                original + " Separate disposable deletion record.",
                f"deployment-{marker}-deleted.txt",
            )
            save(
                Path("artifacts/deployment-owned.json"),
                {"marker": marker, "owned_ids": sorted(owned)},
            )
            updated, new_etag = probe.replace(
                key, old_etag, replacement, f"deployment-{marker}-updated.txt"
            )
            assert updated["revision_id"] != document["revision_id"]
            stale = probe.request(
                "DELETE", f"/api/documents/{key}", admin=True, headers={"If-Match": old_etag}
            )
            assert stale.status_code == 412
            probe.remove(deleted["document_id"], deleted_etag)
            assert probe.read(deleted["document_id"]).status_code == 404
            report["before_recreate_answer"] = probe.investigate(
                marker, key, updated["revision_id"], "21 minutes"
            )
            before = ledger_state(identifier)
            report["containers"].append({"id": identifier, "state": before})
            save(Path("artifacts/deployment-local.json"), report)
            import_container_usage(ledger, identifier, before["calls"])
            stop_owned(identifier, marker)
            identifier = None
            identifier = start(config, marker)
            wait_ready(client)
            fresh = ledger_state(identifier)
            assert fresh["summary"]["calls"] == 0 and fresh["cached_embeddings"] == 0
            current = probe.read(key)
            assert current.status_code == 200 and current.json()["text"] == replacement
            assert (
                current.json()["revision_id"] == updated["revision_id"]
                and current.headers["etag"] == new_etag
            )
            assert probe.read(deleted["document_id"]).status_code == 404
            report["after_recreate_answer"] = probe.investigate(
                marker, key, updated["revision_id"], "21 minutes"
            )
            probe.remove(key, new_etag)
            report.update(
                document_survives_fresh_container=True,
                replacement_survives=True,
                deleted_source_remains_404=True,
                sqlite_and_embedding_cache_reset=True,
                stale_etag_rejected=True,
                own_sources_cleaned=True,
                passed=True,
                second_container_initial_state=fresh,
            )
        finally:
            try:
                cleanup_sources(config, owned, marker)
            finally:
                if identifier:
                    state = ledger_state(identifier)
                    report["containers"].append({"id": identifier, "state": state})
                    save(Path("artifacts/deployment-local.json"), report)
                    import_container_usage(ledger, identifier, state["calls"])
                    report["runtime_stats"] = docker(
                        "stats", "--no-stream", "--format", "{{.MemUsage}}", identifier
                    )
                    stop_owned(identifier, marker)
                report["ledger_after"] = ledger.summary()
                save(Path("artifacts/deployment-local.json"), report)
    print("Local Docker persistence checks passed; report: artifacts/deployment-local.json")


def verify_surface():
    config = Settings()
    marker = "SURFACE-" + uuid4().hex
    identifier = None
    Path("artifacts").mkdir(exist_ok=True)
    report = {"scope": "local production Docker surface/limits; no paid calls", "passed": False}
    try:
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            identifier = start(config, marker, "0.000001")
            wait_ready(client)
            probe = DeploymentChecks(
                client,
                BASE,
                config.demo_admin_token.get_secret_value(),
                secrets=(
                    config.openai_api_key.get_secret_value(),
                    config.qdrant_api_key.get_secret_value(),
                    str(config.qdrant_url),
                ),
            )
            report["surface"] = probe.probe_public()
            too_large = probe.request(
                "POST",
                "/api/documents",
                admin=True,
                files={"file": ("oversized.txt", b"x" * 5_000_001, "text/plain")},
            )
            assert too_large.status_code == 413
            for _ in range(6):
                limited = probe.request(
                    "POST",
                    "/api/investigations",
                    json={"question": "Deployment budget guard probe"},
                )
                assert limited.status_code == 503
            seventh = probe.request(
                "POST", "/api/investigations", json={"question": "Deployment budget guard probe"}
            )
            assert seventh.status_code == 429 and seventh.headers["retry-after"] == "60"
            state = ledger_state(identifier)
            assert state["summary"]["calls"] == 0
            report.update(
                upload_limit_http=413,
                sixth_budget_rejection_http=503,
                seventh_rate_limit_http=429,
                provider_calls=0,
            )
            report["runtime"] = container_json(
                identifier,
                """
import importlib.util, json, os
from pathlib import Path
private_paths=('/app/.env','/app/.git','/app/data')
print(json.dumps({'private_image_paths_absent': all(not Path(p).exists() for p in private_paths),
 'dataset_tooling_absent':importlib.util.find_spec('datasets') is None,
 'pytest_absent':importlib.util.find_spec('pytest') is None,
 'tokenizer_cache_present': bool(list(Path(os.environ['TIKTOKEN_CACHE_DIR']).glob('*')))}))
""",
            )
            assert all(report["runtime"].values())
            report["mounts"] = json.loads(
                docker("inspect", "--format", "{{json .Mounts}}", identifier)
            )
            assert not report["mounts"]
            stop_owned(identifier, marker)
            identifier = None
            identifier = start(config, marker, "0.000001")
            wait_ready(client)
            after = probe.request("GET", "/api/live")
            report["new_instance_id"] = after.headers["x-investigation-instance"]
            assert report["new_instance_id"] != report["surface"]["instance_id"]
            report.update(new_instance_header_verified=True, passed=True)
    finally:
        if identifier:
            stop_owned(identifier, marker)
        save(Path("artifacts/deployment-surface.json"), report)
    print("Production surface/limit checks passed; report: artifacts/deployment-surface.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--surface-only", action="store_true", help="No paid calls or source writes."
    )
    args = parser.parse_args()
    if args.surface_only:
        verify_surface()
    else:
        verify_persistence()


if __name__ == "__main__":
    main()
