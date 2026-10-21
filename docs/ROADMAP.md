# Roadmap

## Recently implemented

- Cookie-backed browser sessions with httpOnly access/refresh cookies, refresh-token
  rotation, server-side revocation, and double-submit CSRF checks.
- A checksum-verified PostgreSQL migration runner; schema changes are mirrored in
  `database/schema.sql`.
- Thread-safe PostgreSQL connection pooling with connections returned to the pool.
- Unique media ordering per listing, migration-time stable resequencing, and a row lock
  to serialize concurrent media additions.
- Request IDs in API responses and structured request logs.
- Non-root container execution and a liveness health check.
- Frontend cookie/CSRF API client tests included in CI.

## Remaining upgrade work

1. Split the monolithic `backend/main.py` into focused routers, services, schemas, and
   database modules without changing the existing API behavior.
2. Convert every blocking database and network operation inside async request handlers
   to threadpool execution or a compatible async client.
3. Add PostgreSQL-backed frontend flow tests for login, browsing, and listing creation;
   keep the existing Node tests for the shared API client and utilities.
4. Improve frontend accessibility and UX: keyboard/focus audits, accessible form errors,
   and consistent non-blocking notifications.
5. Add production operator documentation and a controlled administrator-provisioning
   command, then rotate any credentials exposed outside the repository.
6. Continue feature work from the product roadmap only after these operational and
   correctness items are verified.
