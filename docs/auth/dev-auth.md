# Dev Authentication

The development environment includes an in-memory authentication layer that uses the same `UserModel` shape as the real application and issues Supabase-shaped JWTs.

## How it works

- Seeded users live in memory only
- `POST /api/v1/user/auth` exchanges a seeded username for a bearer token
- Protected `/api/v1/*` routes use the shared `get_current_user` dependency
- In `staging` and `prod`, the same dependency is ready to delegate to Supabase JWT validation

## Seeded users

- `devuser`
- `devadmin`

## Login

```bash
curl -X POST http://localhost:8000/api/v1/user/auth \
  -H 'Content-Type: application/json' \
  -d '{"username":"devuser"}'
```

Example response:

```json
{
  "access_token": "JWT token",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "devuser",
    "first_name": "Dev",
    "last_name": "User",
    "email": "dev@example.com",
    "phone": "555-1234",
    "user_status": 1
  }
}
```

## Use the token

```bash
curl http://localhost:8000/api/v1/store/inventory \
  -H 'Authorization: ******'
```

If rate-limit bypass is configured, you can also send:

```bash
-H 'X-Bypass-Key: <configured bypass key>'
```

## Environment variables

- `APP_ENV` or `ENV`: `dev`, `staging`, or `prod`
- `DEV_JWT_SECRET`: shared secret for development JWT signing
- `DEV_JWT_EXPIRATION_SECONDS`: development token lifetime in seconds

## Token structure

Development JWTs mimic Supabase claims:

```json
{
  "sub": "1",
  "email": "dev@example.com",
  "role": "authenticated",
  "user_metadata": {
    "username": "devuser",
    "first_name": "Dev",
    "last_name": "User",
    "phone": "555-1234",
    "user_status": 1
  },
  "iat": 1717046400,
  "exp": 1717050000
}
```

## Supabase compatibility

The development issuer is intentionally shaped like Supabase Auth so production code can keep using the same dependency and user-mapping flow when JWKS-backed validation is added.

## JWT signature internals

Development tokens use HMAC-SHA256. The 32-byte digest is base64url-encoded to a
43-character string (without `=` padding). The **last character** of that string carries
only 4 significant bits — the lower 2 bits are unused zero-padding and are ignored by
base64 decoders. Any two characters that share the same top 4 bits (e.g. `a` and `b`)
decode to identical bytes, so a single-character substitution at the last position is not
guaranteed to corrupt the signature.

When writing tests that verify tampered-token rejection, always modify a character other
than the last one in the signature segment (e.g. the first character), where all 6 bits
are significant and a substitution always alters the decoded bytes.
