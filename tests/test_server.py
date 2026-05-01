from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from auth.providers import AuthError, VerifiedIdentity

TEST_EMAIL = "ok@example.com"
TEST_OTHER_EMAIL = "other@example.com"
GOOD_SID = "session1x"


class _FakeVerifier:
    def __init__(self, name="google", email=TEST_EMAIL, raises=False, email_unverified=False):
        self.name = name
        self._email = email
        self._raises = raises
        self._email_unverified = email_unverified

    def verify(self, id_token: str):
        if self._raises:
            raise AuthError("invalid token")
        if self._email_unverified:
            raise AuthError("email not verified by Google")
        return VerifiedIdentity(email=self._email, provider=self.name, subject="sub-123")


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client.apps.googleusercontent.com")
    monkeypatch.setenv("ALLOWED_EMAILS", TEST_EMAIL)
    monkeypatch.setenv("SESSION_SECRET", "test-secret-do-not-use-in-prod")
    monkeypatch.setenv("SESSION_COOKIE_TTL_SECONDS", "3600")
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("TARGET_URL", "http://backend:9000/chat")
    monkeypatch.setenv("TARGET_TOKEN", "")
    monkeypatch.setenv("ALLOWED_ORIGIN", "")
    monkeypatch.setenv("INSTANCE_NAME", "TestBot")
    monkeypatch.setenv("INSTANCE_COLOR", "#ff0000")
    monkeypatch.setenv("SPEECH_LANG", "de-CH")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "10000")
    monkeypatch.setenv("AUTH_LOGIN_RATE_LIMIT_PER_MINUTE", "10000")


def _reload_app(login: bool = True, verifier: _FakeVerifier | None = None):
    """Reload server module to pick up env, install a fake verifier, and (by
    default) log a TestClient in so cookies + CSRF header are set."""
    import importlib

    import server

    importlib.reload(server)
    fake = verifier or _FakeVerifier()
    server.PROVIDERS["google"] = fake
    client = TestClient(server.app)
    if login:
        _do_login(client)
    return client


def _do_login(client: TestClient, provider: str = "google", id_token: str = "any") -> int:
    res = client.post(f"/auth/login/{provider}", json={"id_token": id_token})
    if res.status_code == 200:
        # Wire CSRF header for subsequent state-changing requests.
        csrf = client.cookies.get("vg_csrf")
        if csrf:
            client.headers.update({"X-CSRF-Token": csrf})
    return res.status_code


def _mock_backend(json_body=None, status_code=200, raise_error=False, text_body=None):
    """Patch httpx.AsyncClient so /chat's outbound POST is intercepted.

    Returns (context_manager, captured) where `captured` is mutated on call
    to expose the URL, headers and JSON body that the server sent.
    """
    captured = {}

    if raise_error:
        async def post(url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            raise httpx.RequestError("connection failed")
    else:
        if json_body is None and text_body is None:
            json_body = {"response": "ok"}

        async def post(url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            if text_body is not None:
                return httpx.Response(status_code, text=text_body)
            return httpx.Response(status_code, json=json_body)

    mock_client = AsyncMock()
    mock_client.post = post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return patch("httpx.AsyncClient", return_value=mock_client), captured


# -----------------------------------------------------------------------------
# /config
# -----------------------------------------------------------------------------


class TestConfigEndpoint:
    def test_returns_instance_config(self):
        client = _reload_app()
        res = client.get("/config")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "TestBot"
        assert data["color"] == "#ff0000"
        assert data["lang"] == "de-CH"
        assert "de-CH" in data["langs"]

    def test_speech_langs_configurable(self, monkeypatch):
        monkeypatch.setenv("SPEECH_LANGS", "de-CH,en-US")
        client = _reload_app()
        data = client.get("/config").json()
        assert data["langs"] == ["de-CH", "en-US"]

    def test_default_lang_always_in_langs_list(self, monkeypatch):
        monkeypatch.setenv("SPEECH_LANG", "pt-PT")
        monkeypatch.setenv("SPEECH_LANGS", "de-CH,en-US")
        client = _reload_app()
        data = client.get("/config").json()
        assert data["langs"][0] == "pt-PT"

    def test_exposes_google_client_id_and_providers(self):
        client = _reload_app()
        data = client.get("/config").json()
        assert data["googleClientId"] == "test-client.apps.googleusercontent.com"
        assert data["providers"] == ["google"]

    def test_returns_max_length(self):
        client = _reload_app(login=False)
        data = client.get("/config").json()
        assert data["maxLength"] == 4000

    def test_max_length_overridable(self, monkeypatch):
        monkeypatch.setenv("MAX_PROMPT_LENGTH", "100")
        client = _reload_app(login=False)
        assert client.get("/config").json()["maxLength"] == 100


# -----------------------------------------------------------------------------
# /integration — single live discovery URL (endpoint map + backend contract)
# -----------------------------------------------------------------------------


class TestIntegrationEndpoint:
    """One URL backend integrators (and operators) can curl to learn the
    full HTTP surface and the backend contract — no repo checkout needed."""

    def test_served_as_markdown(self):
        client = _reload_app(login=False)
        res = client.get("/integration")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/markdown")

    def test_unauthenticated_access(self):
        client = _reload_app(login=False)
        # Public on purpose; do not require auth.
        assert client.get("/integration").status_code == 200

    def test_describes_request_and_response_shape(self):
        client = _reload_app(login=False)
        body = client.get("/integration").text
        # Cheap sanity: every contract field must appear by name.
        for token in (
            "user_email", "session_id", "metadata", '"response"',
            "TARGET_URL", "TARGET_TOKEN", "502",
        ):
            assert token in body, f"missing {token!r} in /integration"

    def test_lists_every_runtime_endpoint(self):
        # The endpoint map is the load-bearing reason this page exists —
        # if a new endpoint ships, it must be added here too.
        client = _reload_app(login=False)
        body = client.get("/integration").text
        for path in (
            "/integration", "/config", "/openapi.json", "/docs", "/redoc",
            "/chat", "/auth/login/{provider}", "/auth/logout", "/auth/me",
            "/auth/providers", "/debug-log",
        ):
            assert path in body, f"endpoint map missing {path!r}"

    def test_backend_contract_path_is_dropped(self):
        # Hard guarantee that nobody accidentally lands on the old path.
        client = _reload_app(login=False)
        assert client.get("/backend-contract").status_code == 404


# -----------------------------------------------------------------------------
# /chat — request validation
# -----------------------------------------------------------------------------


class TestChatRequestValidation:
    def test_empty_text_rejected(self):
        client = _reload_app()
        res = client.post("/chat", json={"text": "", "session_id": GOOD_SID})
        assert res.status_code == 422

    def test_too_long_rejected(self):
        client = _reload_app()
        res = client.post(
            "/chat", json={"text": "a" * 5000, "session_id": GOOD_SID}
        )
        assert res.status_code == 422

    def test_missing_text_rejected(self):
        client = _reload_app()
        res = client.post("/chat", json={"session_id": GOOD_SID})
        assert res.status_code == 422

    def test_missing_session_id_rejected(self):
        client = _reload_app()
        res = client.post("/chat", json={"text": "hi"})
        assert res.status_code == 422

    def test_short_session_id_rejected(self):
        client = _reload_app()
        res = client.post("/chat", json={"text": "hi", "session_id": "abc"})
        assert res.status_code == 422

    def test_session_id_with_control_chars_rejected(self):
        client = _reload_app()
        res = client.post(
            "/chat",
            json={"text": "hi", "session_id": "abcdefgh\n\rdroptable"},
        )
        assert res.status_code == 422

    def test_overlong_session_id_rejected(self):
        client = _reload_app()
        res = client.post(
            "/chat", json={"text": "hi", "session_id": "a" * 200}
        )
        assert res.status_code == 422

    def test_exactly_max_length_accepted(self):
        client = _reload_app()
        cm, _ = _mock_backend()
        with cm:
            res = client.post(
                "/chat", json={"text": "a" * 4000, "session_id": GOOD_SID}
            )
        assert res.status_code == 200

    def test_one_over_max_rejected(self):
        client = _reload_app()
        res = client.post(
            "/chat", json={"text": "a" * 4001, "session_id": GOOD_SID}
        )
        assert res.status_code == 422


# -----------------------------------------------------------------------------
# /chat — forwarding behaviour and contract
# -----------------------------------------------------------------------------


class TestChatForwarding:
    def test_forwards_response_text(self):
        client = _reload_app()
        cm, _ = _mock_backend({"response": "Hello from backend"})
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 200
        assert res.json() == {"response": "Hello from backend"}

    def test_payload_shape_matches_contract(self):
        client = _reload_app()
        cm, captured = _mock_backend()
        with cm:
            res = client.post(
                "/chat",
                json={"text": "ping", "session_id": GOOD_SID, "lang": "fr-CH"},
            )
        assert res.status_code == 200
        body = captured["json"]
        assert body["user"] == "ping"
        assert body["user_email"] == TEST_EMAIL
        assert body["session_id"] == GOOD_SID
        assert body["metadata"]["lang"] == "fr-CH"
        assert body["metadata"]["instance"] == "TestBot"

    def test_metadata_lang_falls_back_to_speech_lang(self):
        client = _reload_app()
        cm, captured = _mock_backend()
        with cm:
            res = client.post(
                "/chat", json={"text": "ping", "session_id": GOOD_SID}
            )
        assert res.status_code == 200
        # No `lang` in client request → server fills with SPEECH_LANG default.
        assert captured["json"]["metadata"]["lang"] == "de-CH"

    def test_user_email_always_from_session_not_client(self):
        client = _reload_app()
        cm, captured = _mock_backend()
        with cm:
            # Even if a client tries to spoof user_email, server overrides
            # with the verified session value (Pydantic ignores unknown fields).
            res = client.post(
                "/chat",
                json={
                    "text": "spoof",
                    "session_id": GOOD_SID,
                    "user_email": "attacker@evil.com",
                },
            )
        assert res.status_code == 200
        assert captured["json"]["user_email"] == TEST_EMAIL

    def test_target_token_added_when_set(self, monkeypatch):
        monkeypatch.setenv("TARGET_TOKEN", "downstream-secret")
        client = _reload_app()
        cm, captured = _mock_backend()
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 200
        assert captured["headers"]["Authorization"] == "Bearer downstream-secret"

    def test_no_target_token_means_no_auth_header(self):
        client = _reload_app()
        cm, captured = _mock_backend()
        with cm:
            client.post("/chat", json={"text": "hi", "session_id": GOOD_SID})
        assert "Authorization" not in (captured["headers"] or {})

    def test_target_url_used_verbatim(self, monkeypatch):
        monkeypatch.setenv("TARGET_URL", "http://custom-backend:1234/x/y")
        client = _reload_app()
        cm, captured = _mock_backend()
        with cm:
            client.post("/chat", json={"text": "hi", "session_id": GOOD_SID})
        assert captured["url"] == "http://custom-backend:1234/x/y"


class TestChatErrors:
    def test_no_target_configured_returns_503(self, monkeypatch):
        monkeypatch.setenv("TARGET_URL", "")
        client = _reload_app()
        res = client.post("/chat", json={"text": "hi", "session_id": GOOD_SID})
        assert res.status_code == 503

    def test_backend_unreachable_returns_502(self):
        client = _reload_app()
        cm, _ = _mock_backend(raise_error=True)
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 502
        assert "unreachable" in res.json()["detail"].lower()

    def test_backend_4xx_returns_502(self):
        client = _reload_app()
        cm, _ = _mock_backend(status_code=404, json_body={"response": "x"})
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 502

    def test_backend_5xx_returns_502(self):
        client = _reload_app()
        cm, _ = _mock_backend(status_code=500, json_body={"response": "x"})
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 502


class TestChatStrictResponseContract:
    """Strict contract: backend must return {"response": <string>}.

    Anything else (missing field, wrong type, plain text, list root) is a
    contract violation. VoxGate refuses to forward malformed payloads to the
    PWA, surfacing 502 instead.
    """

    def test_missing_response_key_returns_502(self):
        client = _reload_app()
        cm, _ = _mock_backend({"text": "old-style key"})
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 502

    def test_response_is_not_a_string_returns_502(self):
        client = _reload_app()
        cm, _ = _mock_backend({"response": {"nested": "object"}})
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 502

    def test_non_json_response_returns_502(self):
        client = _reload_app()
        cm, _ = _mock_backend(text_body="plain text", status_code=200)
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 502

    def test_list_root_returns_502(self):
        client = _reload_app()
        cm, _ = _mock_backend(["a", "b"])
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 502

    def test_empty_response_string_passes(self):
        # An empty reply is valid (e.g., backend deliberately silent).
        client = _reload_app()
        cm, _ = _mock_backend({"response": ""})
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 200
        assert res.json() == {"response": ""}


# -----------------------------------------------------------------------------
# /selftest — authenticated end-to-end probe
# -----------------------------------------------------------------------------


class TestSelftestEndpoint:
    """Authenticated diagnostic that exercises the same forward path as
    /chat and reports per-clause whether the backend honours the contract."""

    def test_requires_session(self):
        client = _reload_app(login=False)
        cm, _ = _mock_backend()
        with cm:
            res = client.post("/selftest")
        assert res.status_code == 401

    def test_requires_csrf(self):
        client = _reload_app()
        client.headers.pop("X-CSRF-Token", None)
        cm, _ = _mock_backend()
        with cm:
            res = client.post("/selftest")
        assert res.status_code == 403

    def test_no_target_url_fails_first_check(self, monkeypatch):
        monkeypatch.setenv("TARGET_URL", "")
        client = _reload_app()
        # No backend mock — the endpoint short-circuits before any HTTP.
        res = client.post("/selftest")
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is False
        # The first failed check must be the missing config.
        first = body["checks"][0]
        assert first["name"] == "target_url_configured"
        assert first["ok"] is False

    def test_happy_path_all_checks_pass(self):
        client = _reload_app()
        cm, captured = _mock_backend({"response": "pong"})
        with cm:
            res = client.post("/selftest")
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        names = [c["name"] for c in body["checks"]]
        assert names == [
            "target_url_configured",
            "backend_reachable",
            "status_2xx",
            "response_is_json",
            "response_is_object",
            "response_field_string",
        ]
        assert all(c["ok"] for c in body["checks"])
        assert body["response"]["body_preview"] == "pong"

    def test_payload_carries_test_flag(self):
        client = _reload_app()
        cm, captured = _mock_backend({"response": "ok"})
        with cm:
            client.post("/selftest")
        sent = captured["json"]
        # Backends respecting metadata.test=true can no-op.
        assert sent["metadata"]["test"] is True
        # Same shape contract as /chat.
        assert sent["user"] == "VoxGate self-test ping"
        assert sent["user_email"] == TEST_EMAIL
        assert sent["session_id"].startswith("selftest-")
        assert sent["metadata"]["instance"] == "TestBot"

    def test_unreachable_backend_reports_at_reachable_check(self):
        client = _reload_app()
        cm, _ = _mock_backend(raise_error=True)
        with cm:
            res = client.post("/selftest")
        body = res.json()
        assert body["ok"] is False
        failed = next(c for c in body["checks"] if not c["ok"])
        assert failed["name"] == "backend_reachable"

    def test_4xx_backend_reports_at_status_check(self):
        client = _reload_app()
        cm, _ = _mock_backend(status_code=403, json_body={"response": "denied"})
        with cm:
            res = client.post("/selftest")
        body = res.json()
        assert body["ok"] is False
        failed = next(c for c in body["checks"] if not c["ok"])
        assert failed["name"] == "status_2xx"
        assert "403" in failed["detail"]
        # Response body preview is preserved so the user can see what the
        # backend actually said.
        assert body["response"]["status"] == 403

    def test_non_json_backend_reports_at_json_check(self):
        client = _reload_app()
        cm, _ = _mock_backend(text_body="plain text", status_code=200)
        with cm:
            res = client.post("/selftest")
        body = res.json()
        failed = next(c for c in body["checks"] if not c["ok"])
        assert failed["name"] == "response_is_json"

    def test_wrong_shape_reports_at_field_check(self):
        client = _reload_app()
        cm, _ = _mock_backend({"text": "old-style key"})
        with cm:
            res = client.post("/selftest")
        body = res.json()
        failed = next(c for c in body["checks"] if not c["ok"])
        assert failed["name"] == "response_field_string"
        assert "text" in failed["detail"]  # the offending key is named

    def test_bearer_token_is_redacted_in_response(self, monkeypatch):
        monkeypatch.setenv("TARGET_TOKEN", "super-secret-shared-token")
        client = _reload_app()
        cm, _ = _mock_backend({"response": "ok"})
        with cm:
            res = client.post("/selftest")
        body = res.json()
        # Caller sees a placeholder, not the real token.
        assert body["request"]["headers"]["Authorization"] == "Bearer ***redacted***"
        # And the real token never appears anywhere in the response body.
        assert "super-secret-shared-token" not in res.text

    def test_no_token_set_means_no_auth_header_in_diagnostic(self):
        client = _reload_app()
        cm, _ = _mock_backend({"response": "ok"})
        with cm:
            res = client.post("/selftest")
        headers = res.json()["request"]["headers"]
        assert "Authorization" not in headers

    def test_target_token_actually_transmitted(self, monkeypatch):
        # Redaction (above) is not enough — we also need to assert that
        # the *real* token reaches the backend. Otherwise we might mask
        # ourselves into silently sending the placeholder.
        monkeypatch.setenv("TARGET_TOKEN", "real-shared-secret-xyz")
        client = _reload_app()
        cm, captured = _mock_backend({"response": "ok"})
        with cm:
            client.post("/selftest")
        sent_auth = captured["headers"].get("Authorization")
        assert sent_auth == "Bearer real-shared-secret-xyz"

    def test_primitive_root_reports_at_object_check(self):
        # Backend returned a bare JSON string instead of an object.
        client = _reload_app()
        cm, _ = _mock_backend(json_body="just a string", status_code=200)
        with cm:
            res = client.post("/selftest")
        body = res.json()
        assert body["ok"] is False
        failed = next(c for c in body["checks"] if not c["ok"])
        assert failed["name"] == "response_is_object"
        assert "str" in failed["detail"]

    def test_response_is_explicit_null_reports_at_field_check(self):
        # Key present but value null — caught by the same check as missing.
        client = _reload_app()
        cm, _ = _mock_backend({"response": None})
        with cm:
            res = client.post("/selftest")
        body = res.json()
        failed = next(c for c in body["checks"] if not c["ok"])
        assert failed["name"] == "response_field_string"
        assert "NoneType" in failed["detail"]

    def test_diagnostic_envelope_invariant(self, monkeypatch):
        # Every response — pass or fail, early or late — keeps the same
        # top-level shape. Saves frontend/script consumers from defensive
        # branching.
        monkeypatch.setenv("TARGET_URL", "")
        client = _reload_app()
        early_failure = client.post("/selftest").json()
        for key in ("ok", "checks", "request", "response"):
            assert key in early_failure, f"{key} missing on early failure"

        client2 = _reload_app()
        cm, _ = _mock_backend({"response": "ok"})
        with cm:
            success = client2.post("/selftest").json()
        for key in ("ok", "checks", "request", "response"):
            assert key in success, f"{key} missing on success"

    def test_subject_to_chat_rate_limit(self, monkeypatch):
        # /selftest must share /chat's bucket — otherwise it could be
        # used to bypass rate limiting and flood the backend.
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
        client = _reload_app()
        cm, _ = _mock_backend({"response": "ok"})
        with cm:
            for _ in range(3):
                assert client.post("/selftest").status_code == 200
            res = client.post("/selftest")
        assert res.status_code == 429

    def test_chat_and_selftest_share_one_bucket(self, monkeypatch):
        # Two /selftest + two /chat = 4 → exceeds limit 3 = 429 on the
        # last one regardless of which endpoint we hit.
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
        client = _reload_app()
        cm, _ = _mock_backend({"response": "ok"})
        chat_body = {"text": "hi", "session_id": GOOD_SID}
        with cm:
            assert client.post("/selftest").status_code == 200
            assert client.post("/chat", json=chat_body).status_code == 200
            assert client.post("/selftest").status_code == 200
            res = client.post("/chat", json=chat_body)
        assert res.status_code == 429


# -----------------------------------------------------------------------------
# Auth + session
# -----------------------------------------------------------------------------


class TestAuthLogin:
    def test_login_accepted_when_allowlisted(self):
        client = _reload_app(login=False)
        status = _do_login(client)
        assert status == 200
        assert client.cookies.get("vg_session")
        assert client.cookies.get("vg_csrf")

    def test_login_rejected_when_not_allowlisted(self):
        client = _reload_app(login=False, verifier=_FakeVerifier(email=TEST_OTHER_EMAIL))
        status = _do_login(client)
        assert status == 403

    def test_login_rejected_when_email_not_verified(self):
        client = _reload_app(login=False, verifier=_FakeVerifier(email_unverified=True))
        status = _do_login(client)
        assert status == 401

    def test_invalid_signature_rejected(self):
        client = _reload_app(login=False, verifier=_FakeVerifier(raises=True))
        status = _do_login(client)
        assert status == 401

    def test_unknown_provider_returns_404(self):
        client = _reload_app(login=False)
        res = client.post("/auth/login/microsoft", json={"id_token": "x"})
        assert res.status_code == 404

    def test_me_returns_email_when_authenticated(self):
        client = _reload_app()
        res = client.get("/auth/me")
        assert res.status_code == 200
        assert res.json() == {"email": TEST_EMAIL, "provider": "google"}

    def test_me_unauthenticated(self):
        client = _reload_app(login=False)
        res = client.get("/auth/me")
        assert res.status_code == 401

    def test_logout_clears_cookies(self):
        client = _reload_app()
        res = client.post("/auth/logout")
        assert res.status_code == 200
        client.headers.pop("X-CSRF-Token", None)
        res = client.get("/auth/me")
        assert res.status_code == 401

    def test_providers_endpoint_lists_google(self):
        client = _reload_app(login=False)
        res = client.get("/auth/providers")
        assert res.status_code == 200
        assert res.json() == {"providers": ["google"]}


class TestSessionAuthCSRF:
    def test_chat_requires_session(self):
        client = _reload_app(login=False)
        cm, _ = _mock_backend()
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 401

    def test_chat_requires_csrf(self):
        client = _reload_app()
        client.headers.pop("X-CSRF-Token", None)
        cm, _ = _mock_backend()
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 403

    def test_email_removed_from_allowlist_blocks_subsequent_requests(self):
        client = _reload_app()
        import server

        server._auth_config.allowed_emails.clear()
        cm, _ = _mock_backend()
        with cm:
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 403

    def test_provider_binding_in_allowlist(self):
        import server

        client = _reload_app(login=False)
        server.PROVIDERS["microsoft"] = _FakeVerifier(name="microsoft", email=TEST_EMAIL)
        server._auth_config.allowed_emails[TEST_EMAIL] = "google"
        assert _do_login(client, provider="google") == 200
        client.cookies.clear()
        client.headers.pop("X-CSRF-Token", None)
        assert _do_login(client, provider="microsoft") == 403


class TestRateLimit:
    def test_rate_limit_triggers_429(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
        client = _reload_app()
        cm, _ = _mock_backend()
        with cm:
            for _ in range(3):
                res = client.post(
                    "/chat", json={"text": "hi", "session_id": GOOD_SID}
                )
                assert res.status_code == 200
            res = client.post(
                "/chat", json={"text": "hi", "session_id": GOOD_SID}
            )
        assert res.status_code == 429

    def test_login_rate_limit(self, monkeypatch):
        monkeypatch.setenv("AUTH_LOGIN_RATE_LIMIT_PER_MINUTE", "2")
        client = _reload_app(login=False)
        for _ in range(2):
            assert _do_login(client) == 200
            client.cookies.clear()
            client.headers.pop("X-CSRF-Token", None)
        res = client.post("/auth/login/google", json={"id_token": "x"})
        assert res.status_code == 429

    def test_static_assets_not_rate_limited(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
        client = _reload_app(login=False)
        for _ in range(10):
            assert client.get("/config").status_code == 200


class TestSessionSecretAutogen:
    def test_auto_generates_session_secret_when_empty(self, monkeypatch):
        monkeypatch.setenv("SESSION_SECRET", "")
        _reload_app(login=False)
        import server

        assert len(server.SESSION_SECRET) >= 32

    def test_explicit_secret_wins_over_autogen(self, monkeypatch):
        monkeypatch.setenv("SESSION_SECRET", "my-very-secret-value")
        _reload_app(login=False)
        import server

        assert server.SESSION_SECRET == "my-very-secret-value"


class TestProxyHeaderTrust:
    def test_xff_ignored_by_default(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
        client = _reload_app()
        cm, _ = _mock_backend()
        with cm:
            for xff in ["1.1.1.1", "2.2.2.2", "3.3.3.3"]:
                client.post(
                    "/chat",
                    json={"text": "hi", "session_id": GOOD_SID},
                    headers={"X-Forwarded-For": xff},
                )
            res = client.post(
                "/chat",
                json={"text": "hi", "session_id": GOOD_SID},
                headers={"X-Forwarded-For": "4.4.4.4"},
            )
        assert res.status_code == 429

    def test_xff_used_when_trusted(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
        monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
        client = _reload_app()
        cm, _ = _mock_backend()
        with cm:
            for xff in ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]:
                res = client.post(
                    "/chat",
                    json={"text": "hi", "session_id": GOOD_SID},
                    headers={"X-Forwarded-For": xff},
                )
                assert res.status_code == 200


# -----------------------------------------------------------------------------
# Static, security headers, CORS, allowlist parsing, cookies, origins
# -----------------------------------------------------------------------------


class TestStaticFiles:
    def test_index_html_served(self):
        client = _reload_app(login=False)
        res = client.get("/")
        assert res.status_code == 200
        assert "VoxGate" in res.text

    @pytest.mark.parametrize(
        "path,fragment",
        [
            ("/app.js", "instanceConfig"),
            ("/styles.css", ":root"),
            ("/manifest.json", "name"),
            ("/sw.js", ""),
            ("/icon.svg", "<svg"),
        ],
    )
    def test_pwa_asset_served(self, path, fragment):
        client = _reload_app(login=False)
        res = client.get(path)
        assert res.status_code == 200
        if fragment:
            assert fragment in res.text


class TestSecurityHeaders:
    def test_csp_and_headers_set(self):
        client = _reload_app(login=False)
        res = client.get("/config")
        assert "content-security-policy" in {k.lower() for k in res.headers}
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert res.headers["X-Frame-Options"] == "DENY"
        assert "strict-origin" in res.headers["Referrer-Policy"]
        assert "microphone=(self)" in res.headers["Permissions-Policy"]

    def test_csp_blocks_inline_script(self):
        client = _reload_app(login=False)
        res = client.get("/config")
        csp = res.headers["Content-Security-Policy"]
        assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]

    def test_csp_allows_google_identity_services(self):
        client = _reload_app(login=False)
        csp = client.get("/config").headers["Content-Security-Policy"]
        assert "https://accounts.google.com/gsi/client" in csp
        assert "frame-src https://accounts.google.com/gsi/" in csp

    def test_pwa_assets_send_no_cache(self):
        # Cache busting: PWA assets must revalidate so families don't get
        # stuck on stale JS after a deploy. ETag handles the bandwidth side.
        client = _reload_app(login=False)
        for path in ("/", "/app.js", "/styles.css"):
            res = client.get(path)
            assert res.headers.get("Cache-Control") == "no-cache", path

    def test_service_worker_keeps_default_cache_headers(self):
        # sw.js should not be force-revalidated — the SW lifecycle handles
        # its own update mechanism. Avoid double cache layers fighting.
        client = _reload_app(login=False)
        res = client.get("/sw.js")
        assert res.status_code == 200
        # Either no Cache-Control, or anything other than `no-cache`.
        assert res.headers.get("Cache-Control") != "no-cache"


class TestCORS:
    def test_allowed_origin_passes_through(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGIN", "https://allowed.example.com")
        client = _reload_app(login=False)
        res = client.options(
            "/config",
            headers={
                "Origin": "https://allowed.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert res.headers.get("access-control-allow-origin") == "https://allowed.example.com"

    def test_other_origin_blocked(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGIN", "https://allowed.example.com")
        client = _reload_app(login=False)
        res = client.options(
            "/config",
            headers={
                "Origin": "https://attacker.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert res.headers.get("access-control-allow-origin") != "https://attacker.example.com"


class TestAllowlistParsing:
    def test_provider_binding_parsed(self, monkeypatch):
        monkeypatch.setenv(
            "ALLOWED_EMAILS", "alice@example.com:google,bob@example.com"
        )
        _reload_app(login=False)
        import server

        assert server.ALLOWED_EMAILS == {
            "alice@example.com": "google",
            "bob@example.com": None,
        }

    def test_emails_lowercased_and_trimmed(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_EMAILS", "  Alice@Example.COM  , BOB@x.io ")
        _reload_app(login=False)
        import server

        assert "alice@example.com" in server.ALLOWED_EMAILS
        assert "bob@x.io" in server.ALLOWED_EMAILS

    def test_multi_colon_entry_rejected(self, monkeypatch):
        monkeypatch.setenv(
            "ALLOWED_EMAILS", "alice@example.com:google:extra,bob@example.com"
        )
        _reload_app(login=False)
        import server

        assert "alice@example.com" not in server.ALLOWED_EMAILS
        assert "bob@example.com" in server.ALLOWED_EMAILS


class TestCookieSecurity:
    def test_session_cookie_attributes(self):
        client = _reload_app(login=False)
        res = client.post("/auth/login/google", json={"id_token": "x"})
        assert res.status_code == 200
        cookies = res.headers.get_list("set-cookie")
        session_cookie = next((c for c in cookies if c.startswith("vg_session=")), "")
        csrf_cookie = next((c for c in cookies if c.startswith("vg_csrf=")), "")
        assert session_cookie, "vg_session cookie not set"
        assert csrf_cookie, "vg_csrf cookie not set"
        assert "httponly" in session_cookie.lower()
        assert "samesite=strict" in session_cookie.lower()
        assert "httponly" not in csrf_cookie.lower()
        assert "samesite=strict" in csrf_cookie.lower()

    def test_session_cookie_secure_when_configured(self, monkeypatch):
        monkeypatch.setenv("COOKIE_SECURE", "1")
        client = _reload_app(login=False)
        res = client.post("/auth/login/google", json={"id_token": "x"})
        cookies = res.headers.get_list("set-cookie")
        session_cookie = next(c for c in cookies if c.startswith("vg_session="))
        assert "Secure" in session_cookie

    def test_tampered_session_cookie_rejected(self):
        client = _reload_app()
        good = client.cookies.get("vg_session")
        assert good
        mid = len(good) // 2
        bad = good[:mid] + ("A" if good[mid] != "A" else "B") + good[mid + 1:]
        client.cookies.clear()
        res = client.get(
            "/auth/me",
            headers={"Cookie": f"vg_session={bad}"},
        )
        assert res.status_code == 401

    def test_logout_clears_both_cookies(self):
        client = _reload_app()
        res = client.post("/auth/logout")
        assert res.status_code == 200
        cookies = res.headers.get_list("set-cookie")
        cleared = "\n".join(cookies).lower()
        assert "vg_session=" in cleared
        assert "vg_csrf=" in cleared
        assert "max-age=0" in cleared or "expires=thu, 01 jan 1970" in cleared


class TestOriginCheck:
    def test_login_blocked_from_foreign_origin(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGIN", "https://app.example.com")
        client = _reload_app(login=False)
        res = client.post(
            "/auth/login/google",
            json={"id_token": "x"},
            headers={"Origin": "https://attacker.example.com"},
        )
        assert res.status_code == 403

    def test_login_accepted_from_allowed_origin(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGIN", "https://app.example.com")
        client = _reload_app(login=False)
        res = client.post(
            "/auth/login/google",
            json={"id_token": "x"},
            headers={"Origin": "https://app.example.com"},
        )
        assert res.status_code == 200

    def test_login_falls_back_to_referer_when_no_origin(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGIN", "https://app.example.com")
        client = _reload_app(login=False)
        res = client.post(
            "/auth/login/google",
            json={"id_token": "x"},
            headers={"Referer": "https://app.example.com/some/path?x=1"},
        )
        assert res.status_code == 200

    def test_login_unrestricted_when_allowed_origin_empty(self):
        client = _reload_app(login=False)
        res = client.post(
            "/auth/login/google",
            json={"id_token": "x"},
            headers={"Origin": "https://anywhere.example.com"},
        )
        assert res.status_code == 200

    def test_logout_blocked_from_foreign_origin(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGIN", "https://app.example.com")
        client = _reload_app(login=False)
        client.post(
            "/auth/login/google",
            json={"id_token": "x"},
            headers={"Origin": "https://app.example.com"},
        )
        csrf = client.cookies.get("vg_csrf")
        client.headers.update({"X-CSRF-Token": csrf})
        res = client.post(
            "/auth/logout",
            headers={"Origin": "https://attacker.example.com"},
        )
        assert res.status_code == 403


class TestLogoutCSRF:
    def test_logout_requires_csrf_when_logged_in(self):
        client = _reload_app()
        client.headers.pop("X-CSRF-Token", None)
        res = client.post("/auth/logout")
        assert res.status_code == 403

    def test_logout_idempotent_when_not_logged_in(self):
        client = _reload_app(login=False)
        res = client.post("/auth/logout")
        assert res.status_code == 200

    def test_logout_with_valid_csrf_succeeds(self):
        client = _reload_app()
        res = client.post("/auth/logout")
        assert res.status_code == 200
        res = client.get("/auth/me")
        assert res.status_code == 401
