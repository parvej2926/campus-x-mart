# Campus X Mart — Project Overview

## What this project is

Campus X Mart is a full-stack campus marketplace. Students can register and verify accounts, list and browse products, message each other, place orders, leave reviews, and receive notifications. Administrators have a separate sign-in flow for moderation and account management.

The application is composed of:

- A **React 19 + Vite** single-page frontend in `frontend/`.
- A **FastAPI** backend in `backend/`, with PostgreSQL access through psycopg2.
- A canonical PostgreSQL schema and SQL migrations in `database/`.
- Render deployment configuration in `render.yaml` and a backend Docker image definition in `Dockerfile`.

The main browser UI is the shared application in `frontend/src/WorkspaceApp.jsx`; the API routes and much of the service logic currently live together in `backend/main.py`.

## How the main pieces fit together

1. Vite serves `frontend/index.html` and loads `frontend/src/main.jsx`.
2. `main.jsx` mounts `App.jsx`, which re-exports `WorkspaceApp.jsx`.
3. `WorkspaceApp.jsx` renders the screens, calls the FastAPI REST endpoints, manages authenticated state, and maintains notification/chat WebSocket connections. Utility modules in the same folder support translation, maps, YouTube URLs, comments, and category suggestions.
4. FastAPI starts from `backend/main.py`. It defines HTTP and WebSocket routes, request models, authentication/authorization, database operations, upload handling, and GraphQL handling.
5. `backend/database.py` opens PostgreSQL connections using configuration from `backend/settings.py`.
6. `database/schema.sql` defines the baseline database structure. The files under `database/migrations/` apply individual changes to an existing database.
7. `backend/tests/` contains API and unit tests. The test fixture requires a dedicated PostgreSQL database whose name ends in `_test`.

## Repository map

### Root

| File | What it contains |
|---|---|
| [`README.md`](README.md) | Project features, local startup steps, and deployment/database setup notes. |
| [`overview.md`](overview.md) | This repository and file-navigation guide. |
| [`PROJECT_CHECKLIST.md`](PROJECT_CHECKLIST.md) | Current implementation inventory, security actions, known gaps, and verification status. |
| [`ERD.md`](ERD.md) | Human-readable summary of core database entities and relationships. |
| [`feaures.md`](feaures.md) | Original feature inventory; the filename is spelled `feaures.md` in the repository. |
| [`tools.md`](tools.md) | Short project technology/tool inventory. |
| [`Dockerfile`](Dockerfile) | Builds and starts the Python/FastAPI API container. |
| [`render.yaml`](render.yaml) | Render Blueprint for the API service, static frontend, and PostgreSQL database. |
| [`.gitignore`](.gitignore) | Excludes local environments, secrets files, generated frontend output, uploads, and other local artifacts. |
| [`LICENSE`](LICENSE) | Project copyright and third-party materials notice. |

### `.github/`

| File | What it contains |
|---|---|
| [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | Persistent project overview and working, testing, security, and database-change rules for coding assistants. |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | GitHub Actions jobs for backend Ruff/pytest checks and frontend install/lint/build checks. |

### `.vscode/`

| File | What it contains |
|---|---|
| [`.vscode/settings.json`](.vscode/settings.json) | Workspace editor setting for Java project build-configuration updates. |

### `backend/`

| File | What it contains |
|---|---|
| [`backend/main.py`](backend/main.py) | FastAPI application entry point. Defines authentication, registration, listings, locations, uploads, catalog, comments, reactions, reviews, orders, messages, notifications, reports, admin routes, WebSockets, and GraphQL. |
| [`backend/settings.py`](backend/settings.py) | Pydantic settings loaded from environment variables and `backend/.env`; validates required database/JWT settings and parses CORS origins. |
| [`backend/.env.example`](backend/.env.example) | Safe template showing configuration variable names and placeholder values. |
| `backend/.env` | Local-only environment configuration. It is intentionally not included in this guide; do not share or commit it. |
| [`backend/database.py`](backend/database.py) | Creates psycopg2 PostgreSQL connections using the application settings. |
| [`backend/graph_schema.py`](backend/graph_schema.py) | Graphene GraphQL schema, including the greeting and item query. |
| [`backend/llm_assistant.py`](backend/llm_assistant.py) | Marketplace assistant provider calls and rule-based fallback replies. |
| [`backend/ml_model.py`](backend/ml_model.py) | Lightweight keyword-based category prediction helper. |
| [`backend/generate_report.py`](backend/generate_report.py) | Collects marketplace aggregates and builds an in-memory PDF report. |
| [`backend/verification_delivery.py`](backend/verification_delivery.py) | Email/SMS delivery abstraction for verification codes, with SMTP, Resend, Twilio, and development behavior. |
| [`backend/requirements.txt`](backend/requirements.txt) | Runtime Python dependencies and pinned versions. |
| [`backend/requirements-dev.txt`](backend/requirements-dev.txt) | Python development/test tools, including pytest, HTTPX, pytest-cov, and Ruff. |
| [`backend/pytest.ini`](backend/pytest.ini) | Pytest import path and test discovery configuration. |

#### `backend/tests/`

| File | What it tests |
|---|---|
| [`backend/tests/conftest.py`](backend/tests/conftest.py) | Shared TestClient, authenticated-user/item fixtures, and isolated PostgreSQL test-database setup/cleanup. |
| [`backend/tests/test_phase1_security.py`](backend/tests/test_phase1_security.py) | Required settings, authenticated routes, upload validation, GraphQL response behavior, rate limits, and one-time WebSocket tickets. |
| [`backend/tests/test_phase2_dev_otp.py`](backend/tests/test_phase2_dev_otp.py) | OTP exposure policy and verification delivery adapters/failure handling. |
| [`backend/tests/test_phase2_verification_limits.py`](backend/tests/test_phase2_verification_limits.py) | Verification-code resend cooldown, attempt limits, and current-user response behavior. |
| [`backend/tests/test_username_availability.py`](backend/tests/test_username_availability.py) | Username availability responses for valid, taken, and invalid names. |
| [`backend/tests/test_marketplace_catalog.py`](backend/tests/test_marketplace_catalog.py) | Product feed filtering, sorting, and pagination. |
| [`backend/tests/test_marketplace_locations.py`](backend/tests/test_marketplace_locations.py) | Location directory, map details, and invalid listing location handling. |
| [`backend/tests/test_marketplace_social.py`](backend/tests/test_marketplace_social.py) | Product reactions/comments, user search, messaging, message visibility, and chat WebSockets. |
| [`backend/tests/test_marketplace_orders.py`](backend/tests/test_marketplace_orders.py) | Order pricing, roles, state transitions, cancellation, item availability, and privacy. |
| [`backend/tests/test_marketplace_meetup_dates.py`](backend/tests/test_marketplace_meetup_dates.py) | Order meetup-date validation, permissions, and immutability after completion. |
| [`backend/tests/test_marketplace_reviews.py`](backend/tests/test_marketplace_reviews.py) | Review eligibility/update rules and product/seller ratings. |
| [`backend/tests/test_marketplace_notifications.py`](backend/tests/test_marketplace_notifications.py) | Notification privacy, read states, order/admin alerts, registration alerts, and WebSocket delivery. |
| [`backend/tests/test_marketplace_moderation.py`](backend/tests/test_marketplace_moderation.py) | Dedicated admin access, searchable/paginated user directory, reports, and posting bans. |
| [`backend/tests/test_marketplace_verification_gates.py`](backend/tests/test_marketplace_verification_gates.py) | Verified-contact requirements for listing and ordering actions. |
| [`backend/tests/test_marketplace_video.py`](backend/tests/test_marketplace_video.py) | YouTube URL validation and listing video output. |
| [`backend/tests/test_marketplace_assistant.py`](backend/tests/test_marketplace_assistant.py) | Assistant provider selection, response behavior, blank prompts, and upstream failures. |
| [`backend/tests/test_ml_category_predictor.py`](backend/tests/test_ml_category_predictor.py) | Keyword-based category prediction and whole-word matching. |

### `database/`

| File or folder | What it contains |
|---|---|
| [`database/schema.sql`](database/schema.sql) | Canonical baseline schema for a new, empty PostgreSQL database: users/authentication, locations, products/media, posts/social interactions, reviews, orders, messages, notifications, reports, and category predictions. |
| [`database/schema.md`](database/schema.md) | Text description of the database schema and entity relationships. |
| [`database/data.sql`](database/data.sql) | Sample SQL data for manual database setup. Its included password hashes are placeholders; it is not a production credential source. |
| [`database/seed_200_rows.py`](database/seed_200_rows.py) | Explicit development seeder for generated users, locations, and marketplace records; requires development mode and `--yes` because it truncates tables. |
| [`database/migrations/001_websocket_tickets.sql`](database/migrations/001_websocket_tickets.sql) | Idempotently creates the one-time WebSocket ticket table and expiry index. |
| [`database/migrations/002_active_order_per_item.sql`](database/migrations/002_active_order_per_item.sql) | Adds the uniqueness rule limiting active orders per item. |
| [`database/migrations/003_order_meetup_date.sql`](database/migrations/003_order_meetup_date.sql) | Adds the order meetup-date column. |
| [`database/migrations/004_user_posting_bans.sql`](database/migrations/004_user_posting_bans.sql) | Adds student posting-ban fields to users. |
| [`database/migrations/005_message_visibility.sql`](database/migrations/005_message_visibility.sql) | Adds per-user hidden-message records. |

### `docs/`

| File | What it contains |
|---|---|
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Completed requirements and phased plans for security, correctness, backend structure, frontend work, and product features. |

### `frontend/`

| File | What it contains |
|---|---|
| [`frontend/package.json`](frontend/package.json) | Frontend npm scripts and runtime/development dependencies. |
| [`frontend/package-lock.json`](frontend/package-lock.json) | Exact npm dependency lockfile used by `npm ci`. |
| [`frontend/index.html`](frontend/index.html) | Vite HTML shell, title, favicon, and React mount element. |
| [`frontend/vite.config.js`](frontend/vite.config.js) | Vite configuration with React and Tailwind CSS plugins. |
| [`frontend/eslint.config.js`](frontend/eslint.config.js) | ESLint rules and generated-output exclusions. |
| [`frontend/capacitor.config.json`](frontend/capacitor.config.json) | Capacitor app identity and web build directory. |
| [`frontend/README.md`](frontend/README.md) | Starter Vite/React template documentation. |
| [`frontend/.gitignore`](frontend/.gitignore) | Frontend-specific generated files, package output, and editor artifacts to ignore. |
| [`frontend/src/main.jsx`](frontend/src/main.jsx) | React browser entry point; imports the base stylesheet and mounts `App`. |
| [`frontend/src/App.jsx`](frontend/src/App.jsx) | Re-exports the main `WorkspaceApp` component for the entry point. |
| [`frontend/src/WorkspaceApp.jsx`](frontend/src/WorkspaceApp.jsx) | Main marketplace UI, navigation, language selection, screen state, API client usage, realtime connections, forms, and admin views. |
| [`frontend/src/Workspace.css`](frontend/src/Workspace.css) | Main application visual system and component/page styling, including Bengali-friendly font fallbacks. |
| [`frontend/src/index.css`](frontend/src/index.css) | Base Tailwind import and global element styles. |
| [`frontend/src/App.css`](frontend/src/App.css) | Additional stylesheet retained in the source tree; the current `main.jsx` entry imports `index.css`, while `WorkspaceApp.jsx` imports `Workspace.css`. |
| [`frontend/src/translations.js`](frontend/src/translations.js) | English/Bengali text translations and notification-specific translation helpers. |
| [`frontend/src/categorySuggestion.js`](frontend/src/categorySuggestion.js) | Client-side rule-based product category suggestions. |
| [`frontend/src/locationUtils.js`](frontend/src/locationUtils.js) | Builds map search and embed URLs from location data. |
| [`frontend/src/commentUtils.js`](frontend/src/commentUtils.js) | Deduplicates/merges comment lists. |
| [`frontend/src/youtube.js`](frontend/src/youtube.js) | Validates YouTube URLs and constructs privacy-enhanced embed URLs. |
| [`frontend/src/components/Navbar.jsx`](frontend/src/components/Navbar.jsx) | Standalone navigation component retained in the components folder. |
| [`frontend/src/assets/hero.png`](frontend/src/assets/hero.png) | Landing-page hero image. |
| [`frontend/src/assets/react.svg`](frontend/src/assets/react.svg) | React SVG asset. |
| [`frontend/src/assets/vite.svg`](frontend/src/assets/vite.svg) | Vite SVG asset. |
| [`frontend/src/categorySuggestion.test.js`](frontend/src/categorySuggestion.test.js) | Tests client category suggestion rules. |
| [`frontend/src/commentUtils.test.js`](frontend/src/commentUtils.test.js) | Tests comment-list merge/deduplication behavior. |
| [`frontend/src/locationUtils.test.js`](frontend/src/locationUtils.test.js) | Tests location map-query and URL helpers. |
| [`frontend/src/youtube.test.js`](frontend/src/youtube.test.js) | Tests accepted and rejected YouTube URL handling. |
| [`frontend/public/cxm.svg`](frontend/public/cxm.svg) | Campus X Mart favicon/brand mark used by the HTML shell. |
| [`frontend/public/favicon.svg`](frontend/public/favicon.svg) | Additional public SVG favicon asset. |
| [`frontend/public/icons.svg`](frontend/public/icons.svg) | Public SVG icon asset collection. |

#### `frontend/android/`

Tracked Capacitor Android project for building a native Android wrapper around the web application. Gradle files configure the Android build; `app/src/main/` contains the manifest, Java activity, layouts, and drawable/mipmap resources; `app/src/test/` and `app/src/androidTest/` contain starter native test classes. The wrapper's Java entry point is `MainActivity.java`.

### `ml/`

| File | What it contains |
|---|---|
| [`ml/__init__.py`](ml/__init__.py) | Python package marker for the ML utilities. |
| [`ml/category_predictor.py`](ml/category_predictor.py) | Deterministic whole-word keyword classifier for marketplace product categories. |

### `reports/`

| File | What it contains |
|---|---|
| [`reports/marketplace_reports.sql`](reports/marketplace_reports.sql) | Example aggregate queries for category totals, completed sales, top-rated products, and seller listing counts. |

## Database entities at a glance

The baseline schema contains `users`, `verification_codes`, `user_sessions`, `websocket_tickets`, `locations`, `items`, `item_media`, `posts`, `post_media`, `post_comments`, `item_comments`, `post_reactions`, `item_reactions`, `reviews`, `orders`, `messages`, `message_hidden_for`, `notifications`, `reports`, and `item_predictions`.

Important relationships include users-to-listings, items-to-media/comments/reviews/orders, users-to-messages as sender or receiver, and users-to-notifications. The detailed table definitions and constraints are in `database/schema.sql`; the migration files represent incremental changes for an already-existing database.

## Common local commands

Run commands from the relevant project directory:

```bash
# Backend API, from backend/
uvicorn main:app --reload

# Frontend development server, from frontend/
npm run dev

# Frontend production build, from frontend/
npm run build

# Backend tests, from backend/ after configuring TEST_DATABASE_URL
pytest -q
```

For environment variable names and placeholders, see `backend/.env.example`. The real `backend/.env` is local configuration and must remain private. Use `database/schema.sql` only to initialize a new, empty database; use the relevant idempotent migration for an existing database.

## Scope notes

- `backend/main.py` is currently the central API module rather than a router/service package structure.
- `frontend/src/WorkspaceApp.jsx` is the current large shared UI module; several utility files keep smaller domain-specific behaviors separate.
- `database/schema.sql` is the canonical baseline schema. Apply numbered SQL migrations to existing databases rather than rerunning the baseline schema.
- Generated/install directories such as `frontend/node_modules/`, `frontend/dist/`, Python caches, and local virtual environments are not source inventory.
