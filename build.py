"""Build the static LuzKids site into dist/ for Cloudflare Pages.

    pip install -r requirements.txt
    python build.py            # writes dist/

Every page is rendered once per language (/en/, /es/, /fr/, /pt/, /th/)
using the existing translations in content/ and the templates. Nothing is
translated here. static/ is copied once and shared by all languages.
"""
import json
import shutil
import sys
from pathlib import Path

from app import app, LANGUAGES, SUPPORTED_LANGS, manifest_data
from content_loader import load_all_series

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
SITE = "https://luzkids.org"


def pages():
    """Every page address, without the language prefix."""
    yield "/"
    for p in ("library", "songs", "profiles", "progress", "mission", "certificate", "privacy"):
        yield f"/{p}/"
    for s in load_all_series():
        yield f"/series/{s['id']}/"
        for l in s["lessons"]:
            yield f"/series/{s['id']}/{l['id']}/"


def write(rel, data):
    out = DIST / rel.lstrip("/")
    if rel.endswith("/"):
        out = out / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "static", DIST / "static")
    shutil.copy(ROOT / "static" / "sw.js", DIST / "sw.js")
    (DIST / "manifest.json").write_text(json.dumps(manifest_data(), ensure_ascii=False, indent=1), encoding="utf-8")

    client = app.test_client()
    count = 0
    for lang in SUPPORTED_LANGS:
        for page in pages():
            url = f"/{lang}{page}"
            resp = client.get(url, base_url=SITE)
            if resp.status_code != 200:
                sys.exit(f"build failed: {url} returned {resp.status_code}")
            write(url, resp.data)
            count += 1
        resp = client.get(f"/{lang}/__missing__/", base_url=SITE)
        write(f"/{lang}/404.html", resp.data)
    # Site-wide 404 (Cloudflare Pages serves the nearest 404.html).
    write("/404.html", (DIST / "en" / "404.html").read_bytes())

    # Language picker at the root: follows the browser's language.
    langs = json.dumps(list(SUPPORTED_LANGS))
    links = "".join(f'<li><a href="/{c}/">{n}</a></li>' for c, n in LANGUAGES.items())
    write("/index.html", f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LuzKids</title><link rel="manifest" href="/manifest.json">
<script>(function(){{var L={langs},n=(navigator.languages||[navigator.language||"en"]);
for(var i=0;i<n.length;i++){{var c=String(n[i]).slice(0,2).toLowerCase();if(L.indexOf(c)>=0){{location.replace("/"+c+"/");return;}}}}
location.replace("/en/");}})();</script>
<noscript><meta http-equiv="refresh" content="0; url=/en/"></noscript></head>
<body><p>LuzKids</p><ul>{links}</ul></body></html>""".encode("utf-8"))

    # Old addresses from the Railway site keep working.
    redirects = [
        "/library /en/library/ 301",
        "/songs /en/songs/ 301",
        "/profiles /en/profiles/ 301",
        "/dashboard /en/progress/ 301",
        "/:lang/dashboard/ /:lang/progress/ 301",
        "/mission /en/mission/ 301",
        "/privacy /en/privacy/ 301",
        "/series/* /en/series/:splat 301",
        "/lang/:lang /:lang/ 302",
        "/login /en/profiles/ 301",
        "/register /en/profiles/ 301",
    ]
    (DIST / "_redirects").write_text("\n".join(redirects) + "\n", encoding="utf-8")
    shutil.copy(ROOT / "_headers", DIST / "_headers")
    print(f"built {count} pages in {len(SUPPORTED_LANGS)} languages into {DIST}")


if __name__ == "__main__":
    main()
