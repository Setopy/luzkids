# LuzKids 🕯️
Bilingual (EN/ES) interactive Bible studies for children aged 6–12.
*"Let your light shine before others" — Matthew 5:16*

## Privacy: no children's data on the server

LuzKids stores **nothing about children** on the server. There are no
accounts, no logins and no AI chat. Child profiles (nickname and avatar),
lessons completed, XP, streaks, badges, certificates and the Mission Field
list live only in the browser (`localStorage`, key `luzkids.v1`), handled by
`static/js/progress.js`. Families move progress between devices with the
"Save progress to a file" / "Load progress from a file" buttons on
`/profiles`; the file never touches the server. Certificates are printable
pages built in the browser.

There is no server and no database: the site is static files. Feedback is
an email link in the footer ("Report an issue").

Tests: `pytest -q` and `node --test tests/*.cjs`.
`tests/test_privacy.py` fails if a model other than `feedback` is added or a
child-data endpoint comes back.

## Stack
Flask + Jinja + vanilla JS, used only to render pages. `python build.py`
renders every page in every language (`/en/`, `/es/`, `/fr/`, `/pt/`, `/th/`)
into `dist/`, using the existing translations in `content/`. Content lives as
JSON in `content/` (see CONTENT_GUIDE.md — adding a series requires zero code
changes).

## Run locally
```
pip install -r requirements.txt
python app.py            # http://localhost:5000  (same pages as the build)
python build.py          # writes the static site to dist/
```

## Deploy to Cloudflare (free)
Cloudflare Workers with static assets (Workers & Pages → Create → Import a
repository → `Setopy/luzkids`):
- Build command: `pip install -r requirements.txt && python build.py`
- Deploy command: `npx wrangler deploy` (uses `wrangler.jsonc`, which serves `dist/`)
- Custom domains: `luzkids.org` and `www.luzkids.org`

`_headers` (security headers, caching) and `_redirects` (old Railway
addresses such as `/library` → `/en/library/`) are copied into `dist/`.

## Before charging real money (launch checklist)
- [ ] Replace the `/subscribe/<plan>` stub with Stripe Checkout + webhook
      (or Lemon Squeezy — merchant of record, handles MX/TH/NG tax)
- [ ] Confirm Suno plan tier grants commercial licence for all tracks
- [x] Privacy page (`/privacy`): nothing about children is stored on the server
- [ ] Terms of use
- [ ] Decide legal home: DAI:NI, EIDS, or new entity (affects SAT/RESICO)

## Structure
```
app.py              page routes (per language), on-device page shells
build.py            renders the static site into dist/
content_loader.py   JSON content pipeline
content/            one folder per study series  <- THE PRODUCT
templates/          Jinja pages
static/             css, js (progress.js = on-device progress), songs, printables
CONTENT_GUIDE.md    how to author a new series in an evening
```
