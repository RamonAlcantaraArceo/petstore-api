# Deployment

## Docker (Local)

```bash
# In-memory mode
docker compose up

# With local PostgreSQL
docker compose -f docker-compose.postgres.yml up
```

## Fly.io

Fly.io is the primary deployment platform.

### PR / Review Apps

Review apps are deployed automatically for branches prefixed with `fly/`. The app is torn down when the PR is closed.

- Trigger: open or push to a `fly/*` branch PR
- Config: `.fly/pr/fly.toml`

### Dev

```bash
# Manual deploy (uses latest GHCR image by default)
gh workflow run deploy-fly-dev.yml

# Deploy a specific version
gh workflow run deploy-fly-dev.yml -f version=v1.2.3
```

- Config: `.fly/dev/fly.toml`
- Auto-triggered after the GHCR image is published on merge to `main`

### Staging

```bash
# Deploy a specific version to staging
gh workflow run "Deploy to Fly.io Staging" -f version=v1.2.3
```

- Config: `.fly/staging/fly.toml`
- Manual trigger via `workflow_dispatch`

## CI/CD

Deployments are managed via GitHub Actions:

| Environment | Trigger | Workflow |
|-------------|---------|----------|
| PR review app | Open/push to `fly/*` PR | `deploy-fly-pr.yml` |
| Dev | Auto after GHCR image publish (main) | `deploy-fly-dev.yml` |
| Staging | Manual `workflow_dispatch` | `deploy-fly-staging.yml` |

> **Note:** AWS (ECS/EKS) and Kubernetes (Helm) deployment is planned but not yet active.
