# Architecture

## Service Layers

```mermaid
graph TD
    Client --> FlyEdge["Fly.io Edge Proxy"]
    FlyEdge --> FastAPI["FastAPI App"]
    FastAPI --> CorrelationMiddleware["Correlation ID Middleware"]
    CorrelationMiddleware --> AuthMiddleware["Auth Middleware (X-API-Key)"]
    AuthMiddleware --> Router["API Router /api/v1/"]
    Router --> PetService["PetService"]
    Router --> OrderService["OrderService"]
    Router --> UserService["UserService"]
    PetService --> PetRepo["PetRepository (Protocol)"]
    OrderService --> OrderRepo["OrderRepository (Protocol)"]
    UserService --> UserRepo["UserRepository (Protocol)"]
    PetRepo --> MemoryImpl["Memory Implementation"]
    PetRepo --> PostgresImpl["PostgreSQL Implementation"]
    PostgresImpl --> LocalPostgres["Local PostgreSQL (Dev/Test)"]
    PostgresImpl --> Supabase["Supabase PostgreSQL (Staging)"]
```

## CI/CD Flow

```mermaid
graph LR
    PR["Pull Request"] --> CI["CI: lint + type-check + test"]
    ReleaseTag["Release Tag (v*)"] --> GHCR["Build and Publish Image to GHCR"]
    GHCR --> Dev["Deploy to Fly.io Dev (auto)"]
    GHCR --> Staging["Deploy to Fly.io Staging (manual)"]
    Staging --> SupabaseDb["Supabase PostgreSQL (staging data)"]
```

## Component Overview

| Layer | Component | Responsibility |
|---|---|---|
| Transport | FastAPI / Uvicorn | HTTP routing, request/response handling |
| Middleware | CorrelationId, Auth | Cross-cutting concerns |
| API | v1 routers | Endpoint definitions, request validation |
| Service | PetService, etc. | Business logic |
| Repository | Memory / Postgres | Data persistence abstraction |
| ORM | SQLAlchemy 2.x async | Database mapping |
| Data Stores | Local PostgreSQL, Supabase PostgreSQL | Environment-specific persistence backends |
| Deployment | GitHub Actions, GHCR, Fly.io | Build, publish, and runtime hosting pipeline |
| Config | Pydantic Settings | Environment-based configuration |
