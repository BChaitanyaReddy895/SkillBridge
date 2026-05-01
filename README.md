# SkillBridge Attendance API (Prototype)

Backend API for a fictional state-level attendance system with strict role-based access control and dual-token security for Monitoring Officer flows.

## 1) Live API Base URL

- Live base URL: `TODO_AFTER_DEPLOYMENT`
- Deployment note: this project is deployable on Render/Railway/Fly using `uvicorn src.main:app --host 0.0.0.0 --port $PORT`.

## 2) Local Setup (from scratch)

```bash
cd submission
python -m venv .venv
```

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Run API:

```bash
uvicorn src.main:app --reload
```

Swagger docs: `http://127.0.0.1:8000/docs`

Seed data:

```bash
python -m src.seed
```

Run tests:

```bash
pytest -q
```

## 3) DB Choice (SQLite-first, MySQL-ready)

This repo is intentionally lightweight for local development:

- Default local DB: SQLite (`DATABASE_URL=sqlite:///./skillbridge.db`)
- Optional MySQL: set `.env` `DATABASE_URL` to:
  - `mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME`
- Optional PostgreSQL/Neon: set `.env` `DATABASE_URL` to:
  - `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`

If using MySQL, install driver:

```bash
pip install pymysql
```

## 4) Seeded Test Accounts (all password `Pass@123`)

- Student: `student1@skillbridge.test`
- Trainer: `trainer1@skillbridge.test`
- Institution: `institution.north@skillbridge.test`
- Programme Manager: `pm@skillbridge.test`
- Monitoring Officer: `monitor@skillbridge.test`

## 5) JWT Payload Structures

Standard access token (`/auth/signup`, `/auth/login`):

```json
{
  "type": "access",
  "user_id": 123,
  "role": "student",
  "iat": 1714550000,
  "exp": 1714636400
}
```

Monitoring scoped token (`/auth/monitoring-token`):

```json
{
  "type": "monitoring",
  "scope": "read:monitoring",
  "user_id": 77,
  "role": "monitoring_officer",
  "aud": "monitoring",
  "iat": 1714550000,
  "exp": 1714553600
}
```

## 6) Curl Commands (all endpoints)

Set:

```bash
BASE_URL=http://127.0.0.1:8000
```

Signup:

```bash
curl -X POST "$BASE_URL/auth/signup" -H "Content-Type: application/json" -d "{\"name\":\"Student One\",\"email\":\"student.new@test.dev\",\"password\":\"Pass@123\",\"role\":\"student\"}"
```

Login:

```bash
curl -X POST "$BASE_URL/auth/login" -H "Content-Type: application/json" -d "{\"email\":\"student1@skillbridge.test\",\"password\":\"Pass@123\"}"
```

Create batch (trainer/institution):

```bash
curl -X POST "$BASE_URL/batches" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "{\"name\":\"Batch Delta\",\"institution_id\":1}"
```

Create invite:

```bash
curl -X POST "$BASE_URL/batches/1/invite" -H "Authorization: Bearer $TRAINER_TOKEN"
```

Join batch:

```bash
curl -X POST "$BASE_URL/batches/join" -H "Authorization: Bearer $STUDENT_TOKEN" -H "Content-Type: application/json" -d "{\"token\":\"INVITE_TOKEN\"}"
```

Create session:

```bash
curl -X POST "$BASE_URL/sessions" -H "Authorization: Bearer $TRAINER_TOKEN" -H "Content-Type: application/json" -d "{\"batch_id\":1,\"title\":\"Session X\",\"date\":\"2026-05-01\",\"start_time\":\"10:00:00\",\"end_time\":\"11:00:00\"}"
```

Mark attendance:

```bash
curl -X POST "$BASE_URL/attendance/mark" -H "Authorization: Bearer $STUDENT_TOKEN" -H "Content-Type: application/json" -d "{\"session_id\":1,\"status\":\"present\"}"
```

Session attendance (trainer):

```bash
curl -X GET "$BASE_URL/sessions/1/attendance" -H "Authorization: Bearer $TRAINER_TOKEN"
```

Batch summary (institution):

```bash
curl -X GET "$BASE_URL/batches/1/summary" -H "Authorization: Bearer $INSTITUTION_TOKEN"
```

Institution summary (programme manager):

```bash
curl -X GET "$BASE_URL/institutions/1/summary" -H "Authorization: Bearer $PM_TOKEN"
```

Programme summary (programme manager):

```bash
curl -X GET "$BASE_URL/programme/summary" -H "Authorization: Bearer $PM_TOKEN"
```

Monitoring token (requires Monitoring Officer access token + API key):

```bash
curl -X POST "$BASE_URL/auth/monitoring-token" -H "Authorization: Bearer $MONITOR_ACCESS_TOKEN" -H "Content-Type: application/json" -d "{\"key\":\"monitoring-key-change-me\"}"
```

Monitoring attendance (scoped token only):

```bash
curl -X GET "$BASE_URL/monitoring/attendance" -H "Authorization: Bearer $MONITOR_SCOPED_TOKEN"
```

## 7) Schema Decisions

- `batch_trainers`: explicit many-to-many table lets one batch be co-managed by multiple trainers without duplicating trainer fields on `batches`.
- `batch_invites`: invite token table captures creator, expiry, and one-time-use status; easier to audit and revoke invite links.
- Dual token for Monitoring Officer:
  - Login token proves identity and role.
  - Scoped short-lived monitoring token limits blast radius and can be constrained to read-only monitoring endpoints.

## 8) What Works / Partial / Skipped

- Fully working:
  - Core entity models and relationships
  - Role-guarded protected endpoints with server-side 403 enforcement
  - JWT signup/login (24h) and monitoring scoped token (1h)
  - Validation errors (422), missing auth (401), forbidden access (403), and 404 FK checks
  - Seed script with required data volume
  - Required five pytest tests
- Partially done:
  - Live deployment URL not filled yet (depends on platform account setup)
- Skipped:
  - Alembic migrations (using `create_all` for take-home speed)
  - Token blacklist/revocation store (documented below)

## 9) Security Note (current limitation + improvement)

- Current limitation: access/monitoring tokens are stateless JWTs, so early revocation is not implemented.
- With more time: add `jti` claim + Redis denylist (or DB table) and rotate signing keys via KMS-backed key management.

## 10) Token Rotation / Revocation Approach (production)

- Access token short-lived + refresh token flow
- Key rotation with `kid` headers and active key set in JWKS/secret manager
- Revocation list for compromised tokens
- Monitoring API key rotation schedule with overlap window and audit logs
