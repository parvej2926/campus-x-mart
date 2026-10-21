# Campus X Mart

A campus marketplace application built with React, FastAPI, and PostgreSQL.

## Features

- JWT-backed, revocable browser sessions using httpOnly cookies and CSRF protection
- Email and phone verification with expiring six-digit codes
- Marketplace listings, filtering, pagination, and media uploads
- Orders, reviews, reactions, comments, and private messaging
- One-time WebSocket tickets, notifications, and admin moderation
- Local Ollama marketplace assistant (OpenAI is optional)
- Docker image and GitHub Actions checks

## Run locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# Set DATABASE_URL and a private JWT_SECRET_KEY in backend/.env.
# For local verification, set EXPOSE_DEV_OTP=true; development does not send real email or SMS.
```

Initialize a new PostgreSQL database once, then apply tracked migrations whenever upgrading:

```bash
psql "$DATABASE_URL" -f ../database/schema.sql
python -m migrate
```

Ensure `DATABASE_URL` is exported to the shell running `psql`; keep its value private.
Existing databases should run `python -m migrate` without reloading `schema.sql`. The
migration runner records file checksums and rejects edits to migrations that have
already been applied. Do not run `schema.sql` against an existing database; it is a
fresh-database bootstrap file.

Start the API:

```bash
# Optional local assistant: install Ollama and run `ollama pull mistral:latest`.
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Run frontend checks with `npm run lint`, `npm test`, and `npm run build`.

## Sessions and deployment

- Browser sign-in returns user data, not bearer tokens. The API sets a short-lived
  httpOnly access cookie and a rotating, httpOnly refresh cookie; unsafe cookie-auth
  requests require the readable CSRF cookie echoed in `X-CSRF-Token`.
- Non-browser clients can request a short-lived bearer token from `/api/auth/token`
  (or `/api/admin/token` for administrator sessions) over HTTPS. These tokens are
  accepted by protected API routes and are not refreshable.
- Configure `CORS_ORIGINS` with the exact frontend origins. Production cookies require
  HTTPS and use `SameSite=None; Secure` to support a separate frontend origin.
- The container runs as a non-root user and has a `/healthz` liveness check. Apply
  database migrations as a deployment step before starting a new API release.
- `render.yaml` defines a Render Blueprint for the frontend, API, and PostgreSQL
  database. Render generates `JWT_SECRET_KEY` and connects the database automatically.
- Configure Cloudinary for persistent hosted uploads. The local upload directory is
  not durable on hosted instances.
- For Render Free email delivery, set `EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, and
  `RESEND_FROM_EMAIL`. Verify the sender domain with Resend first. For phone codes,
  configure `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_PHONE`.
- The default local Ollama configuration is not available on Render. Configure a
  reachable LLM provider before enabling the assistant in production.
- Public registration creates student accounts only. Provision administrators through
  a trusted operator workflow; never expose database credentials or promote accounts
  through a public endpoint.
- Review Render's current database and service limits before using the free tier with
  important or production user data.

## Copyright

Copyright (c) 2026 Campus X Mart. All rights reserved for original project materials
owned by Campus X Mart. Third-party dependencies and materials remain subject to
their respective licenses. See [LICENSE](LICENSE).
