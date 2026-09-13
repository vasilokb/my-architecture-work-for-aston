# ABS Sandbox - TEST_REPORT

**Run date:** 2026-07-01
**Stack:** Java 21 + Spring Boot 3.3 + Kong 3.9.3 + OPA 0.59.0 + Keycloak 24.0.5 (Quarkus) + Redis 7
**Test runner:** `sandbox/test-flow.ps1` (PowerShell 5.1)

## Result: 9 / 9 OK

| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| 1 | OPA RBAC: operator GET /api/v1/accounts | `allow=true` | `{"allow":true,"is_tenant_active":true}` | OK |
| 2 | OPA RBAC: operator GET /api/v1/credits | `allow=false` | `{"allow":false,"is_tenant_active":true}` | OK |
| 3 | OPA tenant-blacklist: bank-008 manager | `allow=false` | `{"allow":false}` | OK |
| 4 | Kong blacklist: blacklisted user | HTTP 401 | HTTP 401 | OK |
| 5 | Kong blacklist: blacklisted tenant | HTTP 401 | HTTP 401 | OK |
| 6 | Kong file-log: audit.log appended | grew > 0 | +1903 bytes | OK |
| 7 | Keycloak OIDC discovery | 200 + issuer | 200 + `http://localhost:8080/realms/abs` | OK |
| 8 | Keycloak login ROPC: operator@bank-007.test | JWT, ttl=3600 | JWT issued, `expires_in=3600` | OK |
| 9 | Keycloak JWT claims | sub=user-operator, realm_access.roles=[operator] | matches | OK |

## What was proven end-to-end

### Keycloak realm `abs`
- Realm imported at startup via `--import-realm` (see `sandbox/keycloak/Dockerfile`).
- 5 base realm roles: `operator`, `manager`, `credit_manager`, `auditor`, `bank_admin`.
- 3 test users: `operator@bank-007.test / operator`, `manager@bank-007.test / manager`, `bank-admin@bank-007.test / admin`.
- 2 clients: `bank-007` (confidential, PKCE S256, direct access grants for sandbox testing), `admin-service` (client_credentials, service-account enabled).
- OIDC discovery works at `http://localhost:8080/realms/abs/.well-known/openid-configuration`.
- ROPC grant (sandbox-only, for testing without browser): `/realms/abs/protocol/openid-connect/token` with `grant_type=password` returns valid JWT.
- JWT contains: `sub`, `iss=http://localhost:8080/realms/abs`, `realm_access.roles=[operator]`, `azp=bank-007`, `exp` (1h TTL), `jti`.
- Access token TTL: 3600s (1h, matches §6 of protocol 19062026).

### OPA policy `abs.rbac.authz` (Rego)
- RBAC matrix: operator allowed to read accounts, denied to read credits.
- Tenant blacklist: manager of `bank-008` is denied because tenant is inactive in OPA data.
- Data loaded from `sandbox/opa/policies/data.json` on OPA startup (read-only; git tracks the policy, not the data).

### Kong + custom Lua plugin `blacklist-guard`
- Plugin loads via `KONG_PLUGINS=bundled,blacklist-guard` and lives at `/usr/local/share/lua/5.1/kong/plugins/blacklist-guard/`.
- On every request Kong reads `X-User-Id` and `X-Tenant-Id` headers, calls Redis `EXISTS blacklist:user:{id}` and `blacklist:tenant:{id}` with 100ms timeout, returns 401 `{"message":"Token revoked"}` on hit.
- Logs `DENY: user=... tenant=... reason=...` to Kong error log.
- Test data seeded by `sandbox/redis/seed.sh`:
  - `SET blacklist:user:test-blacklisted-user 1 EX 3600` (TTL 1h as per protocol)
  - `SET blacklist:tenant:bank-002 1` (no TTL as per protocol)

### Kong + file-log plugin
- Every request through Kong is written as JSON line to `/var/log/kong/audit.log` (host mount: `sandbox/kong/audit/audit.log`).
- Captures: client_ip, request id, route/service, headers, upstream_status, response status, latencies.

## How to reproduce

```powershell
# from git/abs
cd D:\Астон\evergreen\git\abs
docker compose -f sandbox/docker-compose.yml up -d --build
Start-Sleep -Seconds 90   # Keycloak cold-start takes ~60s on first run
powershell -ExecutionPolicy Bypass -File sandbox/test-flow.ps1
```

Expected last lines:
```
PASS: 9    FAIL: 0
```

## Keycloak cold-start notes

- First startup takes ~60s: Quarkus boot + realm import + admin user creation.
- Healthcheck on `localhost:8080/health/ready` returns 200 only after realm import finishes.
- Volume `sandbox_keycloak-data` is reused across restarts — do NOT delete unless you want to re-import the realm from scratch.

## Bug found and fixed during this session

- **Symptom:** Keycloak container in `Restarting (1)` loop, repeatedly logging `Unrecognized field "accessPolicy" (class org.keycloak.representations.idm.RealmRepresentation)`.
- **Root cause:** docker build cache was copying a stale `realm-export.json` into the image (an older draft version that contained a `accessPolicy` field). The local file on disk was already clean, but `docker compose build` reused the cached image.
- **Fix:** `docker compose build --no-cache keycloak` then `docker volume rm sandbox_keycloak-data && docker compose up -d keycloak`. New image picked up the correct realm JSON; realm imported successfully (`Realm 'abs' imported`).

## Known sandbox limitations (out of scope here, addressed in production design)

1. **No JWT validation in Kong.** Sandbox skips the `jwt` plugin and trusts `X-User-Id / X-Tenant-Id / X-User-Roles` headers as if Kong had already validated a JWT and extracted claims. Production adds `jwt` plugin with `claims_to_headers`.
2. **No OPA call from Kong.** OPA is consulted in production via the `opa` pre-function plugin (or sidecar) for fine-grained authorization. In sandbox the controller does a simple role check, and OPA is exercised only directly via `test-input-*.json` files.
3. **No custom claim `tenant_id` in JWT.** Sandbox JWT has `sub` + `realm_access.roles` only. Production adds a custom protocol mapper (oidc-usermodel-attribute-mapper) that maps user attribute `tenant_id` into the JWT claim.
4. **ROPC used for testing.** Sandbox uses Resource Owner Password Credentials grant (`grant_type=password`) to obtain a token without a browser. Production uses Authorization Code + PKCE (the `bank-007` client is configured with `pkce.code.challenge.method=S256`, ROPC is enabled only because the sandbox test harness is headless).
5. **No Kafka / Audit Service / ClickHouse.** The `file-log` plugin is the sandbox stand-in for the full audit pipeline. In prod, Kong `http-log` plugin posts the same JSON to Kafka topic `auth.audit`, Audit Service writes to ClickHouse.

## Sample log lines (last entries in `sandbox/kong/audit/audit.log`)

Each line is a JSON object with:
- `client_ip` - source IP (172.18.0.1 in tests)
- `request.headers` - includes `x-user-id`, `x-tenant-id`, `x-user-roles`
- `route.name` - `admin-route` or `backend-api-route`
- `upstream_status` - HTTP status from upstream Spring Boot service
- `response.status` - final status (Kong may rewrite, e.g. 401 for blacklist)
- `source` - `upstream` (passed through) or `kong` (blocked by plugin)
- `latencies` - kong, request, proxy, receive in ms

A blacklisted tenant request appears as:
```json
{"source":"kong","response":{"status":401,...},"request":{"headers":{"x-user-id":"alice","x-tenant-id":"bank-002",...}}}
```

A successful request appears as:
```json
{"source":"upstream","upstream_status":"200","response":{"status":200,...},"request":{"headers":{"x-user-id":"alice","x-tenant-id":"bank-001","x-user-roles":"operator",...}}}
```