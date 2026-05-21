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
- After each dev deploy, this workflow triggers test automation in an external test repository and waits for completion.
- If tests fail, the workflow run fails and the staging queue step is skipped.

### Staging

```bash
# Deploy a specific version to staging
gh workflow run "Deploy to Fly.io Staging" -f version=v1.2.3
```

- Config: `.fly/staging/fly.toml`
- Auto-queued by `deploy-fly-dev.yml` only after post-deploy dev tests pass.
- Default hold window is `90` minutes before staging deploy starts.
- Cancel the running `deploy-fly-dev.yml` workflow during that window to stop staging deployment.

## CI/CD

Deployments are managed via GitHub Actions:

| Environment | Trigger | Workflow |
|-------------|---------|----------|
| PR review app | Open/push to `fly/*` PR | `deploy-fly-pr.yml` |
| Dev | Auto after GHCR image publish (main), then external test gate | `deploy-fly-dev.yml` |
| Staging | Queued by dev workflow after successful tests and hold window | `deploy-fly-staging.yml` |

## Required CI/CD configuration

Set these repository-level values to enable post-dev test gating:

| Type | Name | Example | Purpose |
|------|------|---------|---------|
| Variable | `DEV_TEST_REPOSITORY` | `your-org/petstore-tests` | External repository that runs dev validation tests |
| Variable | `DEV_TEST_WORKFLOW` | `dev-environment-tests.yml` | Workflow filename or workflow ID in the test repository |
| Variable | `DEV_TEST_REF` | `main` | Ref used when dispatching the test workflow |
| Variable | `DEV_TEST_WORKFLOW_INPUTS_JSON` | `{"environment":"dev"}` | Optional JSON inputs for the dispatched test workflow |
| Variable | `DEV_TEST_TIMEOUT_MINUTES` | `120` | Max wait time for test completion |
| Variable | `DEV_TEST_POLL_INTERVAL_SECONDS` | `30` | Polling interval while awaiting test completion |
| Variable | `STAGING_DEPLOY_DELAY_MINUTES` | `90` | Review/hold window before auto-dispatching staging deploy |
| Secret | `TEST_AUTOMATION_TOKEN` | `ghp_***` | Token with `actions:write` access to dispatch/read runs in test repo |

> **Note:** AWS (ECS/EKS) and Kubernetes (Helm) deployment is planned but not yet active.
