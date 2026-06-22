def test_index_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_library_loads(client):
    resp = client.get("/library")
    assert resp.status_code == 200


def test_series_page_loads(client):
    resp = client.get("/series/ephesians")
    assert resp.status_code == 200


def test_unknown_series_404s(client):
    resp = client.get("/series/not-a-real-series")
    assert resp.status_code == 404


def test_manifest_is_valid_json(client):
    resp = client.get("/manifest.json")
    assert resp.status_code == 200
    assert resp.json["short_name"] == "LuzKids"


def test_login_page_loads(client):
    resp = client.get("/login")
    assert resp.status_code == 200


def test_api_complete_requires_login(client):
    resp = client.post("/api/complete", json={"series_id": "ephesians", "lesson_id": "lesson01"})
    assert resp.status_code in (302, 401)
