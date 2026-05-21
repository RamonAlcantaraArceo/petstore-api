# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Dependabot configuration to automatically update GitHub Actions, Python (pip), and Docker base image dependencies on a weekly schedule.
- Added automatic dev deployment after GHCR image publication by invoking the reusable Fly.io dev workflow with the same image tag.
- Added post-dev deployment test gating in `deploy-fly-dev.yml` by dispatching and waiting for automation in an external test repository.
- Added a configurable staging hold window (default: 90 minutes) before `deploy-fly-staging.yml` is auto-dispatched.

### Changed
- Updated the release workflow to mark GitHub releases as pre-releases when the tag contains a hyphen (for example, `v0.1.1-rc1`).
- Updated the GHCR image workflow to expose the produced tag as a job output.
- Updated the deployment documentation to reflect the new automatic dev deployment and the ability to specify versions for manual deployments.
- Updated the release deployment flow to: GHCR publish -> dev deploy -> external dev tests -> delayed staging queue.

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
