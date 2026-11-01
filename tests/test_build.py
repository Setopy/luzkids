import build


def test_build_writes_every_page(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "DIST", tmp_path / "dist")
    build.main()
    d = tmp_path / "dist"
    for rel in ("index.html", "404.html", "manifest.json", "sw.js", "_redirects", "_headers",
                "static/js/progress.js", "en/index.html", "es/library/index.html",
                "th/series/ephesians/lesson01/index.html", "pt/privacy/index.html", "fr/404.html"):
        assert (d / rel).exists(), rel
    html = (d / "es" / "library" / "index.html").read_text(encoding="utf-8")
    assert 'href="/es/series/ephesians/"' in html
    assert "https://luzkids.org/es/library/" in html
