# WorldOfCodes — Assignment 7 (backend only)

Python / FastAPI / PostgreSQL / SQLAlchemy / Alembic / Pydantic / JWT.
No frontend, Express, Prisma runtime, Docker judge or learning content is required.

## Origin and scope

Authentication was extracted from `NYerassyl/WorldOfCodes` commit
`d4ea40d01e8b5c776b84c6a88e7777ba612c8ecb` (PRs #36 and #37).
`auth_security.py`, `site_auth.py` and the auth service preserve JWT, Node-compatible
scrypt hashing, revocable sessions and transaction locking from the main project.
The extraction adds standalone routes/profile ownership and narrows models to
User and AuthSession. Its **independent database is created by Alembic**; do not
apply these migrations to the WorldOfCodes shared database. No user data/secrets
were copied. This repository is an adapted teaching subset, not the full website.

## Start on macOS / Linux

Python 3.12+ and a running PostgreSQL server are required.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
createdb assignment7
export DATABASE_URL='postgresql+psycopg:///assignment7'
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export JWT_ACCESS_TTL_SECONDS=3600
alembic upgrade head
uvicorn main:app --reload --port 8000
```

For password-based PostgreSQL use
`postgresql+psycopg://USER:PASSWORD@localhost:5432/assignment7`.
Keep JWT_SECRET unchanged across restarts; store it in your server environment.
`.env.example` is a template, not automatically loaded by Alembic. Export variables
before migrations. Uvicorn can additionally load an actual `.env` with `--env-file .env`.
Swagger: http://127.0.0.1:8000/docs . OpenAPI: `/openapi.json`.

## API and permissions

All paths have the `/api` prefix; `/api/auth/register` is the assignment's
`/auth/register` operation within that prefix.

| Method / path | Access / result |
| --- | --- |
| GET /api/health | Public liveness |
| POST /api/auth/register | Public; 201 `{token,user}` |
| POST /api/auth/login | Public; 200 `{token,user}` |
| POST /api/auth/logout | Current session; 204, JWT revoked |
| GET /api/users/me | Authenticated; private profile |
| GET /api/users/{user_id} | Public; no email/password/token |
| PATCH /api/users/{user_id} | Owner only; displayName/bio |
| DELETE /api/users/{user_id} | Owner only; sessions cascade-delete |

Registration body: `{"email":"alice@example.com","nickname":"alice","password":"StrongPassword123!"}`.
Login body: email and password. Nicknames are unique, lowercase letters, 3–24.
Click Swagger **Authorize** and paste only the JWT. Normal API calls send
`Authorization: Bearer <token>`.
Duplicate account → 409; bad Pydantic input → 422; invalid credentials/token → 401;
non-owner mutation → 403; missing public profile → 404; missing JWT config → 503.
Authorization uses **ownership**, so admin roles are unnecessary for this scope.
Users cannot set XP, coins, IDs, email or password hashes through profile patches.

## Architecture

- `main.py`, `routers.py`: HTTP routing and centralized domain errors.
- `canonical_schemas.py`: Pydantic request constraints, rejects extra fields.
- `auth_service.py`, `profile_service.py`: business rules and ownership.
- `auth_security.py`: HS256 JWT; salted scrypt; SHA-256 token hash.
- `site_auth.py`: reusable current-user/session dependencies, revocation checks.
- `database.py`: PostgreSQL engine and per-request transaction.
- `canonical_models.py`: User (`Player` class) and AuthSession, one-to-many.
- `migrations/`: full initial Alembic schema, unique constraints and foreign key.
- `tests/`: JWT unit tests and real PostgreSQL API/concurrency tests.

JWT requires sub, iat, exp, jti, iss and aud. Issuer is `worldofcodes-auth`, audience
`worldofcodes-api`; only HS256 is accepted. JWT_SECRET must be at least 32 UTF-8
bytes, with no fallback secret. Each token's hash is stored in AuthSession;
logout invalidates that session immediately. Concurrent logouts acquire an
exclusive row lock. Existing opaque-format session validation from the source is
retained, but this application issues **only JWTs**. No refresh token flow.

## Recreate schema and test (isolated database only)

```sh
createdb assignment7_test
export DATABASE_URL='postgresql+psycopg:///assignment7_test'
alembic upgrade head
alembic check
pytest -q
# Destructive only on this disposable test database:
alembic downgrade base
alembic upgrade head
```

Tests require a localhost database ending in `_test` and clear its two tables.
They do not use SQLite or `create_all`; migrations must run first.
The GitHub Actions workflow provisions PostgreSQL 17 and repeats these checks.

## Swagger verification

1. Register Alice; repeat to see 409; use invalid email/password to see 422.
2. Login with wrong password (401), then the correct one (200).
3. GET `/users/me` without a token (401); Authorize and repeat (200).
4. PATCH Alice's profile as Alice (200).
5. Register/login Bob; patch/delete Alice using Bob's token (403).
6. Logout Bob (204); reuse Bob's token (401).
7. DELETE Alice as Alice (204); her previous tokens now return 401.

Optional automated **actual Swagger UI** verification:
`pip install playwright && python -m playwright install chromium`, start Uvicorn
on port 8017 against a disposable database, then run `python scripts/verify_swagger.py`.
Every operation is executed using Try it out → Execute. This is API documentation
verification, not an added frontend website.

## Verified locally (2026-11-23)

- PostgreSQL 17 isolated `woc_assignment7_20261123_test`: **18 tests passed**.
- Alembic upgrade → downgrade → upgrade; `alembic check`: no drift.
- Two separate Uvicorn processes: profile and JWT session persisted after restart.
- All **8 operations** executed through Swagger UI, including 401/403/404/409/422.
- Only test accounts were created; no main-site database or frontend was changed.
- Test server stopped after verification. A Starlette/httpx deprecation warning
  remains; it does not fail tests.

To repeat persistence + Swagger verification on a migrated `_test` database:
`pip install -r requirements-dev.txt`, `python -m playwright install chromium`,
then `python scripts/verify_live.py`. GitHub CI runs this same verification.
