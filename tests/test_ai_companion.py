import json
from types import SimpleNamespace

import groq
import httpx
import pytest

from app import User, db, limiter


@pytest.fixture
def signed_in(client, app, monkeypatch):
    limiter.reset()
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-a-secret")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    with app.app_context():
        user = User(email="ai-test@example.test", display_name="Test", password_hash="unused")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    yield client
    limiter.reset()


def ask(client, **overrides):
    return client.post("/api/ask", json={
        "question": "Why did Paul write this letter?",
        "series_id": "ephesians", "lesson_id": "lesson01", "lang": "en",
        **overrides,
    })


def completion(content="God loves us.", choices=True):
    return {"id": "test", "object": "chat.completion", "created": 1,
            "model": "openai/gpt-oss-20b", "choices": [
                {"index": 0, "message": {"role": "assistant", "content": content,
                                       "reasoning": "Private reasoning must never be displayed."},
                 "finish_reason": "stop"}] if choices else []}


@pytest.fixture
def provider(monkeypatch):
    original = groq.Groq
    state = SimpleNamespace(calls=[], options=[], handler=lambda req: httpx.Response(200, json=completion()))

    def create(**kwargs):
        state.options.append(kwargs)
        def handle(req):
            state.calls.append(json.loads(req.content))
            return state.handler(req)
        return original(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr(groq, "Groq", create)
    return state


def test_migrates_retired_model_and_returns_only_answer(signed_in, provider):
    def handler(req):
        if json.loads(req.content)["model"] == "llama-3.1-8b-instant":
            return httpx.Response(400, json={"error": {
                "message": "The model has been decommissioned", "code": "model_decommissioned"}})
        return httpx.Response(200, json=completion("  God loves us.  "))
    provider.handler = handler
    response = ask(signed_in)
    assert response.status_code == 200
    assert response.json == {"ok": True, "answer": "God loves us."}
    sent = provider.calls[0]
    assert sent["model"] == "openai/gpt-oss-20b"
    assert sent["reasoning_effort"] == "low"
    assert sent["include_reasoning"] is False
    assert sent["max_completion_tokens"] >= 1024
    assert "Deeper Life Bible Church" in sent["messages"][0]["content"]
    assert provider.options[0]["max_retries"] == 0
    assert provider.options[0]["timeout"] < 30


def test_model_override(signed_in, provider, monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
    assert ask(signed_in).status_code == 200
    assert provider.calls[0]["model"] == "openai/gpt-oss-120b"


def test_non_reasoning_model_override(signed_in, provider, monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "enterprise-model")
    assert ask(signed_in).status_code == 200
    assert "reasoning_effort" not in provider.calls[0]
    assert "include_reasoning" not in provider.calls[0]


@pytest.mark.parametrize("status,code,expected", [
    (400, "model_decommissioned", "model_unavailable"),
    (404, "model_not_found", "model_unavailable"),
    (401, "invalid_api_key", "provider_auth"),
    (403, "model_permission_blocked", "provider_auth"),
    (429, "rate_limit_exceeded", "provider_rate_limited"),
    (500, "server_error", "provider_error"),
])
def test_provider_failure_is_not_success(signed_in, provider, caplog, status, code, expected):
    provider.handler = lambda req: httpx.Response(status, json={
        "error": {"message": "sensitive upstream details", "code": code}})
    response = ask(signed_in)
    assert response.status_code == 503
    assert response.json["ok"] is False
    assert response.json["error"] == expected
    assert len(provider.calls) == 1
    assert "sensitive upstream details" not in response.text + caplog.text
    assert "test-key-not-a-secret" not in response.text + caplog.text
    assert code in caplog.text


@pytest.mark.parametrize("failure,code", [
    (httpx.ReadTimeout, "provider_timeout"),
    (httpx.ConnectError, "provider_connection"),
])
def test_network_failures(signed_in, provider, failure, code):
    def fail(req):
        raise failure("network failure", request=req)
    provider.handler = fail
    response = ask(signed_in)
    assert response.status_code == 503
    assert response.json["error"] == code
    assert len(provider.calls) == 1


@pytest.mark.parametrize("body", [completion(None), completion(""), completion("   "), completion(choices=False)])
def test_empty_completion_is_not_success(signed_in, provider, body):
    provider.handler = lambda req: httpx.Response(200, json=body)
    response = ask(signed_in)
    assert response.status_code == 503
    assert response.json["error"] == "empty_answer"


@pytest.mark.parametrize("key", ["", "   "])
def test_missing_key(signed_in, provider, monkeypatch, key):
    monkeypatch.setenv("GROQ_API_KEY", key)
    response = ask(signed_in)
    assert response.status_code == 503
    assert response.json["error"] == "not_configured"
    assert provider.calls == []


def test_login_required(client, provider):
    limiter.reset()
    response = ask(client)
    assert response.status_code == 401
    assert response.json["ok"] is False
    assert provider.calls == []


@pytest.mark.parametrize("body", [None, [], "question", {"question": None}, {"question": []},
                                 {"question": " "}, {"question": "Hello", "series_id": []}])
def test_invalid_input(signed_in, provider, body):
    response = signed_in.post("/api/ask", data=json.dumps(body), content_type="application/json")
    assert response.status_code == 400
    assert response.is_json
    assert provider.calls == []


def test_language_and_question_limit(signed_in, provider):
    assert ask(signed_in, lang="es", question="a" * 400).status_code == 200
    assert "Answer in Spanish" in provider.calls[0]["messages"][0]["content"]
    assert len(provider.calls[0]["messages"][1]["content"]) == 300


def test_app_rate_limit_remains_enforced(signed_in, provider):
    for _ in range(6):
        assert ask(signed_in).status_code == 200
    response = ask(signed_in)
    assert response.status_code == 429
    assert response.json["ok"] is False
    assert response.json["rate_limited"] is True
    assert len(provider.calls) == 6

