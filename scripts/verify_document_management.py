import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path.cwd() / "backend"))
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

settings = Settings()
headers = {"Authorization": "Bearer " + settings.demo_admin_token.get_secret_value()}
summary = {
    "storage": "real Qdrant",
    "generation_calls": 0,
    "embedding_calls_possible": bool(settings.openai_api_key.get_secret_value()),
}
identifier = etag = None
try:
    with TestClient(create_app(settings)) as client:
        first = client.post(
            "/api/documents",
            headers=headers,
            files={"file": ("incident.pdf", Path("fixtures/uploads/incident.pdf").read_bytes())},
        )
        print("PDF create status:", first.status_code, flush=True)
        if first.status_code not in (200, 201):
            print("Sanitized API response:", first.json(), flush=True)
            raise SystemExit(1)
        identifier = first.json()["document"]["document_id"]
        etag = first.headers["etag"]
        # Only mutate newly created smoke data, never an existing user document.
        if first.status_code != 201:
            summary["duplicate_existing_sample"] = True
            identifier = None
            raise SystemExit("Sample already exists; stopped without modifying existing data.")
        summary["pdf_create"] = first.status_code
        for name in ("incident.docx", "incident.txt"):
            result = client.post(
                "/api/documents",
                headers=headers,
                files={"file": (name, Path("fixtures/uploads", name).read_bytes())},
            )
            assert result.status_code == 200 and result.json()["duplicate"]
            summary[name + "_deduplicated"] = True
        result = client.get("/api/documents/" + identifier)
        assert result.status_code == 200 and result.json()["locations"][0]["kind"] == "page"
        summary["page_locations"] = True
        replacement_text = "Fictional slice 3 smoke revision " + str(uuid4())
        updated = client.put(
            "/api/documents/" + identifier,
            headers={**headers, "If-Match": etag},
            files={"file": ("replacement.txt", replacement_text.encode())},
        )
        assert updated.status_code == 200
        old_etag, etag = etag, updated.headers["etag"]
        assert etag != old_etag
        summary["replacement"] = True
    with TestClient(create_app(settings)) as restarted:
        fetched = restarted.get("/api/documents/" + identifier)
        assert fetched.status_code == 200 and fetched.json()["text"] == replacement_text
        summary["persisted_across_app_restart"] = True
        stale = restarted.delete(
            "/api/documents/" + identifier, headers={**headers, "If-Match": old_etag}
        )
        assert stale.status_code == 412
        removed = restarted.delete(
            "/api/documents/" + identifier, headers={**headers, "If-Match": etag}
        )
        assert removed.status_code == 204
        summary["stale_delete_rejected"] = True
        summary["delete"] = True
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get("/api/documents/" + identifier).status_code == 404
        summary["deletion_persisted_across_app_restart"] = True
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/ingestion-live-check.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
finally:
    # Leave only a tombstone and immutable revisions for the documented soft-delete behaviour.
    if identifier and not summary.get("delete"):
        with TestClient(create_app(settings)) as cleanup:
            current = cleanup.get("/api/documents/" + identifier)
            if current.status_code == 200:
                cleanup.delete(
                    "/api/documents/" + identifier,
                    headers={**headers, "If-Match": current.headers["etag"]},
                )
