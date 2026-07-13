# Leads Tracker — Design Choices

Decision log explaining **why** the system is built the way it is. The authoritative
*what-to-build* spec lives in [system-design.md](./system-design.md); this document records the
active decisions, the alternatives considered, and how each choice is meant to evolve.

Format per decision: **Decision · Context · Rationale · Alternatives considered · Future evolution.**

---

## Scope & scale assumption

**Context:** Leads are submitted by humans filling a public form — low write volume, read-mostly
internal UI.

**Decision:** Build a simple synchronous request path with background email dispatch, rather than a
full queue/worker pipeline, while keeping clean seams to add one later.

**Rationale:** The volume doesn't justify the operational weight of a broker + workers; a layered
app with interfaces gets us testability and swap-ability without that cost.

---

## 1. Relational store → PostgreSQL

**Decision:** PostgreSQL (SQLAlchemy + Alembic migrations).

**Rationale:** Structured, relational, transactional data; strong typing (`enum` for `state`,
`citext` for email); good concurrency and indexing; still a single container locally.

**Alternatives considered:** *SQLite* — zero-config and fine for a demo, but Postgres better mirrors
production (concurrency, migration behavior, enum/index semantics) at no extra local-setup cost.

**Future evolution:** managed Postgres (RDS / Cloud SQL / Neon / Supabase), read replicas, PITR backups.

---

## 2. Auth → JWT (email + password)

**Decision:** Internal users log in with email + password and receive a short-lived **JWT** (optional
refresh). Passwords hashed with bcrypt/argon2. The token carries user id/email.

**Rationale:** Stateless, simple to verify in a FastAPI dependency, and the token identity is reused
to resolve "the current attorney" for the assignee filter (Decision 4).

**Alternatives considered:** *HTTP-only session cookie* — equally valid; JWT chosen for statelessness
and a clean verification seam. *Managed IdP now* — overkill for the assignment.

**Future evolution:** offload to an IdP (Auth0 / Cognito / Clerk / Google Workspace SSO); the
JWT-verification seam stays the same.

---

## 3. Lead → attorney assignment: mapping table + strategy interface

**Decision:** A dedicated `lead_assignments` mapping table (not an `assigned_attorney_id` FK on
`leads`), populated via a swappable `AssignmentStrategy.assign(lead) -> attorney_id`. Today's
implementation is `SingleAttorneyStrategy` (one seeded attorney gets every lead). Exactly **one
active assignment per lead**, created in the **same transaction** as the lead.

**Rationale:** Attorney-based routing is a stated future direction. A mapping table lets routing
evolve without a schema rewrite — it cleanly supports reassignment, an assignment history/audit
trail, and (later) multiple assignees per lead. The strategy interface keeps the routing decision in
one place; swapping real business logic in touches neither the router, the `leads` table, nor the
submission flow.

**Alternatives considered:** *Single FK column on `leads`* — simplest, but reassignment/history and
multi-assignee become schema migrations later; rejected for that rigidity.

**Future evolution:** real `AssignmentStrategy` (round-robin, by practice area, geography,
load-based) plus a reassignment UI.

---

## 4. "Assigned to me" filter derived from the token

**Decision:** `GET /leads?assigned_to_me=true` restricts results to leads whose active
`lead_assignments` row points at the JWT's user. The attorney is derived from the authenticated
token, never from a client-supplied email.

**Rationale:** Supports the future world where attorneys only want their own leads, and does so
securely — one user can't scope to another's leads by passing a different email. With one seeded
attorney today, "assigned to me" and "all leads" return the same set; the toggle becomes meaningful
once real routing exists.

**Alternatives considered:** *`?assigned_to={email}` free parameter* — rejected as an authorization
hole. A privileged admin variant (`?assigned_to={id}`) is a trivial future add.

---

## 5. Resume files → object storage, not the database

**Decision:** Store resumes in S3-compatible object storage (MinIO locally, S3 in prod); persist only
the **object key** in Postgres. Serve to authenticated attorneys via streamed download or short-lived
presigned URLs; the bucket is never public.

**Rationale:** Object stores are purpose-built and cheap for blobs. Storing files in Postgres bloats
the DB and hurts backups/replication. Using the S3 API locally (MinIO) means the same SDK code path
runs in production.

**Alternatives considered:** *BYTEA/blob in Postgres* — rejected (DB bloat, backup weight). *Local
filesystem volume* — rejected (doesn't mirror prod, no presigned access model).

**Future evolution:** S3 with lifecycle policies, versioning, encryption at rest; optional AV scan.

---

## 6. Email provider behind an adapter (Mailpit → SES/SendGrid)

**Decision:** All sending goes through an `EmailAdapter` interface (`send(to, template, context)`).
Local dev uses **Mailpit** (SMTP catcher with a web UI); production uses AWS SES or
SendGrid/Postmark/Resend; tests use a console/in-memory fake.

**Rationale:** Provider becomes a config choice, not a code change. Mailpit lets you *see* both the
prospect and attorney emails locally without real sends; the fake makes emails assertable in CI.

**Future evolution:** deliverability tooling (DKIM/SPF, bounce handling) comes free with SES/SendGrid.

---

## 7. Email is a post-commit side effect (failure semantics)

**Decision:** The two submission emails are scheduled **only after the lead and its assignment
commit**. If either persistence step fails, the transaction rolls back, **neither email is sent**, and
the prospect receives an error. On success, emails are dispatched via FastAPI `BackgroundTasks`,
decoupled from the HTTP response. The attorney email reads the already-persisted assignment — it
never re-runs the strategy.

**Rationale:** We must never notify anyone about a lead that wasn't durably stored and assigned.
Decoupling the actual send means a slow/failing mail provider can't block the prospect's submission or
lose the stored lead.

**Alternatives considered:** *Send inline before/around commit* — rejected: risks emailing about a
lead that then fails to persist, or blocking the user on a slow provider.

**Future evolution:** replace `BackgroundTasks` with a real queue (SQS/Redis + worker) for retries,
dead-lettering, and idempotency keys — the `EmailAdapter` call site is unchanged.

---

## 8. Local setup → Docker Compose (one command)

**Decision:** `docker compose up` brings up web, API, Postgres, MinIO, and Mailpit on one network,
with migrations and seed (demo attorney + bucket) on first boot.

**Rationale:** Satisfies the one-command local-setup requirement with a reproducible multi-service
environment that mirrors production topology.

**Future evolution:** containers on ECS/Kubernetes, CI/CD, IaC.

---

## 9. Backend structure → layered + adapters

**Decision:** Routers → services → repositories, with infra (storage, email) behind adapters.

**Rationale:** Routers stay thin and testable; business rules (state machine, assignment,
orchestration) live in services; infra behind adapters means tests use fakes and environments swap
implementations via config only.

---

## 10. Lead state machine kept centralized

**Decision:** A 2-state enum (`PENDING → REACHED_OUT`) with the transition enforced in the service
layer; illegal transitions return `409 Conflict`.

**Rationale:** Centralizing the rule makes it trivial to add future states (e.g. `CONTACTED`,
`CONVERTED`, `REJECTED`) and, later, an audit log of transitions.

---

## Summary — technology choices

| Choice | Why (short) |
|--------|-------------|
| **FastAPI** | Required; async, Pydantic validation, auto OpenAPI docs, clean DI. |
| **Next.js** | Required; App Router, SSR for the guarded dashboard, simple public form. |
| **PostgreSQL** | Production-grade relational store; enums, indexes, migrations; one container. |
| **JWT auth** | Stateless; token identity reused for the assignee filter. |
| **`lead_assignments` + strategy** | Future-proofs attorney routing without schema/flow rewrites. |
| **S3/MinIO** | Right tool for blobs; identical SDK path local↔prod; keeps DB lean. |
| **Mailpit → SES/SendGrid** | See every email locally; real deliverability in prod; swappable adapter. |
| **Docker Compose** | One-command local setup; reproducible multi-service environment. |
| **Adapters + layers** | Testability and clean prod/dev swaps without touching business logic. |
