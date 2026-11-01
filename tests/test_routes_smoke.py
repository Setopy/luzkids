import pytest

from app import SUPPORTED_LANGS


def test_root_redirects_to_a_language(client):
    resp = client.get("/", headers={"Accept-Language": "es"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/es/")


@pytest.mark.parametrize("lang", SUPPORTED_LANGS)
def test_main_pages_load_in_every_language(client, lang):
    for page in ("", "library/", "songs/", "series/ephesians/", "series/ephesians/lesson01/",
                 "profiles/", "progress/", "mission/", "certificate/", "privacy/"):
        resp = client.get(f"/{lang}/{page}")
        assert resp.status_code == 200, (lang, page)
        assert f'<html lang="{lang}">'.encode() in resp.data


def test_links_keep_the_language(client):
    html = client.get("/es/library/").data.decode()
    assert 'href="/es/series/ephesians/"' in html
    assert 'value="/en/library/"' in html         # language switcher
    assert '"base": "/es"' in html or '"base":"/es"' in html


def test_unknown_language_or_series_404s(client):
    assert client.get("/xx/library/").status_code == 404
    assert client.get("/en/series/not-a-real-series/").status_code == 404


def test_lesson_page_has_on_device_footer(client):
    resp = client.get("/en/series/ephesians/lesson01/")
    assert b'id="lesson-progress"' in resp.data
    assert b'id="lesson-data"' in resp.data
    assert b"ai-question" not in resp.data


def test_series_page_marks_lessons_for_progress_js(client):
    resp = client.get("/en/series/ephesians/")
    assert b'data-series="ephesians"' in resp.data


def test_manifest_is_valid_json(client):
    resp = client.get("/manifest.json")
    assert resp.status_code == 200
    assert resp.json["short_name"] == "LuzKids"


def test_feedback_is_an_email_link(client):
    html = client.get("/en/library/").data.decode()
    assert "mailto:" in html
    assert "<form" not in html
