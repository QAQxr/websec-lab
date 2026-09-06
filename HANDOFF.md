# WebSec Lab Handoff

## Document Purpose

This is the current handoff and status document for WebSec Lab. Update it after every phase, design correction, verification run, or known-issue change.

**Last updated:** 2026-09-06

**Project path:** `~/opencode/projects/websec-lab`

**GitHub repository:** `https://github.com/QAQxr/websec-lab`

## Current Status

**Current phase:** Phase 2.2a complete

**Active work:** None. The Phase 2.1 Docker stack is currently running with the Phase 2.2a schema and seed loaded.

**Next allowed phase:** Phase 2.2b, only after explicit approval

**Intentional vulnerabilities:** None implemented

**Working tree:** Clean at the last handoff verification; update this line if new uncommitted work appears.

**Branch:** `main`

**Current phase commit:** To be recorded after the Phase 2.2a commit.

**Remote state:** Phase 2.1 is saved on GitHub at `1f4dd82`; Phase 2.2a changes are currently local and unpushed.

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
* Data-model documentation at `docs/architecture/data-model.md`.

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

An obsolete network named `websec_lab_public_edge` remains from the initial topology attempt. It is not used by the current Compose file.

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
* Container integration and unit tests: `12 passed`.
* Host and network verification script passes.
* Direct host TCP access to the actual MySQL, Redis, and internal-api container IPs is blocked.
* Web container cannot fetch `http://example.com`.
* Reset recreates the database bootstrap state and passes the same checks.

The host has an unrelated listener on `127.0.0.1:3306`. The WebSec Lab Compose project does not publish MySQL; the verification script reports this external listener without treating it as the lab service.

## Known Issues and Risks

* Phase 2.1 is saved on GitHub; Phase 2.2a is local and has not been pushed yet.
* `websec_lab_public_edge` is an obsolete cleanup candidate.
* Docker Compose reports that buildx is not installed and uses the fallback builder.
* Active MySQL and Redis volume sizes have not been measured separately.
* No registration/login/session workflow or REST business API exists yet; the `sessions` table is schema-only.
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

## Next Work

Do not start Phase 2.2b automatically. The next implementation plan should be reviewed and explicitly approved first.

Recommended Phase 2.2b order:

1. Add registration, simulated email verification, login, logout, and session display.
2. Add MySQL integration tests for authentication and session lifecycle.
3. Add a minimal dashboard and project CRUD without intentional vulnerabilities.
4. Re-run the full Phase 2.1 and Phase 2.2a regression suites after each increment.

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
