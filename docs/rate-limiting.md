# Rate Limiting

Petstore API enforces a **fixed-window rate limit** on all non-exempt endpoints to protect the service from abuse and ensure fair usage.

---

## How It Works

Requests are tracked per **API key** (from the `X-API-Key` header) or, when no key is supplied, per **client IP address**.  
A fixed-window counter is incremented with each request.  
Once the counter exceeds the configured threshold within the current window, the API returns `429 Too Many Requests` until the window resets.

### Exempt Endpoints

The following paths are **never** rate-limited:

| Path | Reason |
|---|---|
| `/health` | Health probe |
| `/api/v1/health` | Versioned health probe |
| `/openapi.json` | OpenAPI schema |
| `/docs` | Swagger UI |

---

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `RATE_LIMIT_REQUESTS` | `40` | Max requests allowed per window per client key |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Window duration in seconds |
| `RATE_LIMIT_BYPASS_KEY` | _(empty)_ | Secret value for the bypass header (see below) |

Set these in your `.env` file (copy from `.env.example`):

```env
RATE_LIMIT_REQUESTS=40
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_BYPASS_KEY=your-secret-bypass-key-here
```

---

## Response Format

When a request is accepted, the response includes rate-limit metadata headers:

```
X-RateLimit-Limit: 40
X-RateLimit-Remaining: 39
X-RateLimit-Reset: 60
```

When the rate limit is exceeded the API returns:

**HTTP `429 Too Many Requests`**

```json
{
  "detail": "Rate limit exceeded. Please retry after the window resets."
}
```

The throttled response includes a `Retry-After` header indicating the number of seconds to wait before the next request will succeed:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 42
Content-Type: application/json
```

---

## Normal Usage Example

```bash
# First 40 requests succeed (HTTP 200 / 404 / etc.)
curl -H "X-API-Key: my-api-key" https://api.example.com/api/v1/pet/1

# Request 41+ within the same 60-second window returns 429
# HTTP/1.1 429 Too Many Requests
# Retry-After: 23
# {"detail": "Rate limit exceeded. Please retry after the window resets."}
```

---

## Bypass Mechanism

Certain privileged clients (for example, internal automation or admin tooling) can skip rate limiting entirely by including the `X-Bypass-Key` header with the configured secret value.

### Configuration

```env
RATE_LIMIT_BYPASS_KEY=super-secret-value
```

!!! warning "Keep the bypass key secret"
    The bypass key grants unlimited request throughput.  
    Treat it like a high-privilege credential — store it in a secret manager and never commit it to source control.

### Example

```bash
# No rate limit applied when the correct bypass key is present
curl -H "X-API-Key: my-api-key" \
     -H "X-Bypass-Key: super-secret-value" \
     https://api.example.com/api/v1/pet/1
```

If `RATE_LIMIT_BYPASS_KEY` is left empty (the default) the bypass mechanism is **disabled**; the `X-Bypass-Key` header has no effect.

---

## OpenAPI / 429 Error Response

The `429 Too Many Requests` response is emitted by the rate-limiting middleware **before** route handlers are invoked.  
The global API description in the interactive docs (`/docs`) documents this behaviour, accepted responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`, and `Retry-After` is always present on 429 responses.

---

## Design Notes

- **In-memory, per-process store** — no external dependency (Redis, etc.) is required.  
  Each application process maintains its own counters; in a multi-replica deployment consider replacing the store with a shared Redis instance using the same `RateLimitMiddleware` interface.
- **Fixed-window algorithm** — simple and predictable.  
  Each window starts the first time a key is seen and resets after `RATE_LIMIT_WINDOW_SECONDS` seconds.
- **Middleware placement** — `RateLimitMiddleware` is registered as a Starlette `BaseHTTPMiddleware` *inside* the auth middleware stack so rate limiting occurs for every request reaching the application, authenticated or not.
