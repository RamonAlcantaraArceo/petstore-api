# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
