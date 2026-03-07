# Architecture

## Service Layers

```mermaid
graph TD
    Client --> APIGateway["API Gateway / ALB"]
    APIGateway --> FastAPI["FastAPI App"]
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
    PostgresImpl --> RDS["AWS RDS PostgreSQL"]
```

## CI/CD Flow

```mermaid
graph LR
    PR["Pull Request"] --> CI["CI: lint + type-check + test"]
    CI --> Build["Build Docker Image"]
    Build --> ECR["Push to AWS ECR"]
    ECR --> Dev["Deploy to Dev EKS"]
    Dev --> Staging["Deploy to Staging (manual)"]
    Staging --> Prod["Deploy to Prod (manual + approval)"]
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
| Config | Pydantic Settings | Environment-based configuration |
