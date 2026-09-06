# WebSec Lab

Phase 2.1 and Phase 2.2a provide the AcmeCloud infrastructure and deterministic database baseline:

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

The Phase 2.2a fixture contains fake local-only users, projects, memberships, files, messages, comments, notifications, API keys, audit logs, and system settings. No business API exposes this data yet.

## Reset

The reset script removes this Compose project's named volumes and recreates the stack:

```bash
./scripts/reset.sh
```

This is a disposable local training environment. Do not add real credentials, host mounts, SSH keys, Docker socket mounts, or production data.
