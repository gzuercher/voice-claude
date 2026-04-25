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
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("VOXGATE_ALLOW_OPEN", "1")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "10000")


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


class _FakeTextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeMessage:
    def __init__(self, text):
        self.content = [_FakeTextBlock(text)]


def _mock_anthropic(reply="Hi there", raise_error=False):
    if raise_error:
        create = AsyncMock(side_effect=RuntimeError("boom"))
    else:
        create = AsyncMock(return_value=_FakeMessage(reply))
    fake_client = type("C", (), {})()
    fake_client.messages = type("M", (), {"create": create})()
    return fake_client, create


class TestClaudeEndpoint:
    def test_no_api_key_returns_503(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        client = _reload_app()
        res = client.post("/claude", json={"text": "hi", "session_id": "session1x"})
        assert res.status_code == 503

    def test_returns_assistant_reply(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        client = _reload_app()
        import server

        fake, _ = _mock_anthropic("Hello!")
        server._anthropic_client = fake
        res = client.post("/claude", json={"text": "hi", "session_id": "session1x"})
        assert res.status_code == 200
        assert res.json()["response"] == "Hello!"

    def test_session_history_persists(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        client = _reload_app()
        import server

        snapshots = []

        async def fake_create(**kwargs):
            snapshots.append([dict(m) for m in kwargs["messages"]])
            return _FakeMessage("reply")

        fake = type("C", (), {})()
        msgs_obj = type("M", (), {})()
        msgs_obj.create = fake_create
        fake.messages = msgs_obj
        server._anthropic_client = fake
        client.post("/claude", json={"text": "first", "session_id": "abcdefgh"})
        client.post("/claude", json={"text": "second", "session_id": "abcdefgh"})
        msgs = snapshots[1]
        assert msgs[0] == {"role": "user", "content": "first"}
        assert msgs[1] == {"role": "assistant", "content": "reply"}
        assert msgs[2] == {"role": "user", "content": "second"}

    def test_history_truncated_to_max(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        client = _reload_app()
        import server

        fake, _ = _mock_anthropic("ok")
        server._anthropic_client = fake
        for i in range(15):
            res = client.post(
                "/claude", json={"text": f"m{i}", "session_id": "trunc123"}
            )
            assert res.status_code == 200
        assert len(server._sessions["trunc123"]["messages"]) <= server.SESSION_MAX_MESSAGES

    def test_sessions_isolated(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        client = _reload_app()
        import server

        snapshots = []

        async def fake_create(**kwargs):
            snapshots.append([dict(m) for m in kwargs["messages"]])
            return _FakeMessage("ok")

        fake = type("C", (), {})()
        msgs_obj = type("M", (), {})()
        msgs_obj.create = fake_create
        fake.messages = msgs_obj
        server._anthropic_client = fake
        client.post("/claude", json={"text": "a-msg", "session_id": "sessionAA"})
        client.post("/claude", json={"text": "b-msg", "session_id": "sessionBB"})
        assert snapshots[1] == [{"role": "user", "content": "b-msg"}]

    def test_api_error_rolls_back_history(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        client = _reload_app()
        import server

        fake, _ = _mock_anthropic(raise_error=True)
        server._anthropic_client = fake
        res = client.post("/claude", json={"text": "hi", "session_id": "errsess1"})
        assert res.status_code == 502
        assert server._sessions.get("errsess1", {"messages": []})["messages"] == []

    def test_missing_session_id_rejected(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        client = _reload_app()
        res = client.post("/claude", json={"text": "hi"})
        assert res.status_code == 422

    def test_auth_required(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "secret123")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        client = _reload_app()
        res = client.post("/claude", json={"text": "hi", "session_id": "sessshort"})
        assert res.status_code == 401


class TestStaticFiles:
    def test_index_html_served(self):
        client = _reload_app()
        res = client.get("/")
        assert res.status_code == 200
        assert "VoxGate" in res.text


class TestSecurityHeaders:
    def test_csp_and_headers_set(self):
        client = _reload_app()
        res = client.get("/config")
        assert "content-security-policy" in {k.lower() for k in res.headers}
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert res.headers["X-Frame-Options"] == "DENY"
        assert "strict-origin" in res.headers["Referrer-Policy"]
        assert "microphone=(self)" in res.headers["Permissions-Policy"]

    def test_csp_blocks_inline_script(self):
        client = _reload_app()
        res = client.get("/config")
        csp = res.headers["Content-Security-Policy"]
        assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]


class TestSessionIdValidation:
    def test_short_session_id_rejected(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        client = _reload_app()
        res = client.post("/claude", json={"text": "hi", "session_id": "abc"})
        assert res.status_code == 422

    def test_session_id_with_control_chars_rejected(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        client = _reload_app()
        res = client.post(
            "/claude", json={"text": "hi", "session_id": "abcdefgh\n\rdroptable"}
        )
        assert res.status_code == 422

    def test_overlong_session_id_rejected(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        client = _reload_app()
        res = client.post(
            "/claude", json={"text": "hi", "session_id": "a" * 200}
        )
        assert res.status_code == 422


class TestRateLimit:
    def test_rate_limit_triggers_429(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        client = _reload_app()
        import server

        fake, _ = _mock_anthropic("ok")
        server._anthropic_client = fake
        for _ in range(3):
            res = client.post(
                "/claude", json={"text": "hi", "session_id": "ratelmt1"}
            )
            assert res.status_code == 200
        res = client.post("/claude", json={"text": "hi", "session_id": "ratelmt1"})
        assert res.status_code == 429


class TestSessionTTL:
    def test_expired_sessions_evicted(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        monkeypatch.setenv("SESSION_TTL_SECONDS", "1")
        client = _reload_app()
        import server

        fake, _ = _mock_anthropic("ok")
        server._anthropic_client = fake
        client.post("/claude", json={"text": "hi", "session_id": "ttltest1"})
        assert "ttltest1" in server._sessions
        server._sessions["ttltest1"]["last_seen"] -= 10
        client.post("/claude", json={"text": "again", "session_id": "ttltest2"})
        assert "ttltest1" not in server._sessions
        assert "ttltest2" in server._sessions

    def test_max_sessions_cap(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        monkeypatch.setenv("MAX_SESSIONS", "3")
        client = _reload_app()
        import server

        fake, _ = _mock_anthropic("ok")
        server._anthropic_client = fake
        for i in range(5):
            sid = f"capacity{i}"
            client.post("/claude", json={"text": "hi", "session_id": sid})
            server._sessions[sid]["last_seen"] -= (5 - i)
        assert len(server._sessions) <= 3


class TestFailLoudStartup:
    def test_refuses_when_anthropic_set_and_no_token(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxx")
        monkeypatch.setenv("VOXGATE_ALLOW_OPEN", "0")
        with pytest.raises(SystemExit):
            _reload_app()

    def test_refuses_when_target_set_and_no_token(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "")
        monkeypatch.setenv("TARGET_URL", "http://x/y")
        monkeypatch.setenv("VOXGATE_ALLOW_OPEN", "0")
        with pytest.raises(SystemExit):
            _reload_app()

    def test_starts_with_token_set(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "secret")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxx")
        monkeypatch.setenv("VOXGATE_ALLOW_OPEN", "0")
        client = _reload_app()
        res = client.get("/config")
        assert res.status_code == 200


class TestTimingSafeAuth:
    def test_uses_compare_digest(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "secret123")
        client = _reload_app()
        with _mock_target():
            res = client.post(
                "/prompt",
                json={"text": "hi"},
                headers={"Authorization": "Bearer secret123"},
            )
        assert res.status_code == 200

    def test_empty_credentials_rejected(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "secret")
        client = _reload_app()
        res = client.post(
            "/prompt", json={"text": "hi"}, headers={"Authorization": "Bearer "}
        )
        assert res.status_code == 401
