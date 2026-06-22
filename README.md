# LuzKids 🕯️
Bilingual (EN/ES) interactive Bible studies for children aged 6–12.
*"Let your light shine before others" — Matthew 5:16*

## Stack
Flask + SQLite (SQLAlchemy) + vanilla JS. Same stack as ElisaVoz — deliberately
boring; the value is the content. Content lives as JSON in `content/`
(see CONTENT_GUIDE.md — adding a series requires zero code changes).

## Run locally
```
pip install -r requirements.txt
python app.py            # http://localhost:5000
```

## Deploy to Railway
1. Push this repo to GitHub, create a Railway project from it.
2. Set env vars: `SECRET_KEY` (random string), and add a Postgres plugin —
   Railway injects `DATABASE_URL` automatically (the code converts the
   legacy `postgres://` prefix).
3. Procfile is included; Railway runs `flask db upgrade` as a release step,
   then gunicorn.

### One-time migration bootstrap on the existing production database
Schema is now managed by Flask-Migrate/Alembic (`migrations/`) instead of
`db.create_all()`. Production already has tables matching the current
models (created previously by `db.create_all()` / `migrate_increment3.py`),
so on the **first** deploy after this change, stamp the baseline instead of
running it, or Alembic will try to create tables that already exist:
```
railway run flask db stamp 35e0b42b1f2e
```
After that one-time stamp, future schema changes go through the normal
`flask db migrate -m "..."` / `flask db upgrade` flow, and the release step
in the Procfile handles upgrades automatically on every deploy.

## Before charging real money (launch checklist)
- [ ] Replace the `/subscribe/<plan>` stub with Stripe Checkout + webhook
      (or Lemon Squeezy — merchant of record, handles MX/TH/NG tax)
- [ ] Confirm Suno plan tier grants commercial licence for all tracks
- [ ] Privacy policy + terms (children's data: COPPA-style care — child
      profiles store first name + emoji only, by design; keep it that way)
- [ ] Email verification + password reset (Flask-Mail or a transactional API)
- [ ] Decide legal home: DAI:NI, EIDS, or new entity (affects SAT/RESICO)
- [ ] Rate limiting on auth routes; set strong SECRET_KEY

## Structure
```
app.py              routes, models, auth, progress, payment stubs
content_loader.py   JSON content pipeline
content/            one folder per study series  <- THE PRODUCT
templates/          Jinja pages
static/             css, js, audio (Suno tracks), printables (PDFs)
CONTENT_GUIDE.md    how to author a new series in an evening
```
