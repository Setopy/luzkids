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

The only table the app uses is `feedback` (anonymous reports from the footer
form). To read them, set `FEEDBACK_ADMIN_TOKEN` on Railway and open
`/feedback?token=<your token>`; without the variable the page is hidden.
`RESEND_API_KEY` (optional) emails each report to the owner.

Tests: `pytest -q` and `node --test tests/*.cjs`.
`tests/test_privacy.py` fails if a model other than `feedback` is added or a
child-data endpoint comes back.

## Stack
Flask + SQLAlchemy + vanilla JS. SQLite locally by default, Postgres in
production (set `DATABASE_URL`). Same stack as ElisaVoz — deliberately
boring; the value is the content. Content lives as JSON in `content/`
(see CONTENT_GUIDE.md — adding a series requires zero code changes).

## Run locally
```
pip install -r requirements.txt
flask db upgrade         # create/update the local SQLite schema
python app.py            # http://localhost:5000
```

## Deploy to Railway
1. Push this repo to GitHub, create a Railway project from it.
2. Add a Postgres service to the project, then on the **web** service set
   `DATABASE_URL` to `${{Postgres.DATABASE_URL}}` (a reference variable —
   Railway resolves it to the internal connection string). Also set
   `SECRET_KEY` (random string).
3. Schema migrations (Flask-Migrate/Alembic, see `migrations/`) run via
   Railway's **pre-deploy command**, configured in `railway.json`
   (`flask db upgrade`) — this runs automatically before every deploy.
   Railway does **not** honor a Heroku-style `release:` line in the
   Procfile, so don't rely on that.

## Before charging real money (launch checklist)
- [ ] Replace the `/subscribe/<plan>` stub with Stripe Checkout + webhook
      (or Lemon Squeezy — merchant of record, handles MX/TH/NG tax)
- [ ] Confirm Suno plan tier grants commercial licence for all tracks
- [x] Privacy page (`/privacy`): nothing about children is stored on the server
- [ ] Terms of use
- [ ] Decide legal home: DAI:NI, EIDS, or new entity (affects SAT/RESICO)
- [ ] Set a strong SECRET_KEY on Railway (used for the language cookie and CSRF)

## Structure
```
app.py              routes, feedback model, on-device page shells
content_loader.py   JSON content pipeline
content/            one folder per study series  <- THE PRODUCT
templates/          Jinja pages
static/             css, js (progress.js = on-device progress), songs, printables
CONTENT_GUIDE.md    how to author a new series in an evening
```
