# Petstore API

A **production-ready Python backend API** implementing the [Petstore OpenAPI 3.0 spec](https://petstore3.swagger.io/api/v3/openapi.json), built with FastAPI and deployable to AWS EKS.

## Quick Start

Start the API in in-memory mode (no external dependencies):

```bash
docker compose up
```

Then test the health endpoint:

```bash
curl http://localhost:8000/health
```

## Features

- Full Petstore API (pets, store, users)
- Three runtime modes: in-memory, local PostgreSQL, AWS RDS
- Structured JSON logging with correlation IDs
- API key authentication with JWT-ready interface
- Deployable via Docker locally and Helm to AWS EKS
