# Campus X Mart

A campus marketplace application built with React and FastAPI.

## Features

- User authentication with JWT
- Email and phone verification with expiring six-digit codes
- Item listing and browsing
- Product filtering and pagination
- Real-time comments and chat
- Rating and reactions
- Google Maps and video embeds
- Upload support with Cloudinary fallback
- Local Ollama marketplace assistant (no API key required; OpenAI is optional)
- Docker support and CI workflow for automation

## Run locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# fill in DATABASE_URL and JWT_SECRET_KEY before starting the app
# For local verification testing, set EXPOSE_DEV_OTP=true in backend/.env; dev mode does not send real email or SMS.
# install Ollama and run `ollama pull mistral:latest` if the model is not already available
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Deployment notes

- Docker image is defined in the repository root `Dockerfile`.
- GitHub Action workflow runs lint/build checks in `.github/workflows/ci.yml`.
- `render.yaml` defines a Render Blueprint for the frontend, API, and PostgreSQL database.
- To deploy, push this repository to GitHub, create a Render Blueprint from the repository, and apply the Blueprint. Render generates `JWT_SECRET_KEY` and connects the database automatically.
- Initialize the newly provisioned, empty database once from the repository root with `psql "$DATABASE_URL" -f database/schema.sql`. Set `DATABASE_URL` securely in your local environment first; do not paste it into source files or commit it. This is a one-time operation, not a command to rerun on an existing database.
- For Render Free email delivery, set `EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, and
    `RESEND_FROM_EMAIL` on the API service. Verify the sender domain with Resend first;
    its API sends over HTTPS, which works with Render Free. SMTP remains available on
    hosts that permit outbound SMTP. For phone codes, configure `TWILIO_ACCOUNT_SID`,
    `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_PHONE`. Codes expire after 10 minutes, allow
    five attempts, and can be resent after 60 seconds.
- Configure Cloudinary for persistent uploads. The local upload directory is not durable on hosted instances.
- The free Render database and web service have provider-defined usage and lifecycle limits. Review the current limits in Render before using this setup for real users or important data.
- The default local Ollama configuration is not available on Render. Configure a reachable LLM provider before enabling the assistant in production.

## Copyright

Copyright (c) 2026 Campus X Mart. All rights reserved for original project materials owned by Campus X Mart. Third-party dependencies and materials remain subject to their respective licenses. See [LICENSE](LICENSE).
- For Render Free email delivery, configure Resend as described above. For phone
    codes, configure `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_PHONE`.
