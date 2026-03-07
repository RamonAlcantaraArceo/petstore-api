# Deployment

## Docker (Local)

```bash
# In-memory mode
docker compose up

# With local PostgreSQL
docker compose -f docker-compose.postgres.yml up
```

## Kubernetes (Helm)

```bash
# Deploy to dev
helm upgrade --install petstore-api ./helm/petstore-api \
  -f ./helm/petstore-api/values-dev.yaml \
  --set image.tag=<commit-sha>

# Deploy to staging
helm upgrade --install petstore-api ./helm/petstore-api \
  -f ./helm/petstore-api/values-staging.yaml \
  --set image.tag=<commit-sha>
```

## CI/CD

Deployments are managed via GitHub Actions:

- **Dev**: Auto-deploy on merge to `main`
- **Staging**: Manual trigger via `workflow_dispatch`
- **Production**: Manual trigger with environment approval
