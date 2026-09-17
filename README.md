# LuzKids 🕯️
Bilingual (EN/ES) interactive Bible studies for children aged 6–12.
*"Let your light shine before others" — Matthew 5:16*

## AI companion configuration and troubleshooting

The lesson question feature uses Groq. On the Railway **web** service, set
`GROQ_API_KEY` to an active key from your Groq project. Never commit a key.

`GROQ_MODEL` is optional and defaults to `openai/gpt-oss-20b`, Groq's
[recommended replacement](https://console.groq.com/docs/deprecations) for
`llama-3.1-8b-instant`, which was retired for free/developer accounts on
August 16, 2026. This continues to use Groq and the existing Groq key;
an OpenAI API key is not needed. If you set a model override, confirm that
your Groq project permits that model.

GPT-OSS requests use low reasoning effort, omit reasoning from the response,
and reserve 1024 tokens for reasoning plus the final answer. The prompt still
requests at most four child-friendly sentences. Calls have a 10-second SDK
timeout and no automatic retries; the page also stops waiting after 20 seconds.
Only successful answers reduce the browser's three-question session allowance.
The server's per-account request limits still apply to attempts.

If questions fail after deployment, inspect Railway logs for
`AI companion provider error`:
- `status=401` or `403`: check the Groq key, project access and model permissions.
- `code=model_decommissioned` / `model_not_found`: check `GROQ_MODEL` against
  Groq's current supported models.
- `status=429`: check Groq usage/quota and retry later.
- Timeouts, connection failures or `status=5xx`: check Groq service health.

The endpoint returns HTTP 503 and an error code for provider failures, while
keeping the child-facing message simple. Logs omit API keys, provider response
bodies and children's questions. A 401 from **/api/ask** itself means the user
must log in again.

Run regression checks with `pytest -q` and, with Node.js installed,
`node --test tests/test_ai_companion_ui.cjs`. Provider responses are simulated
through the real Groq SDK; no live API key is needed for these tests.
After deployment, log in at luzkids.org, open a lesson and ask one short question
to verify the real Groq account and model access.

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
