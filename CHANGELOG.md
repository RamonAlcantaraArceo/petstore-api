# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
- Initial pre-release of Petstore API implementing the OpenAPI 3.0 spec.
- Features:
  - FastAPI backend with async SQLAlchemy support
  - In-memory, PostgreSQL, and AWS RDS storage options
  - API key authentication
  - Structured logging with structlog
  - Comprehensive test suite (unit, integration, system, e2e)
  - Performance test scaffolding
  - Pydantic-based configuration
- `GET /api/v1/pet/findByStatus`: `status` query parameter is now optional;
  omitting it returns all pets regardless of status. Pagination via `skip`
  (offset, default 0) and `limit` (max 100, default unlimited) query
  parameters is now supported.
