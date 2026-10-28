"""HTTP deployment checks shared by local-container and public-service verification."""

import math
import re
from urllib.parse import urlsplit


def origin(value):
    url = urlsplit(value)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in {"", "/"}
        or url.scheme == "http"
        and url.hostname not in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError("Use an HTTPS origin, or HTTP loopback, without credentials/path/query.")
    return value.rstrip("/")


class DeploymentChecks:
    def __init__(self, client, base_url, token, secrets=()):
        self.client, self.base, self.token = client, origin(base_url), token
        self.secrets = [value.encode() for value in (*secrets, token) if len(value) >= 8]
        self.owned = set()

    def request(self, method, path, *, admin=False, headers=None, **options):
        headers = dict(headers or {})
        if admin:
            headers["Authorization"] = f"Bearer {self.token}"
        return self.client.request(
            method, self.base + path, headers=headers, follow_redirects=False, **options
        )

    def read(self, identifier):
        return self.request("GET", f"/api/documents/{identifier}")

    def upload(self, text, filename):
        response = self.request(
            "POST",
            "/api/documents",
            admin=True,
            files={"file": (filename, text.encode(), "text/plain")},
        )
        assert response.status_code == 201, (
            "Probe requires a newly created source; no existing data is owned."
        )
        document = response.json()["document"]
        self.owned.add(document["document_id"])
        assert document["index_status"] == "ready", "Source is not indexed."
        return document, response.headers["etag"]

    def replace(self, identifier, etag, text, filename):
        assert identifier in self.owned, "Only this probe's new documents may be changed."
        response = self.request(
            "PUT",
            f"/api/documents/{identifier}",
            admin=True,
            headers={"If-Match": etag},
            files={"file": (filename, text.encode(), "text/plain")},
        )
        assert response.status_code == 200, "Probe replacement failed."
        return response.json()["document"], response.headers["etag"]

    def remove(self, identifier, etag):
        assert identifier in self.owned, "Only this probe's new documents may be deleted."
        response = self.request(
            "DELETE", f"/api/documents/{identifier}", admin=True, headers={"If-Match": etag}
        )
        assert response.status_code == 204, "Probe deletion failed."

    def probe_public(self):
        alive = self.request("GET", "/api/live")
        assert alive.status_code == 200 and alive.json()["status"] == "running"
        instance = alive.headers.get("x-investigation-instance", "")
        assert re.fullmatch(r"[a-f0-9]{32}", instance), "Boot identity header is missing."
        health = self.request("GET", "/api/health")
        assert health.status_code == 200 and health.json()["status"] == "ready", (
            "Dependencies are not ready."
        )
        page = self.request("GET", "/")
        assert page.status_code == 200 and 'id="root"' in page.text
        assets = list(dict.fromkeys(re.findall(r'(?:src|href)="(/assets/[^"?#]+)"', page.text)))
        assert any(path.endswith(".js") for path in assets) and any(
            path.endswith(".css") for path in assets
        )
        for path, response in [("/", page), ("/api/health", health)] + [
            (path, self.request("GET", path)) for path in assets
        ]:
            assert response.status_code == 200, f"Asset unavailable: {path}"
            assert not any(value in response.content for value in self.secrets), (
                "Secret found in public content."
            )
        for path in ("/.env", "/data/usage.sqlite3", "/backend/app/main.py"):
            assert self.request("GET", path).status_code == 404, "Private path is exposed."
        assert self.request("POST", "/api/__test/reset").status_code == 404
        for method, path in (
            ("POST", "/api/documents"),
            ("PUT", "/api/documents/unauthorized-probe"),
            ("DELETE", "/api/documents/unauthorized-probe"),
        ):
            assert self.request(method, path).status_code == 401, (
                "Anonymous mutation is not rejected."
            )
        invalid = self.request("POST", "/api/investigations", json={"question": "x"})
        assert invalid.status_code == 422, "Invalid question was not rejected before paid work."
        return {
            "liveness_http": alive.status_code,
            "instance_id": instance,
            "release_revision": alive.headers.get("x-release-revision", "unknown"),
            "health": health.json(),
            "compiled_assets": assets,
            "private_paths_hidden": True,
            "test_reset_absent": True,
            "anonymous_mutations_rejected": True,
            "invalid_question_rejected": True,
            "known_secrets_absent_from_checked_content": True,
        }

    def investigate(self, marker, identifier, revision, fact):
        response = self.request(
            "POST",
            "/api/investigations",
            json={
                "question": (
                    "What recovery time was documented for fictional deployment case "
                    + marker
                    + "?"
                )
            },
            timeout=105,
        )
        assert response.status_code == 200, f"Investigation returned HTTP {response.status_code}."
        result = response.json()
        assert result["status"] == "answered" and fact in result["answer"], (
            "Investigation did not return the expected fact."
        )
        by_id = {e["evidence_id"]: e for e in result["evidence"]}
        assert any(
            by_id[c["evidence_id"]]["document_id"] == identifier
            and by_id[c["evidence_id"]]["revision_id"] == revision
            for claim in result["claims"]
            for c in claim["citations"]
        ), "New active revision was not actually cited."
        return result


def import_container_usage(ledger, container_id, calls):
    """Preserve paid-test usage before deleting ephemeral container SQLite; import once."""
    from app.providers import BudgetExceeded

    assert re.fullmatch(r"[a-f0-9]{64}", container_id), "Expected an owned full container ID."
    with ledger.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        rows = []
        for call in calls:
            kind = f"deployment:{container_id}:{call['id']}:{call['kind']}"
            if db.execute("SELECT 1 FROM calls WHERE kind=?", (kind,)).fetchone():
                continue
            amount = max(call["reserved"], call["actual_usd"] or 0)
            if not math.isfinite(amount) or amount < 0:
                raise ValueError("Invalid imported usage amount.")
            rows.append(
                (
                    kind,
                    amount,
                    call["created"],
                    call["input_tokens"],
                    call["output_tokens"],
                    call["actual_usd"],
                )
            )
        spent = db.execute("SELECT COALESCE(SUM(reserved),0) FROM calls").fetchone()[0]
        if spent + sum(row[1] for row in rows) > ledger.ceiling:
            raise BudgetExceeded
        db.executemany(
            "INSERT INTO calls(kind,reserved,created,input_tokens,output_tokens,actual_usd) "
            "VALUES (?,?,?,?,?,?)",
            rows,
        )
    return len(rows)
