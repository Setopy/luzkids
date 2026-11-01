from app import db


def test_index_loads(client):
    assert client.get("/").status_code == 200


def test_library_loads(client):
    assert client.get("/library").status_code == 200


def test_series_page_loads(client):
    resp = client.get("/series/ephesians")
    assert resp.status_code == 200
    assert b'data-series="ephesians"' in resp.data


def test_unknown_series_404s(client):
    assert client.get("/series/not-a-real-series").status_code == 404


def test_lesson_page_has_on_device_footer(client):
    resp = client.get("/series/ephesians/lesson01")
    assert resp.status_code == 200
    assert b'id="lesson-progress"' in resp.data
    assert b'id="lesson-data"' in resp.data
    assert b"ai-question" not in resp.data


def test_manifest_is_valid_json(client):
    resp = client.get("/manifest.json")
    assert resp.status_code == 200
    assert resp.json["short_name"] == "LuzKids"


def test_on_device_pages_load(client):
    for path in ("/profiles", "/progress", "/mission", "/certificate", "/privacy"):
        assert client.get(path).status_code == 200, path


def test_dashboard_redirects_to_progress(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 301
    assert resp.headers["Location"].endswith("/progress")
