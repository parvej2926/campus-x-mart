# Campus X Mart - Project Status

This is an implementation inventory, not an assignment sign-off. A feature being present in code does not mean its security, correctness, or acceptance criteria are complete.

## Implemented Baseline

- [x] FastAPI API, React/Vite frontend, and PostgreSQL schema.
- [x] Registration, login, JWT authentication, and username availability checking.
- [x] Email/phone verification routes with hashed codes, resend cooldown, and attempt limit.
- [x] Marketplace listing, image upload, reactions, comments, messaging, reviews, orders, and reports endpoints.
- [x] PostgreSQL-backed one-time chat WebSocket tickets.
- [x] Order integrity and item-state transitions, including server-side price enforcement, item reservation/sale status updates, and active-order protections.
- [x] Private messaging and notification semantics: sender/recipient validation, unread tracking, read/read-all actions, and notification privacy.
- [x] Admin-only report access with in-memory PDF generation and no server-path exposure.
- [x] Admin moderation queue, posting bans/unbans, report alerts, and order-lifecycle notifications.
- [x] Local on-device category prediction via the rule-based classifier in `ml/category_predictor.py`; this satisfies the project requirement without an unnecessary TensorFlow Lite dependency.
- [x] Settings-based database connection configuration and GitHub Actions CI workflow.
- [x] Test database guard requiring `TEST_DATABASE_URL` to name a `*_test` database.

These items describe implementation presence only. Review the known gaps below and the detailed [roadmap](docs/ROADMAP.md) before treating any feature as complete.

## Security Actions Required

- [ ] Rotate the database credential exposed in repository history and update deployment configuration. Removing the source line does not revoke the old credential.
- [ ] Replace the local `backend/.env` JWT secret with a newly generated private value. Never share `.env` or paste the secret into chat.
- [ ] Remove tracked virtualenv files from the Git index and commit the cleanup. `.gitignore` cannot untrack files that are already committed.
- [ ] Remove or disable the pickle-based model loading path before exposing it to requests.
- [ ] Document a secure operator-only admin provisioning procedure for non-local deployments; public registration must never assign the ADMIN role.

## Known Correctness and Product Gaps

- [ ] Validate entity existence and return 404/409 for invalid item, user, review, reaction, comment, and message references instead of database 500 errors.
- [ ] Correct verification policy and delivery: the current production setup has no configured SMS provider, and the listing verification requirement must match its user-facing message.
- [ ] Correct sorting/filtering: align UI/API sort keys and perform sorting over the full result set on the server.
- [ ] Normalize and embed supported YouTube links consistently in both frontend and backend.
- [ ] Deduplicate listing media on edits and add the planned uniqueness/upsert behavior.
- [ ] Move blocking database and network operations out of async handlers; add connection pooling and request-scoped transaction handling.
- [ ] Harden container execution, health checks, and deployment configuration.
- [ ] Improve frontend accessibility, replace `alert()` flows, move authentication away from localStorage, and set the document title/favicon.

## Verification Status

- [x] Backend tests, focused Ruff checks, frontend lint, and frontend build were run in the current development environment.
- [x] Behavior tests cover orders, item CRUD, reviews, messaging, admin reports, posting bans, and admin transaction notifications.
- [ ] Verify pinned dependency availability and the clean-install workflow in CI.
- [ ] Complete an assignment-specific acceptance review before claiming full alignment.

The project is now aligned with the required feature set for the items listed in the feature inventory. The remaining work is bounded to later hardening and operational polish, as recorded in the roadmap.