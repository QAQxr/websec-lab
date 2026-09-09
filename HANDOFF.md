# WebSec Lab Handoff

## Document Purpose

This is the current handoff and status document for WebSec Lab. Update it after every phase, design correction, verification run, or known-issue change.

**Last updated:** 2026-09-09

**Project path:** `~/opencode/projects/websec-lab`

**GitHub repository:** `https://github.com/QAQxr/websec-lab`

## Current Status

**Current phase:** Phase 2.2c HTML and REST project CRUD plus shared authorization model finalized locally

**Active work:** No active implementation process. The Phase 2.1 Docker stack is running with the Phase 2.2a schema/seed, Phase 2.2b authentication foundation, and the Phase 2.2c HTML/REST project workflows loaded.

**Next allowed increment:** Membership mutation, ownership transfer, and share-token behavior require separate approval

**Intentional vulnerabilities:** None implemented

**Working tree:** Contains uncommitted local Phase 2.2c REST parity, test, and documentation changes; no commit or push was created in this task.

**Branch:** `main`

**Phase 2.2a implementation commit:** `5f6e62e Fix Phase 2.2a schema idempotency and handoff metadata`

**Phase 2.2b implementation commit:** `31fc67e Implement Phase 2.2b authentication foundation`

**Phase 2.2b closeout fix commit:** `c3b10f0 Fix Phase 2.2b mailbox access and registration consistency`

**Current HEAD before the local Phase 2.2c REST parity changes:** `87e8a99`.

**Remote state:** `main` and `origin/main` were synchronized at `87e8a99` before the local Phase 2.2c REST parity changes.

## What Has Been Completed

### Design

The initial `PROJECT_DESIGN.md` was reviewed against the six implementation-readiness requirements.

The design now specifies:

* Docker/network isolation as the primary egress boundary.
* `LAB_EGRESS=deny` as an application-level experiment guard only.
* No public Nginx `/uploads/` path.
* Flask file authorization before future file delivery.
* MySQL for integration/security behavior; SQLite only for pure unit tests.
* Route -> Service -> Policy -> Repository responsibilities.
* Lab-only identifiers such as `LAB-SQLI-001` instead of CVE-like identifiers.
* Phase 2.1 infrastructure separated from future Phase 2.2 application work.

### Phase 2.1 Infrastructure

Implemented:

* Docker Compose services: Nginx, Flask web, MySQL, Redis, internal-api.
* Basic Flask landing page at `/`.
* JSON health endpoint at `/health`.
* Private internal-api endpoint at `/internal/health`.
* Web-to-MySQL connectivity check.
* Web-to-Redis connectivity check.
* Web-to-internal-api connectivity check.
* Deterministic MySQL bootstrap marker.
* Named volumes for MySQL, Redis, uploads, and mail data.
* Non-root web and internal-api containers.
* Read-only application containers with temporary filesystems.
* No Docker socket, home directory, SSH key, or credential mounts.
* Reset script that recreates the stack and named volumes.
* Container integration tests and pure configuration unit tests.

### Phase 2.2a Database Model and Deterministic Seed

Implemented:

* Canonical MySQL schema in `database/schema.sql`.
* Migration metadata in `schema_migrations` and migration guidance in `database/migrations/`.
* Core tables: users, sessions, projects, project_members, files, messages, comments, notifications, api_keys, audit_logs, system_settings.
* Supporting schema tables for verification, reset, sharing, imports, points, training, attempts, and password history.
* Deterministic local-only users, projects, ownership, memberships, files, messages, comments, notifications, fake API keys, audit logs, and system settings.
* Minimal typed records and `LabRepository` snapshot layer.
* MySQL schema/seed integration tests and SQLite pure unit coverage.
* Two-reset deterministic snapshot verification.
* Direct schema replay verification without duplicate table or constraint errors.
* Data-model documentation at `docs/architecture/data-model.md`.

### Phase 2.2b Authentication Foundation

Implemented:

* Registration with username/email validation, confirmation checks, pending status, and maintained scrypt password hashing.
* Random one-time email verification tokens with hashed database storage, expiry, and local Redis mailbox output.
* Login with pending/locked checks, server-side Redis sessions, MySQL session rows, last-login updates, and session rotation.
* Logout with server-side invalidation and expired authentication cookie.
* HttpOnly/SameSite cookie policy with configurable Secure behavior for local HTTP versus HTTPS-like deployments.
* Safe `/profile` session display and authenticated `/dashboard`.
* Password, session, authentication, verification, logout, dashboard, and security regression tests.
* Authentication architecture documentation at `docs/architecture/authentication.md`.

### Phase 2.2b Closeout Fix

Implemented and synchronized before the current local Phase 2.2c authorization changes:

* `/dev/mail` remains local/test-only and now requires an authenticated admin; disabled environments return 404 and other users receive 403.
* Registration creates the pending user and verification record in one MySQL transaction.
* Redis mailbox failure triggers mailbox cleanup and compensating deletion of the new verification/user state.
* Mailbox permission and registration failure-injection integration tests cover success, unauthorized access, admin access, production-like disablement, and recovery.

### Phase 2.2c HTML Project CRUD Foundation

Implemented locally without intentional vulnerabilities:

* Authenticated project list and create/detail/edit/delete HTML workflows.
* `ProjectPolicy.access_for()` as the single structured authorization truth source.
* Active authentication, global admin capability, project membership, ownership, visibility, and action-specific capability boundaries.
* Owner, manager, viewer, contributor-read, team read-only, shared private-like, and non-member authorization boundaries.
* Separate metadata-edit and visibility-edit capabilities; managers cannot change visibility.
* Owner membership creation in the same transaction as project creation.
* Explicit repository scopes for global admin, authenticated team visibility, and deny.
* Parameterized project queries with owner/member/team/global object filtering.
* Consistent GET/POST edit authorization and fail-closed owner mismatch handling.
* Stable slug generation with collision suffixes; slugs remain stable during edits.
* Project policy unit tests and MySQL/Redis-backed integration authorization tests.

Deferred by scope:

* Membership invite, role-change, and removal routes.
* Ownership transfer.
* Share-token access.
* CSRF protection and intentional vulnerability behavior.

### Phase 2.2c REST Project Parity

Implemented locally without intentional vulnerabilities:

* `/api/projects` list and create routes.
* `/api/projects/<project_id>` detail, PATCH, and DELETE routes.
* Existing session authentication with 401 responses for guest, pending, and locked principals.
* Shared `ProjectService`, `ProjectPolicy`, validation, ownership, membership, visibility, and repository scope behavior.
* Explicit JSON success/error envelopes and status mapping for validation, authentication, authorization, not-found, conflict, and infrastructure failures.
* Explicit project serialization that separates membership role from global role and excludes internal fields.
* REST/HTML authorization parity, IDOR regression tests, owner mismatch tests, and mass-assignment tests.
* REST architecture documentation at `docs/architecture/rest.md`.

Deferred by scope:

* Membership invite, role-change, and removal routes.
* Ownership transfer.
* Share-token access.
* CSRF protection and intentional vulnerability behavior.

## Runtime Topology

```text
Browser
  |
  | 127.0.0.1:8080
  v
Nginx
  | host_ingress (Nginx only)
  | proxy_private (internal)
  v
Flask web
  | proxy_private (internal)
  | app_private (internal)
  +--> MySQL
  +--> Redis
  `--> internal-api
```

Private networks use:

```text
internal: true
com.docker.network.bridge.inhibit_ipv4: "true"
```

The first option removes the default external route. The second prevents the host from routing directly to private container IPs. `host_ingress` is intentionally non-internal because Docker cannot publish the loopback Nginx port from an internal bridge network.

Only this host mapping exists:

```text
127.0.0.1:8080 -> nginx:80
```

MySQL, Redis, and internal-api have no host port mappings.

## Current Runtime State

Expected healthy services:

```text
websec-lab-nginx-1
websec-lab-web-1
websec-lab-mysql-1
websec-lab-redis-1
websec-lab-internal-api-1
```

Active named volumes:

```text
websec_lab_mysql_data
websec_lab_redis_data
websec_lab_uploads
websec_lab_mail
```

The obsolete network `websec_lab_public_edge` from the initial topology attempt was inspected, confirmed empty, and removed. No other project network was modified.

## How To Run

From the project root:

```bash
docker compose up -d --build
```

Open:

```text
http://127.0.0.1:8080/
http://127.0.0.1:8080/health
```

Run tests:

```bash
docker compose --profile test run --rm test-runner
./scripts/verify_phase21.sh
```

Reset the disposable local state:

```bash
./scripts/reset.sh
```

The reset removes this Compose project's named volumes and recreates the stack. It does not remove unrelated Docker resources.

Stop without deleting volumes:

```bash
docker compose down --remove-orphans
```

## Verification Baseline

The following checks have passed after a reset:

* `docker compose up -d` starts all services.
* Nginx landing page returns AcmeCloud/WebSec Lab HTML.
* `/health` returns database, Redis, and internal-api status `ok`.
* Nginx does not expose `/internal/health`.
* Full unit and integration suite after REST parity: `69 passed`.
* REST project API integration and service-delegation suite: `17 passed`.
* HTML project authorization tests remain green inside the full suite.
* HTML/REST authorization parity: passed.
* Project IDOR defense and serialization boundary tests: passed.
* Phase 2.2a schema/seed assertions remain covered inside the full suite.
* Mailbox permission and registration compensation tests pass.
* Direct `schema.sql` replay: two consecutive executions passed.
* Host and network verification script passes.
* Direct host TCP access to the actual MySQL, Redis, and internal-api container IPs is blocked.
* Web container cannot fetch `http://example.com`.
* Reset recreates the database bootstrap state and passes the same checks.
* Two full volume resets produced identical deterministic seed snapshots.

The host has an unrelated listener on `127.0.0.1:3306`. The WebSec Lab Compose project does not publish MySQL; the verification script reports this external listener without treating it as the lab service.

## Known Issues and Risks

* Phase 2.1, Phase 2.2a, Phase 2.2b, and Phase 2.2c authorization finalization are saved on GitHub through `87e8a99`; the current REST parity changes remain uncommitted locally.
* Docker Compose reports that buildx is not installed and uses the fallback builder; buildx is intentionally not installed because the project builds and tests successfully without it.
* Active MySQL and Redis volume sizes have not been measured separately.
* The host has an unrelated listener on `127.0.0.1:3306`; it was not modified. The Compose project does not publish MySQL.
* Membership mutation, ownership transfer, share-token access, and CSRF remain deferred.
* `/dev/mail` intentionally exposes raw verification links only to local/test admins; it is not a real mail service.
* Registration compensation cannot guarantee recovery from a host-wide MySQL outage during the compensating delete; the route remains a generic 503 and no normal success is reported.
* No learning mode, challenge mode, audit mode, PoC, patch, or vulnerability test exists yet.
* No intentional SQLi, XSS, CSRF, IDOR, SSRF, upload, traversal, command injection, SSTI, XXE, deserialization, race, or authorization flaw has been added.

## Commit History

| Commit | Meaning |
|---|---|
| `88ea430` | Initial `PROJECT_DESIGN.md` |
| `5f961f9` | Readiness corrections for Phase 2.1 safety and scope |
| `35625e5` | Corrected Nginx host-ingress topology |
| `ab720c7` | Added strict private bridge isolation |
| `99e2ab3` | Implemented Phase 2.1 infrastructure baseline |
| `2ff431b` | Added project handoff document and saved Phase 2.1 state |
| `b910d9d` | Implemented Phase 2.2a data model and deterministic seed |
| `66ad03f` | Updated Phase 2.2a handoff status |
| `c91f457` | Closed Phase 2.2a open questions |
| `634c749` | Recorded Phase 2.2a remote synchronization |
| `5f6e62e` | Fixed Phase 2.2a schema replay idempotency and added regression coverage |
| `31fc67e` | Implemented Phase 2.2b authentication foundation |
| `c3b10f0` | Fixed Phase 2.2b mailbox access and registration consistency |
| `d78c63f` | Implemented Phase 2.2c HTML project CRUD foundation |
| `87e8a99` | Finalized Phase 2.2c authorization model |

## Next Work

The HTML and REST project CRUD plus shared authorization model are complete locally after full verification. The next implementation plan should be reviewed and explicitly approved before adding membership mutation, ownership transfer, or share-token behavior.

Recommended next increment order:

1. Add separately approved membership invite, role-change, and removal workflows.
2. Add ownership transfer and share-token behavior only after the corresponding policy and test design is approved.
3. Re-run the full Phase 2.1, Phase 2.2a, Phase 2.2b, and Phase 2.2c regression suites after each increment.

Do not introduce vulnerability behavior until the normal business workflow is stable and a separate phase is approved.

## Handoff Procedure

The next agent should:

1. Read this document and `PROJECT_DESIGN.md`.
2. Check `git status --short --branch` before editing.
3. Check `docker compose ps` before restarting or resetting services.
4. Preserve the three-network topology and private-network verification.
5. Keep integration/security tests on MySQL.
6. Keep vulnerability work out of Phase 2.1 and Phase 2.2 core business implementation.
7. Update this document and the task audit log after meaningful changes.
