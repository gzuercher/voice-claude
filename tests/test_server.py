from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "")
    monkeypatch.setenv("TARGET_URL", "http://backend:9000/prompt")
    monkeypatch.setenv("TARGET_TOKEN", "")
    monkeypatch.setenv("ALLOWED_ORIGIN", "")
    monkeypatch.setenv("INSTANCE_NAME", "TestBot")
    monkeypatch.setenv("INSTANCE_COLOR", "#ff0000")
    monkeypatch.setenv("SPEECH_LANG", "de-CH")


def _reload_app():
    import importlib

    import server

    importlib.reload(server)
    return TestClient(server.app)


def _mock_target(json_body=None, status_code=200, raise_error=False):
    if json_body is None:
        json_body = {"response": "ok"}

    if raise_error:
        mock_post = AsyncMock(side_effect=httpx.RequestError("connection failed"))
    else:
        mock_response = httpx.Response(status_code, json=json_body)
        mock_post = AsyncMock(return_value=mock_response)

    mock_client = AsyncMock()
    mock_client.post = mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return patch("httpx.AsyncClient", return_value=mock_client)


class TestConfigEndpoint:
    def test_returns_instance_config(self):
        client = _reload_app()
        res = client.get("/config")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "TestBot"
        assert data["color"] == "#ff0000"
        assert data["lang"] == "de-CH"


class TestPromptEndpoint:
    def test_forwards_to_target(self):
        client = _reload_app()
        with _mock_target({"response": "Hello from backend"}):
            res = client.post("/prompt", json={"text": "hi"})
        assert res.status_code == 200
        assert res.json()["response"] == "Hello from backend"

    def test_empty_text_rejected(self):
        client = _reload_app()
        res = client.post("/prompt", json={"text": ""})
        assert res.status_code == 422

    def test_too_long_rejected(self):
        client = _reload_app()
        res = client.post("/prompt", json={"text": "a" * 5000})
        assert res.status_code == 422

    def test_missing_text_rejected(self):
        client = _reload_app()
        res = client.post("/prompt", json={})
        assert res.status_code == 422

    def test_target_unreachable_returns_502(self):
        client = _reload_app()
        with _mock_target(raise_error=True):
            res = client.post("/prompt", json={"text": "hi"})
        assert res.status_code == 502
        assert "unreachable" in res.json()["detail"].lower()

    def test_target_error_returns_502(self):
        client = _reload_app()
        with _mock_target(status_code=500, json_body={"error": "internal"}):
            res = client.post("/prompt", json={"text": "hi"})
        assert res.status_code == 502

    def test_no_target_configured(self, monkeypatch):
        monkeypatch.setenv("TARGET_URL", "")
        client = _reload_app()
        res = client.post("/prompt", json={"text": "hi"})
        assert res.status_code == 503


class TestAuth:
    def test_no_token_required_when_unset(self):
        client = _reload_app()
        with _mock_target():
            res = client.post("/prompt", json={"text": "hi"})
        assert res.status_code == 200

    def test_valid_token_accepted(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "secret123")
        client = _reload_app()
        with _mock_target():
            res = client.post(
                "/prompt",
                json={"text": "hi"},
                headers={"Authorization": "Bearer secret123"},
            )
        assert res.status_code == 200

    def test_wrong_token_rejected(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "secret123")
        client = _reload_app()
        res = client.post(
            "/prompt",
            json={"text": "hi"},
            headers={"Authorization": "Bearer wrong"},
        )
        assert res.status_code == 401

    def test_missing_token_rejected_when_required(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "secret123")
        client = _reload_app()
        res = client.post("/prompt", json={"text": "hi"})
        assert res.status_code == 401


class TestStaticFiles:
    def test_index_html_served(self):
        client = _reload_app()
        res = client.get("/")
        assert res.status_code == 200
        assert "VoiceClaude" in res.text
