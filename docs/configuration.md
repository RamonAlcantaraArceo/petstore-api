# Configuration

All settings are loaded from environment variables. Copy `.env.example` to `.env` for local development.

Environment variables already exported in your shell take precedence over values
in `.env`.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `STORAGE_MODE` | `memory` | Runtime mode: `memory` \| `local` \| `cloud` |
| `API_KEY` | `dev-api-key` | Required API key for authentication |
| `DATABASE_URL` | `""` | PostgreSQL connection URL (required for non-memory mode) |
| `APP_ENV` | `dev` | Application environment: `dev` \| `staging` \| `prod` |
| `DEV_IN_MEMORY_AUTH_ENABLED` | `true` | Dev-only feature flag for in-memory user authentication and identity storage |
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DB_POOL_SIZE` | `5` | SQLAlchemy connection pool size |
| `DB_MAX_OVERFLOW` | `10` | SQLAlchemy max overflow connections |
| `DB_POOL_TIMEOUT` | `30` | SQLAlchemy pool timeout (seconds) |
| `RATE_LIMIT_REQUESTS` | `40` | Max requests per window per API key / client IP |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window duration (seconds) |
| `RATE_LIMIT_BYPASS_KEY` | _(empty)_ | Secret `X-Bypass-Key` header value that skips rate limiting |
| `SUPABASE_URL` | `""` | Supabase project URL; required for staging/production JWT issuer validation |
| `SUPABASE_PUBLISHABLE_KEY` | `""` | Preferred Supabase public API key for Auth requests |
| `SUPABASE_ANON_KEY` | `""` | Backward-compatible alias for `SUPABASE_PUBLISHABLE_KEY` |
| `SUPABASE_JWT_SECRET` | `""` | Shared secret for legacy HS256 Supabase JWTs |

## Storage Modes

- **`memory`**: All data is held in-process. No external dependencies. Perfect for local dev and unit tests.
- **`local`**: Connects to a local PostgreSQL via `DATABASE_URL`.
- **`cloud`**: Connects to AWS RDS PostgreSQL.

When `APP_ENV=dev`, user authentication can stay fully in-memory by keeping
`DEV_IN_MEMORY_AUTH_ENABLED=true` (default). Set it to `false` only if you
explicitly want dev traffic to use Supabase token validation.
