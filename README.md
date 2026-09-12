# WebSec Lab

Phase 2.1, Phase 2.2a, Phase 2.2b, Phase 2.2c, Phase 2.2d, and Phase 2.2e provide the AcmeCloud infrastructure, deterministic database baseline, authentication foundation, normal HTML/REST project workflow, membership mutation, and ownership transfer workflow:

```text
Browser -> 127.0.0.1:8080 -> Nginx -> Flask web
                                      |-> MySQL
                                      |-> Redis
                                       `-> internal-api
```

## Start

```bash
docker compose up -d --build
```

Open `http://127.0.0.1:8080/` and check `http://127.0.0.1:8080/health`.

Only Nginx publishes a host port. MySQL, Redis, and internal-api are private Compose services. Both application networks are Docker `internal` networks, so the default runtime has no public egress path. `LAB_EGRESS=deny` remains an application-level guard and is not the network isolation mechanism.

## Tests and Verification

```bash
docker compose --profile test run --rm test-runner
./scripts/verify_phase21.sh
./scripts/verify_determinism.sh
```

Integration and schema tests run against the Compose MySQL 8.4 service. SQLite is reserved for pure unit tests.

The Phase 2.2a fixture contains fake local-only users, projects, memberships, files, messages, comments, notifications, API keys, audit logs, and system settings. Authenticated users can access the HTML and REST project list/create/detail/edit/delete workflows and the Phase 2.2d membership invite/role-change/removal workflows through shared service, policy, and repository layers. Phase 2.2c/2.2d finalize active authentication, global admin capability, project membership, ownership, visibility, field-level edit, target-aware mutation, object-scope, JSON serialization, and HTML/REST parity boundaries. See [`docs/architecture/rest.md`](docs/architecture/rest.md) and [`docs/architecture/membership.md`](docs/architecture/membership.md).

## Authentication Foundation

Phase 2.2b provides normal, non-vulnerable registration, simulated email verification, login, logout, server-side sessions, a safe profile/session view, and a minimal dashboard.

Open `http://127.0.0.1:8080/register` to create a local account. New accounts are pending until the verification link is opened from the local-only mailbox at `http://127.0.0.1:8080/dev/mail`. The mailbox does not send real email.

Authentication uses MySQL for users, verification records, and session audit rows, and Redis for active session state. The cookie contains only an opaque session identifier and is HttpOnly with SameSite=Lax. Local HTTP defaults to `Secure=false`; HTTPS-like deployments should set `SESSION_COOKIE_SECURE=true`.

The current phase does not include share-token routes, file/folder routes, password reset, CSRF protection, other REST business APIs, or intentional vulnerabilities.

## Reset

The reset script removes this Compose project's named volumes and recreates the stack:

```bash
./scripts/reset.sh
```

This is a disposable local training environment. Do not add real credentials, host mounts, SSH keys, Docker socket mounts, or production data.
