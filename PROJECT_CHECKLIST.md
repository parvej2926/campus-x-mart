# Campus X Mart - Project Status

This checklist records implemented behavior separately from operations that still
require an operator or additional work.

## Implemented

- [x] FastAPI API, React/Vite frontend, PostgreSQL schema, and PostgreSQL-backed tests.
- [x] Registration, login, verification, admin access controls, and role-gated moderation.
- [x] Cookie browser sessions: httpOnly access and refresh tokens, refresh rotation,
  server-side revocation, CSRF checks, and bearer authentication for API clients.
- [x] Marketplace listings, media upload, server-side filtering/sorting/pagination,
  reactions, comments, messaging, reviews, orders, reports, and notifications.
- [x] Order state protections and one active confirmed/completed order per item.
- [x] Idempotent database migration runner with checksums and applied-version tracking.
- [x] Unique item-media order index and row-level locking for concurrent additions.
- [x] Thread-safe PostgreSQL connection pool, request IDs, and structured request logs.
- [x] Non-root Docker runtime, `/healthz` liveness check, and frontend Node test script.
- [x] CI runs focused Ruff checks, backend tests, frontend lint/tests/build.

## Operator actions

- [ ] Rotate the database credential exposed in repository history and update deployment
  configuration; removing a credential from source does not revoke it.
- [ ] Ensure any local JWT secret that may have been shared is replaced privately.
- [ ] Verify production `CORS_ORIGINS`, HTTPS cookie settings, Cloudinary, and email/SMS
  provider credentials in the deployment environment.
- [ ] Provision administrators only through a trusted operator-controlled process.

## Remaining engineering work

- [ ] Split `backend/main.py` into routers, services, schemas, and database modules.
- [ ] Move all blocking database/provider work out of async request handlers.
- [ ] Add end-to-end frontend flow tests for login, marketplace browsing, and listing
  creation; current frontend tests cover utilities and the shared API client.
- [ ] Audit every form and interactive view for keyboard access, focus behavior, and
  accessible error announcements.
- [ ] Add broader PostgreSQL migration tests for every historical schema version.
- [ ] Review remaining entity-existence and conflict paths for intentional 404/409
  responses rather than database errors.

## Validation

Run the checks from the repository root:

```bash
cd backend && ruff check --select F,E9 . && pytest -q
cd ../frontend && npm ci && npm run lint && npm test && npm run build
```
