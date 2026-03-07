# API Reference

The Petstore API implements the [Petstore OpenAPI 3.0 spec](https://petstore3.swagger.io/api/v3/openapi.json).

## Interactive Documentation

When running locally, visit:

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>
- **OpenAPI JSON**: <http://localhost:8000/openapi.json>

## Endpoints

### Pet

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/pet` | Add a new pet |
| PUT | `/api/v1/pet` | Update an existing pet |
| GET | `/api/v1/pet/findByStatus` | Find pets by status |
| GET | `/api/v1/pet/findByTags` | Find pets by tags |
| GET | `/api/v1/pet/{petId}` | Get pet by ID |
| POST | `/api/v1/pet/{petId}` | Update pet with form data |
| DELETE | `/api/v1/pet/{petId}` | Delete a pet |
| POST | `/api/v1/pet/{petId}/uploadFile` | Upload pet image |

### Store

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/store/inventory` | Returns pet inventories by status |
| POST | `/api/v1/store/order` | Place an order |
| GET | `/api/v1/store/order/{orderId}` | Find order by ID |
| DELETE | `/api/v1/store/order/{orderId}` | Delete order |

### User

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/user` | Create user |
| POST | `/api/v1/user/createWithList` | Create users with list |
| GET | `/api/v1/user/login` | Log user in |
| GET | `/api/v1/user/logout` | Log user out |
| GET | `/api/v1/user/{username}` | Get user by username |
| PUT | `/api/v1/user/{username}` | Update user |
| DELETE | `/api/v1/user/{username}` | Delete user |

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check (unauthenticated) |
