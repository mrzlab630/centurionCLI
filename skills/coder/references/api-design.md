# API Design Standards — CODER Reference

> Check on activation when building or modifying APIs.

## REST Conventions

### URL Structure
```
GET    /api/v1/wallets              → list
GET    /api/v1/wallets/:id          → get one
POST   /api/v1/wallets              → create
PUT    /api/v1/wallets/:id          → full update
PATCH  /api/v1/wallets/:id          → partial update
DELETE /api/v1/wallets/:id          → delete
POST   /api/v1/wallets/:id/actions/sync → custom action (verb as sub-resource)
```

### Rules
- **Nouns** for resources, never verbs (`/wallets` not `/getWallets`)
- **Plural** names (`/wallets` not `/wallet`)
- **Lowercase** kebab-case for multi-word (`/swap-orders`)
- **Nesting** max 2 levels (`/wallets/:id/positions`, not `/wallets/:id/positions/:pid/trades`)
- **Versioning** in URL path (`/api/v1/`) — not headers

### Query Parameters
```
GET /api/v1/trades?page=1&limit=20&sort=-createdAt&status=open
```
- `page` + `limit` (default 20, max 100)
- `sort` — prefix `-` for descending
- `filter` — flat params, not nested objects

## Response Format

### Success
```json
{
  "data": { ... },          // single object
  "data": [ ... ],          // array for lists
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 142
  }
}
```

### Error
```json
{
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "Wallet balance 0.5 SOL is below required 1.0 SOL",
    "details": {
      "balance": 0.5,
      "required": 1.0
    }
  }
}
```

### Rules
- **Always** return `{ data }` or `{ error }` — never raw values
- **Error codes** = UPPER_SNAKE_CASE, machine-readable
- **Error messages** = human-readable, specific, actionable
- **Never** expose stack traces in production
- **Never** return 200 for errors — use proper HTTP status codes

## HTTP Status Codes

| Code | When |
|---|---|
| `200` | Success (GET, PUT, PATCH, DELETE with body) |
| `201` | Created (POST that creates a resource) |
| `204` | No Content (DELETE, actions with no response) |
| `400` | Bad Request (validation error, malformed input) |
| `401` | Unauthorized (no/invalid auth token) |
| `403` | Forbidden (valid auth, insufficient permissions) |
| `404` | Not Found (resource doesn't exist) |
| `409` | Conflict (duplicate, state conflict) |
| `422` | Unprocessable Entity (valid JSON, invalid business logic) |
| `429` | Too Many Requests (rate limit hit) |
| `500` | Internal Server Error (unexpected, log and alert) |
| `503` | Service Unavailable (dependency down, maintenance) |

## Validation

### Input Validation (zod recommended)
```typescript
import { z } from 'zod';

const CreateWalletSchema = z.object({
  address: z.string().min(32).max(44),
  label: z.string().max(100).optional(),
  maxTxSol: z.number().positive().max(10),
  slippage: z.number().min(0.1).max(50).default(1.5),
});

// In handler:
const result = CreateWalletSchema.safeParse(req.body);
if (!result.success) {
  return res.status(400).json({
    error: {
      code: 'VALIDATION_ERROR',
      message: 'Invalid input',
      details: result.error.flatten().fieldErrors
    }
  });
}
```

### Rules
- Validate at API boundary — trust internal code
- Use zod/joi for schema validation, not manual checks
- Return ALL validation errors at once, not one at a time
- Sanitize strings (trim, limit length) before DB

## Rate Limiting

```typescript
// Per-user: 100 req/min for reads, 20 req/min for writes
// Global: 1000 req/sec
// Response headers:
// X-RateLimit-Limit: 100
// X-RateLimit-Remaining: 42
// X-RateLimit-Reset: 1710432000
// 429 when exceeded
```

## Authentication

- **Bearer token** in `Authorization` header: `Bearer <token>`
- **Never** in URL query params (logged by proxies/CDNs)
- **Never** in cookies for API (use for browser-only)
- Token expiry: 24h access, 30d refresh

## Versioning Strategy

- **URL versioning** (`/api/v1/`, `/api/v2/`) — simple, explicit
- **Breaking changes** = new version
- **Additive changes** (new fields) = same version
- **Deprecation**: 3-month notice via `Deprecation` header + docs
- **Max 2 versions** active simultaneously

## Documentation (OpenAPI/Swagger)

```yaml
# openapi.yaml (keep in repo root or docs/)
openapi: 3.1.0
info:
  title: Snorter API
  version: 1.0.0
paths:
  /api/v1/wallets:
    get:
      summary: List monitored wallets
      parameters:
        - name: page
          in: query
          schema: { type: integer, default: 1 }
      responses:
        '200':
          description: Wallet list
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items: { $ref: '#/components/schemas/Wallet' }
```

### Rules
- OpenAPI spec = source of truth, keep in sync with code
- Auto-generate where possible (tsoa, nestjs/swagger)
- Include request/response examples
- Document error codes per endpoint

## Anti-Patterns (NEVER Do)

- **Never** return 200 with `{ success: false }` — use HTTP status codes
- **Never** expose internal IDs without need (use UUIDs for public APIs)
- **Never** accept unlimited arrays/strings — set max limits
- **Never** return unbounded lists — always paginate
- **Never** use GET for mutations (even "simple" toggles)
- **Never** nest resources deeper than 2 levels
- **Never** return different shapes for same endpoint based on params
