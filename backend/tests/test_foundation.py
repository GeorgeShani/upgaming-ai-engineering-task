from pathlib import Path

import httpx
import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def config(**overrides) -> Settings:
    values = {"openai_api_key": "", "qdrant_url": None, "qdrant_api_key": ""}
    values.update(overrides)
    return Settings(_env_file=None, **values)


def connected_config() -> Settings:
    return config(
        openai_api_key="test-ai-secret",
        qdrant_url="https://database.example",
        qdrant_api_key="test-db-secret",
    )


def test_blank_template_url_does_not_prevent_startup():
    assert config(qdrant_url="").qdrant_url is None


def test_unconfigured_dependencies_are_reported_without_outbound_requests():
    def unexpected_request(request):
        pytest.fail(f"Unexpected provider request: {request.url.host}")

    app = create_app(config(), transport=httpx.MockTransport(unexpected_request))
    with TestClient(app) as client:
        assert client.get("/api/live").json() == {"status": "running"}
        response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["app"] == "running"
    assert response.json()["status"] == "degraded"
    assert all(
        item["status"] == "unconfigured" for item in response.json()["dependencies"].values()
    )


def test_reachable_dependencies_check_both_models_and_keep_secrets_server_side():
    requests = []

    def provider(request):
        requests.append(request)
        if request.url.host == "api.openai.com":
            assert request.headers["authorization"] == "Bearer test-ai-secret"
        else:
            assert request.headers["api-key"] == "test-db-secret"
        return httpx.Response(200, json={})

    app = create_app(connected_config(), transport=httpx.MockTransport(provider))
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert len(requests) == 3
    assert {r.url.path for r in requests} == {
        "/v1/models/gpt-5.4-mini-2026-03-17",
        "/v1/models/text-embedding-3-small",
        "/collections",
    }
    assert all(r.method == "GET" for r in requests)
    assert "test-ai-secret" not in response.text
    assert "test-db-secret" not in response.text


@pytest.mark.parametrize("status_code", [401, 429, 500])
def test_provider_rejections_are_degraded_and_do_not_leak_error_bodies(status_code):
    def provider(request):
        return httpx.Response(status_code, text="sensitive-provider-details")

    app = create_app(connected_config(), transport=httpx.MockTransport(provider))
    with TestClient(app) as client:
        assert client.get("/api/live").status_code == 200
        response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["dependencies"]["openai"]["status"] == "unavailable"
    assert "sensitive-provider-details" not in response.text


def test_timeout_is_a_dependency_failure_rather_than_a_server_crash():
    def provider(request):
        raise httpx.ReadTimeout("sensitive-url-and-key", request=request)

    app = create_app(connected_config(), transport=httpx.MockTransport(provider))
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 503
    assert "timed out" in response.text
    assert "sensitive-url-and-key" not in response.text


def test_frontend_is_served_but_unknown_api_paths_remain_404s(tmp_path: Path):
    (tmp_path / "index.html").write_text("<h1>Test frontend</h1>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('test');", encoding="utf-8")
    app = create_app(config(), frontend_dist=tmp_path)
    with TestClient(app) as client:
        assert "Test frontend" in client.get("/").text
        assert client.get("/assets/app.js").status_code == 200
        missing = client.get("/api/not-implemented")
        assert missing.status_code == 404
        assert missing.json() == {"detail": "Not Found"}


def test_missing_frontend_build_returns_an_actionable_error(tmp_path: Path):
    with TestClient(create_app(config(), frontend_dist=tmp_path)) as client:
        response = client.get("/")
    assert response.status_code == 503
    assert "npm run build" in response.json()["detail"]
