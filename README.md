# Campus X Mart

A campus marketplace application built with React, FastAPI, and PostgreSQL.

## Features

- JWT-backed, revocable browser sessions using httpOnly cookies and CSRF protection
- Email and phone verification with expiring six-digit codes
- User profile photos
- Marketplace listings, filtering, pagination, and media uploads
- Orders, reviews, reactions, comments, and private messaging
- One-time WebSocket tickets, notifications, and admin moderation
- Local Ollama marketplace assistant
- Docker image and GitHub Actions checks

## Run locally

The application runs on your computer: PostgreSQL on `localhost:5432`, the API on
`localhost:8000`, and the frontend on `localhost:5173`. No hosted database or deployment
service is required. Install and start PostgreSQL and make sure `pg_isready` reports it
is accepting connections. Node.js 20+ and Python 3.11+ are also required.

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# Generate a local secret and set JWT_SECRET_KEY in .env:
python -c "import secrets; print(secrets.token_urlsafe(32))"
# For local verification, set EXPOSE_DEV_OTP=true in .env.
```

Create and initialize a local PostgreSQL database once:

```bash
createdb campusxmart
psql -d campusxmart -f ../database/schema.sql
python -m migrate
```

If your local PostgreSQL role or port differs, update `DATABASE_URL` in `backend/.env`.
For an existing database, run only `python -m migrate`; `schema.sql` is for a fresh
database. The migration runner records checksums and rejects edits to applied migrations.

Start the API:

```bash
# Optional local assistant: install Ollama and run `ollama pull mistral:latest`.
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Run frontend checks with `npm run lint`, `npm test`, and `npm run build`.

## Local application behavior

- Browser sign-in returns user data, not bearer tokens. The API sets a short-lived
  httpOnly access cookie and a rotating, httpOnly refresh cookie; unsafe cookie-auth
  requests require the readable CSRF cookie echoed in `X-CSRF-Token`.
- Non-browser clients can request a short-lived bearer token from `/api/auth/token`
  (or `/api/admin/token` for administrator sessions). These tokens are
  accepted by protected API routes and are not refreshable. Browser cookies work over
  local HTTP.
- The frontend always calls the local API at `http://localhost:8000`; its WebSocket
  connections use that same local backend.
- Uploaded files are stored under `backend/uploads/`. In development, phone
  verification sends a real SMS when `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and
  `TWILIO_FROM_PHONE` are configured in `backend/.env`; otherwise,
  `EXPOSE_DEV_OTP=true` shows a demo code locally. Set `EMAIL_PROVIDER=resend`,
  `RESEND_API_KEY`, and `RESEND_FROM_EMAIL` to deliver verification emails through
  Resend during development; without those settings, email verification uses the
  local demo flow.
- The assistant uses local Ollama by default. Install Ollama and pull the configured
  model if you want to use it; otherwise the assistant can use its built-in fallback.
- Public registration creates student accounts only. Provision administrators through
  a trusted operator workflow; never expose database credentials or promote accounts
  through a public endpoint.

## Copyright

Copyright (c) 2026 Campus X Mart. All rights reserved for original project materials
owned by Campus X Mart. Third-party dependencies and materials remain subject to
their respective licenses. See [LICENSE](LICENSE).
