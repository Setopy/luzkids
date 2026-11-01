"""The site must never store or receive data about children."""
import app as app_module
from app import app as flask_app
from content_loader import load_series, load_lesson, _load_series_cached


def test_no_database():
    assert not hasattr(app_module, "db")
    assert not any(k.startswith("SQLALCHEMY") for k in flask_app.config)


def test_no_server_endpoints_accept_data():
    for rule in flask_app.url_map.iter_rules():
        assert rule.methods <= {"GET", "HEAD", "OPTIONS"}, rule


def test_child_data_endpoints_are_gone(client):
    for method, path in [("post", "/api/complete"), ("post", "/api/ask"), ("get", "/login"),
                         ("get", "/register"), ("get", "/logout"), ("post", "/mission/add"),
                         ("post", "/feedback/submit"), ("get", "/certificate/lesson/ephesians/lesson01/1")]:
        resp = getattr(client, method)(path, follow_redirects=True)
        assert resp.status_code in (404, 405), (method, path, resp.status_code)


def test_pages_have_no_forms_or_cookies(client):
    resp = client.get("/en/profiles/")
    assert "Set-Cookie" not in resp.headers
    resp = client.get("/en/series/ephesians/lesson01/")
    assert "Set-Cookie" not in resp.headers


def test_unknown_ids_are_not_cached():
    before = _load_series_cached.cache_info().currsize
    for i in range(50):
        assert load_series(f"nope{i}") is None
        assert load_series(f"../../etc{i}") is None
    assert _load_series_cached.cache_info().currsize == before


def test_lesson_must_belong_to_series():
    assert load_lesson("ephesians", "lesson01") is not None
    assert load_lesson("ephesians", "not-a-lesson") is None


def test_client_data_has_no_personal_fields():
    from app import client_data
    with flask_app.test_request_context("/es/library/"):
        from flask import g
        g.lang = "es"
        data = client_data()
    assert set(data) == {"lang", "base", "ranks", "badges", "s"}
    assert data["base"] == "/es"
