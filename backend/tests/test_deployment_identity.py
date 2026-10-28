import re

from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_boot_identity_stays_stable_until_a_new_app_instance_starts():
    config = Settings(_env_file=None)
    with TestClient(create_app(config)) as client:
        first = client.get("/api/live").headers["x-investigation-instance"]
        assert re.fullmatch(r"[a-f0-9]{32}", first)
        assert client.get("/api/health").headers["x-investigation-instance"] == first
        assert client.post("/api/documents").headers["x-investigation-instance"] == first
    with TestClient(create_app(config)) as client:
        assert client.get("/api/live").headers["x-investigation-instance"] != first


def test_release_header_accepts_only_commit_ids_and_does_not_echo_arbitrary_env(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "a" * 40)
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get("/api/live").headers["x-release-revision"] == "a" * 40
    monkeypatch.setenv("RENDER_GIT_COMMIT", "private-value-do-not-echo")
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/api/live")
        assert response.headers["x-release-revision"] == "unknown"
        assert "private-value" not in str(response.headers)
