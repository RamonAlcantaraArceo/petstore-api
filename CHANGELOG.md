# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Logging

- Added correlation-aware request lifecycle logs with HTTP method, path, client
  IP, response status, content length, and duration.
- Unified structlog, standard-library, and Uvicorn logs under one formatter,
  using readable development output and structured JSON in staging/production.
- Fixed middleware ordering and correlation enrichment so rate-limit and other
  request-scoped logs include the matching correlation ID.
- Prevented configured and supplied rate-limit bypass keys from being written
  to startup or request logs.

### Security

- Hardened Supabase ES256 and HS256 JWT validation to require the configured
  `/auth/v1` issuer plus `exp`, `iat`, and `sub` claims while continuing to
  validate the `authenticated` audience.
- Refactored JWKS retrieval and authentication call sites to use
  `httpx.AsyncClient`, preserving the one-hour cache and key-rotation retry
  without blocking the FastAPI event loop.

### Tests

- Added behavior-focused coverage for Supabase Auth provider requests and
  failures, staging user-route orchestration, paginated admin lookup, JWT JWKS
  transport failures, malformed key sets, and async-client ownership.

### Fixed

- Added `PyJWT[crypto]>=2.8.0` to production runtime requirements and Docker
  dependency verification so JWT and cryptography imports are available in
  deployed images.
- Added `email-validator>=2.3.0` to Docker
  dependency verification to fix `ModuleNotFoundError: No module named 'email_validator'`
  on container startup.
- Removed duplicate `requirements-runtime.txt`; Docker now installs production
  dependencies directly from `pyproject.toml` via `uv pip install --no-dev .`
  so there is a single source of truth for runtime packages.
- Removed spurious `dotenv` dependency from `pyproject.toml` (pydantic-settings
  handles `.env` loading internally; `dotenv` was never imported in the app).
- Added Docker smoke-test job to CI (`build-image`) that builds the image,
  starts the container, waits for the health check to pass, and validates the
  `/health` endpoint before the workflow completes.
- Added `SUPABASE_PUBLISHABLE_KEY` as the preferred alias for
  `SUPABASE_ANON_KEY` while retaining legacy environment compatibility.

### Added

- Added `supabase_sign_up()` helper to `app/auth/supabase_auth.py` — proxies
  `POST /auth/v1/signup` to Supabase Auth. Detects duplicate-email signups
  (Supabase returns 200 with empty `identities`) and raises HTTP 409.
- Added `supabase_update_user()` helper — calls `PUT /auth/v1/user` with the
  user's own bearer token to sync email/phone/metadata changes to Supabase Auth.
- Added `supabase_delete_user()` helper — calls
  `DELETE /auth/v1/admin/users/{uuid}` with a server-side Supabase admin key
  for permanent account deletion.
- Added `supabase_get_user_by_email()` helper — resolves Supabase Auth
  user records (including UUID + metadata) from email via the admin users API.
- Added `supabase_service_role_key` field to `Settings`
  with env aliases:
  `SUPABASE_SECRET_API_KEY` (preferred),
  `SUPABASE_AUTH_ADMIN_KEY`,
  and `SUPABASE_SERVICE_ROLE_KEY` (legacy compatibility).
- Added `GET /user/me` endpoint — returns the currently authenticated user's
  profile resolved from JWT claims. Works in all environments and is the
  recommended way to get "my own profile" in staging/prod where Supabase users
  do not have a username.

### Changed

- Restored dev in-memory user authentication lifecycle behind the new
  `DEV_IN_MEMORY_AUTH_ENABLED` feature flag. In `APP_ENV=dev`, users created
  via `/api/v1/user` now sync into the in-memory auth store and can authenticate
  with `/api/v1/user/login` and `/api/v1/user/auth` without Supabase.
- Added canonical `POST /user/login` with validated JSON email/password
  credentials and a unified token-plus-user response. The Petstore-compatible
  `GET /user/login` now delegates to the same login service and is marked
  deprecated in OpenAPI and runtime logs.
- `POST /user` and `POST /user/createWithList` now **proxy through Supabase
  Auth** in staging/prod: each user is registered via `supabase_sign_up()`,
  then a matching local DB profile row is mirrored. The response schema is
  identical to the dev environment. Requires `email` in the request body.
- `PUT /user/{username}` now syncs `email`, `phone`, and profile metadata to
  Supabase Auth (via `supabase_update_user()`) before updating the local DB in
  staging/prod. Username changes are rejected (HTTP 422) in staging/prod.
- `DELETE /user/{username}` in staging/prod now performs a full Supabase Auth
  deletion flow: resolve target UUID by email, delete user via Supabase admin
  API, then delete local mirrored profile by username/email/metadata fallback.
  If the admin key is missing it returns HTTP 501.
- `GET /user/{username}` returns HTTP 501 in staging/prod with a message
  directing callers to `GET /user/me` (Supabase users have no username).

### Per-environment behaviour summary

| Endpoint | dev | staging/prod |
|---|---|---|
| `POST /user` | ✅ in-memory | ✅ proxy → Supabase signup + mirror to DB |
| `POST /user/createWithList` | ✅ in-memory | ✅ same, each user individually |
| `GET /user/login` | ✅ dev JWT | ✅ Supabase Auth |
| `GET /user/logout` | ✅ no-op | ✅ revokes Supabase session |
| `GET /user/me` | ✅ from JWT claims | ✅ from JWT claims |
| `GET /user/{username}` | ✅ DB lookup | ❌ 501 — use `/user/me` |
| `PUT /user/{username}` | ✅ DB update | ✅ Supabase Auth sync + DB update |
| `DELETE /user/{username}` | ✅ DB delete | ✅ Supabase Admin delete + DB (needs secret admin API key) |

### Added

- Implemented Supabase HS256 JWT validation in `app/auth/supabase_jwt.py`.
  `validate_supabase_jwt` now verifies the token signature against
  `SUPABASE_JWT_SECRET`, checks the `exp` claim, and returns decoded claims.
  Raises `SupabaseJWTNotConfiguredError` (→ HTTP 503) when the secret is not
  set, `SupabaseJWTExpiredError` (→ HTTP 401) for expired tokens, and
  `SupabaseJWTError` (→ HTTP 401) for any other validation failure.
- Added `supabase_jwt_secret` field to `Settings` (env var `SUPABASE_JWT_SECRET`).
  Required for staging and production environments.
- Added `SupabaseJWTExpiredError` to `app/auth/supabase_jwt.py` and wired it
  into `get_current_user` in `app/api/deps.py` with a distinct 401 response.
- Added `serve-staging` Makefile target that reliably starts the service using
  `.env.staging`, bypassing shell-exported variables that would otherwise take
  precedence over the env file.
- Added `app/auth/supabase_auth.py` with `supabase_sign_in` and
  `supabase_sign_out` helpers that call the Supabase Auth REST API
  (`/auth/v1/token` and `/auth/v1/logout`) using `httpx`.
- Added `supabase_url` and `supabase_anon_key` fields to `Settings`
  (env vars `SUPABASE_URL`, `SUPABASE_ANON_KEY`). Required for login/logout
  in staging and production.

### Changed

- `GET /user/login` now delegates to Supabase Auth in staging/prod (treating
  the ``username`` field as the Supabase account email) and returns the
  Supabase access token. Dev environment behavior is unchanged.
- `GET /user/logout` now calls `supabase_sign_out` to revoke the session on
  the Supabase side in staging/prod (best-effort; continues even if
  misconfigured).

### Changed

- `Settings.model_config` now reads `ENV_FILE` from the environment
  (default: `".env"`), allowing an alternate dotenv file to be selected at
  process start time without code changes.

### Fixed

- Fixed Python 2-style bare tuple `except DevJWTError, SupabaseJWTError` in
  `maybe_get_current_user` (replaced with `except (DevJWTError, SupabaseJWTError, HTTPException)`).
- Fixed 401 on all protected routes in staging/prod: Supabase JWT ``sub``
  claims are UUIDs (e.g. ``"a1b2c3d4-..."``), not integers. Added
  ``_sub_to_user_id()`` in `app/api/deps.py` which tries integer parsing first
  (dev JWTs) then derives a stable positive integer from the UUID's 128-bit
  value. Previously every Supabase token returned 401 "missing a valid subject".
- Replaced the HS256-only stub in `app/auth/supabase_jwt.py` with full
  JWKS-backed ES256 support. The Supabase project uses ES256 (ECDSA P-256)
  asymmetric signing. `validate_supabase_jwt` now auto-detects the algorithm
  from the JWT header: ES256 tokens are verified against the public key
  fetched from ``{supabase_url}/auth/v1/.well-known/jwks.json`` (cached
  1 hour, with automatic cache invalidation on key rotation); HS256 tokens
  fall back to ``SUPABASE_JWT_SECRET``. Added ``PyJWT[crypto]`` dependency.

### Tests

- Added `tests/unit/test_supabase_jwt.py` with 8 test cases covering valid
  token decoding, missing secret, wrong secret, expired tokens, malformed
  tokens, tampered payloads, unsupported algorithms, and missing `exp` claims.

### Fixed

- Fixed a flaky test (`test_protected_route_rejects_tampered_bearer_token`) caused by
  an unreliable JWT token-tampering strategy. HMAC-SHA256 produces a 32-byte digest
  whose base64url encoding is 43 characters; the last character carries only 4
  significant bits (the lower 2 are unused zero-padding). Single-character substitution
  at the last position has a ~6.25% chance of decoding to identical bytes, silently
  passing signature verification. The test now tampers the first character of the
  signature segment where all 6 bits are significant and the change is always effective.
- Applied `black` auto-formatting to `app/middleware/delay_injection.py` and
  `app/middleware/rate_limit.py` to satisfy the CI lint gate.

### Tests

- Added `tests/unit/test_delay_injection_middleware.py`: full unit-test coverage for
  `DelayInjectionMiddleware` (probability clamping, delay injection, pass-through).
- Added `tests/unit/test_failure_injection_middleware.py`: full unit-test coverage for
  `FailureInjectionMiddleware` (probability clamping, all 5xx status codes, pass-through).
- Added `tests/unit/test_app_factory.py`: verifies injection middleware registration and
  exercises both branches of the lifespan bypass-key startup log.

## [0.3.0] - 2026-06-03

### Added

- Adds dev JWT issuance/validation, seeded in-memory dev users, and /auth/dev/login.
- Wires protected v1 routers and rate limiting to authenticated bearer user identity.
- Adds auth documentation, MkDocs navigation, and focused auth/rate-limit tests.

### Changed

- Refactors auth and rate limit dependencies to support both API key and JWT auth schemes.
- Updates API documentation to reflect new auth options and requirements.
- Refactors petstore-core and removes redundant code from petstore-api related to models, schemas, and services that are now centralized in petstore-core to be shared with petstore-grpc/graphql.

### Fixed

- Migrated all SQLAlchemy ORM model columns from legacy `Column[T]` annotations to the
  SQLAlchemy 2.x `Mapped[T]` + `mapped_column()` pattern, resolving mypy errors of the
  form "Invalid conditional operand of type ColumnElement[bool]".
- Removed now-unnecessary `# type: ignore[assignment]` suppression comments from
  repository files that were previously required to work around the unannotated columns.

## [0.2.1] - 2026-06-01

### Fixed

- Resolved issue with packaging of petstore_core after incomplete work during refactor.
- Fixed /redoc endpoint to be exposed again

## [0.2.0] - 2026-05-28

### Added
- New `petstore_core` package to consolidate domain models, services, repositories,
  and schemas. This provides a stable, reusable core for the API and future clients.
- `error_mapping.py` module in `app/api/v1/` to standardize error responses across all endpoints.

### Changed
- Refactored app architecture: moved core models, services, repositories, and schemas
  into the standalone `petstore_core` package while keeping API-specific code in `app/`.
- All API routes (`pets`, `store`, `users`, `health`) now use error mapping for consistent
  error handling across adapter layers.
- Updated imports throughout the codebase to reference the new `petstore_core` package structure.

## [0.1.1-rc4] - 2026-05-26

### Added
- `GET /api/v1/pet/findByStatus`: `status` query parameter is now optional;
  omitting it returns all pets regardless of status. Pagination via `skip`
  (offset, default 0) and `limit` (max 100, default unlimited) query
  parameters is now supported.
- Added `make merge-cleanup` to run linting, type checks, tests, and report
  generation in one local command.

### Changed
- E2E tests now spawn the API as a host-side `uvicorn` subprocess instrumented
  with `coverage run --parallel-mode` instead of booting a Docker Compose stack.
  The previous design produced root-owned coverage files in the bind-mounted
  `.e2e-coverage/` directory, causing `coverage combine` to fail with
  `PermissionError` in CI. The subprocess approach removes the Docker
  dependency from E2E execution and ensures coverage files are owned by the
  same user that runs the merge step.
- CI now always uploads test/coverage artifacts even when test execution fails,
  then explicitly fails the workflow after upload when tests fail.
- Coverage enforcement now runs after combining API and E2E coverage data, so
  the final merged report is the value checked against the 80% threshold.

### Removed
- `tests/e2e/docker-compose.e2e.yml` and the `pytest-docker` dev dependency are
  no longer needed and have been removed.

## [0.1.1-rc2 and 0.1.1-rc3]
### Added
- Fixture datasets for seeding the service with golden data at startup.
  - Four named datasets: `empty` (clean slate), `basic` (pets + users), `mixed_v1`
    (all pet statuses, orders, users with contact details), and `mixed_v2` (exotic
    animals, richer categories/tags, three orders, four users including admin and guest).
  - New `SEED_DATASET` environment variable (added to `Settings`) that controls which
    dataset is loaded automatically when the service starts — works for both in-memory
    and PostgreSQL storage modes.
  - `app/fixtures/` package exposing `FixtureDataset`, `get_dataset`, and
    `seed_from_settings` as the public API.
  - `scripts/load_fixtures.py` rewritten as a full CLI tool with `--dataset` and
    `--list` flags; supports all storage modes and can be driven by `SEED_DATASET`.
  - Comprehensive unit tests covering dataset invariants and the async loader logic
    (`tests/unit/test_fixture_datasets.py`, `tests/unit/test_fixture_loader.py`).
- Dependabot configuration to automatically update GitHub Actions, Python (pip), and Docker base image dependencies on a weekly schedule.
- Added automatic dev deployment after GHCR image publication by invoking the reusable Fly.io dev workflow with the same image tag.
- Added a `Makefile` with a `merge-cleanup` target to run linting, type checks, tests, and coverage/Allure report generation in one reproducible command.

### Changed
- Updated the release workflow to mark GitHub releases as pre-releases when the tag contains a hyphen (for example, `v0.1.1-rc1`).
- Updated the GHCR image workflow to expose the produced tag as a job output.
- Updated the deployment documentation to reflect the new automatic dev deployment and the ability to specify versions for manual deployments.
- Updated CI test job flow so report upload runs even when tests fail, then explicitly fails the job afterward when test execution failed.

## [0.1.1-rc1] - 2026-05-19
### Added
- Initial pre-release of Petstore API implementing the OpenAPI 3.0 spec.
- FastAPI backend with async SQLAlchemy support.
- In-memory, PostgreSQL, and AWS RDS storage options.
- API key authentication.
- Structured logging with structlog.
- Comprehensive test suite (unit, integration, system, e2e).
- Performance test scaffolding.
- Pydantic-based configuration.

### Changed
- Switched project versioning to Hatchling VCS with Git tags as the release source of truth.
- Added tag-triggered Python artifact release workflow and aligned GHCR publishing to `v*` tags.
- Release continuity note: the first stable release tag after this migration should be `v0.2.0`.
