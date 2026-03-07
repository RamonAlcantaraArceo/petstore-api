# Configuration

All settings are loaded from environment variables. Copy `.env.example` to `.env` for local development.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `STORAGE_MODE` | `memory` | Runtime mode: `memory` \| `local` \| `cloud` |
| `API_KEY` | `dev-api-key` | Required API key for authentication |
| `DATABASE_URL` | `""` | PostgreSQL connection URL (required for non-memory mode) |
| `APP_ENV` | `dev` | Application environment: `dev` \| `staging` \| `prod` |
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DB_POOL_SIZE` | `5` | SQLAlchemy connection pool size |
| `DB_MAX_OVERFLOW` | `10` | SQLAlchemy max overflow connections |
| `DB_POOL_TIMEOUT` | `30` | SQLAlchemy pool timeout (seconds) |

## Storage Modes

- **`memory`**: All data is held in-process. No external dependencies. Perfect for local dev and unit tests.
- **`local`**: Connects to a local PostgreSQL via `DATABASE_URL`.
- **`cloud`**: Connects to AWS RDS PostgreSQL.
