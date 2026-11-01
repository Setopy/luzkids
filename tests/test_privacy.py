"""The server must never store or receive data about children."""
from app import app as flask_app, db
from content_loader import load_series, load_lesson, _load_series_cached


def test_only_feedback_table_exists(app):
    assert set(db.metadata.tables) == {"feedback"}


def test_child_data_endpoints_are_gone(client):
    for method, path in [("post", "/api/complete"), ("post", "/api/ask"), ("get", "/login"),
                         ("post", "/login"), ("get", "/register"), ("post", "/register"),
                         ("get", "/logout"), ("post", "/mission/add"), ("post", "/profiles"),
                         ("get", "/certificate/lesson/ephesians/lesson01/1"),
                         ("get", "/certificate/series/ephesians/1")]:
        resp = getattr(client, method)(path)
        assert resp.status_code in (404, 405), (method, path, resp.status_code)


def test_feedback_list_hidden_without_token(client, monkeypatch):
    monkeypatch.delenv("FEEDBACK_ADMIN_TOKEN", raising=False)
    assert client.get("/feedback").status_code == 404


def test_feedback_list_needs_matching_token(client, monkeypatch):
    monkeypatch.setenv("FEEDBACK_ADMIN_TOKEN", "s3cret-token")
    assert client.get("/feedback?token=wrong").status_code == 404
    assert client.get("/feedback?token=s3cret-token").status_code == 200


def test_feedback_is_saved(client):
    from app import Feedback
    client.post("/feedback/submit", data={"message": "Typo in lesson 2", "page": "/library"})
    assert Feedback.query.count() == 1


def test_unknown_ids_are_not_cached():
    before = _load_series_cached.cache_info().currsize
    for i in range(50):
        assert load_series(f"nope{i}") is None
        assert load_series(f"../../etc{i}") is None
    assert _load_series_cached.cache_info().currsize == before


def test_lesson_must_belong_to_series():
    assert load_lesson("ephesians", "lesson01") is not None
    assert load_lesson("ephesians", "not-a-lesson") is None


def test_client_data_has_no_personal_fields(app):
    from app import client_data
    with flask_app.test_request_context("/"):
        data = client_data()
    assert set(data) == {"lang", "ranks", "badges", "s"}
