# Leads Tracker

A public lead-intake form + internal, auth-guarded lead-management app.

**Stack:** FastAPI (API) · Next.js (web) · PostgreSQL (data) · MinIO/S3 (resume files) · Mailpit/SMTP (email).

Implements the spec in [docs/system-design.md](./docs/system-design.md); rationale in
[docs/design-choices.md](./docs/design-choices.md).

---

## Quick start

```bash
cp .env.example .env       # optional — sensible defaults are baked in
docker compose up --build
```

This brings up five services on one network, runs DB migrations, and seeds the demo attorney +
the resume bucket on first boot.

| What | URL |
|------|-----|
| Public lead form & internal dashboard | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Captured emails (Mailpit) | http://localhost:8025 |
| MinIO console | http://localhost:9001 (user/pass: `minioadmin` / `minioadmin`) |

**Demo attorney login:** `attorney@example.com` / `attorney123` (override in `.env`).

---

## Try it end to end

1. Open http://localhost:3000, fill the form, attach a PDF/DOC/DOCX, submit.
2. Open http://localhost:8025 — you'll see **two** emails: the prospect confirmation and the
   attorney notification.
3. Sign in at http://localhost:3000/login with the demo attorney.
4. On the dashboard: filter by state, toggle **Assigned to me**, download the resume, and click
   **Mark reached out** to move the lead `PENDING → REACHED_OUT`.

---

## Architecture

```
Next.js (web)  ──►  FastAPI (api)  ──►  PostgreSQL (db)
                         │       └───►  MinIO / S3  (resumes)
                         └───────────►  Mailpit / SMTP (email)
```

- **Backend** is layered — routers → services → repositories — with infra behind adapters
  (`storage`, `email`) and a swappable `AssignmentStrategy`. See [backend/app](./backend/app).
- **Lead submission** persists the lead **and** its active assignment in one transaction; the two
  emails are scheduled only *after* that commit, via `BackgroundTasks` (a slow mail provider never
  blocks or loses a submission).
- **Frontend** guards `/leads` with middleware; the JWT lives in an http-only cookie and the app
  proxies authenticated calls (list, state change, resume download) to the API server-side.

### Layout

```
backend/
  app/
    api/v1/         routers (leads, auth, health)
    services/       leads_service, email_service, auth_service, assignment/
    repositories/   SQLAlchemy data access
    adapters/       storage/ (S3/MinIO) · email/ (SMTP/console)
    models/         ORM models  ·  schemas/  Pydantic  ·  core/  config, db, security, deps
    migrations/     Alembic
frontend/
  app/              App Router: / (form), /login, /leads (dashboard), api/ (route handlers)
  lib/              server-side API client, types, session
docker-compose.yml  ·  .env.example
```

---

## API summary

Base path `/api/v1` (full interactive docs at `/docs`).

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/leads` | public | Submit a lead (multipart: fields + resume) → `201` |
| `GET` | `/leads` | required | List leads (`?state=`, `?assigned_to_me=true`, pagination, sort) |
| `GET` | `/leads/{id}` | required | Get one lead (with active assignee) |
| `GET` | `/leads/{id}/resume` | required | Streamed resume (or `?presigned=true` for a short-lived URL) |
| `PATCH` | `/leads/{id}/state` | required | Transition state (`{ "state": "REACHED_OUT" }`) |
| `POST` | `/auth/login` | public | Obtain a JWT |
| `GET` | `/auth/me` | required | Current user |
| `GET` | `/healthz` | public | Liveness/readiness |

---

## Configuration

All config is via environment variables (see [.env.example](./.env.example) and
[backend/app/core/config.py](./backend/app/core/config.py)). Nothing sensitive is committed —
`.env` is git-ignored.

**Local ↔ prod swaps** are config-only, thanks to the adapters:

| Concern | Local | Production |
|---------|-------|------------|
| Object storage | MinIO (`S3_ENDPOINT_URL=http://minio:9000`) | AWS S3 (unset endpoint, real creds/region) |
| Email | Mailpit (`EMAIL_BACKEND=smtp`, `SMTP_HOST=mailpit`) | SES/SendGrid SMTP creds, or a new adapter |
| Database | Postgres container | Managed Postgres (RDS/Cloud SQL/Neon/Supabase) |

---

## Notes & production hardening

- **Assignment** uses `SingleAttorneyStrategy` today (every lead → the one seeded attorney). Real
  routing (round-robin, practice area, load-based) is a drop-in `AssignmentStrategy` — no router,
  schema, or flow changes.
- **Not yet included** (called out in the design as prod concerns): rate limiting / CAPTCHA on the
  public form, TLS termination, AV scanning of uploads, and a real queue + worker for email retries
  (the `EmailAdapter` call site is unchanged when that lands).
