# AcmeCloud Data Model

## Source of Truth

The executable schema is `database/schema.sql`. The deterministic fixture is `database/seed.sql`. The web bootstrap records `001_initial_schema` in `schema_migrations`, applies the schema once, and then runs the idempotent seed.

All application timestamps use MySQL `DATETIME(6)` values interpreted as UTC. Seed timestamps are fixed values so a reset produces the same snapshot. IDs are explicit stable unsigned integers in the seed and auto-incrementing unsigned integers for later application writes.

## Entity Relationships

```text
users
  |
  +---- projects (owner_id)
  |       |
  |       +---- project_members ---- users
  |       |
  |       +---- files ------------- users (owner_id)
  |       |
  |       +---- comments ---------- users (author_id)
  |
  +---- messages (sender_id / recipient_id)
  |
  +---- notifications
  |
  +---- api_keys
  |
  +---- audit_logs (actor_id)
  |
  +---- email_verifications
  |
  +---- password_resets
  |
  +---- password_history
  |
  +---- point_balances
  |
  +---- point_redemptions
  |
  +---- challenge_progress
  |
  `---- lab_attempts

projects
  +---- files
  +---- comments
  +---- shares
  +---- webhook_configs
  `---- import_jobs
```

## Core Tables

| Table | Responsibility | Important constraints |
|---|---|---|
| `users` | Local identities, roles, status, profile data | Unique username/email; role and status checks; password hash only |
| `projects` | Workspace ownership and settings | Owner foreign key; unique slug; visibility check; JSON settings |
| `project_members` | Per-project membership and role | Composite primary key; project/user foreign keys; role check |
| `files` | File metadata and future storage references | Owner/project foreign keys; unique storage name; kind check |
| `messages` | Direct messages and threads | Sender/recipient foreign keys; self-referencing thread foreign key |
| `comments` | Project comments and soft deletion | Project/author foreign keys |
| `notifications` | User notifications and event payloads | User foreign key; JSON payload |
| `api_keys` | Fake local API key fixtures | User foreign key; unique key hash; scoped JSON |
| `audit_logs` | Product event history | Nullable actor foreign key; JSON parameters and metadata |
| `system_settings` | Admin-managed settings | Primary setting key; optional updater foreign key; type check |

## Supporting Tables

`email_verifications`, `password_resets`, `shares`, `webhook_configs`, `import_jobs`, `point_balances`, `point_redemptions`, `challenge_progress`, `lab_attempts`, and `password_history` are schema-only in Phase 2.2a. They exist to establish stable relationships for later business and training phases; no corresponding Web route or API is implemented yet.

## Seed Roles and Ownership

| Identity | Role | Ownership/membership |
|---|---|---|
| `admin@example.local` | `admin` | Owns `Operations`; owner member of Operations |
| `manager@example.local` | `manager` | Owns `Product`; manager member of Operations |
| `alice@example.local` | `user` | Owns `Project Alpha` |
| `bob@example.local` | `user` | Owns `Project Beta`; viewer member of Project Alpha |
| `charlie@example.local` | `user` | Owns `Project Gamma` |

Seed passwords are fake local-only fixtures. Only password hashes are stored in MySQL; the web application has no endpoint that exposes them.

## Repository Boundary

The current `LabRepository` reads schema/fixture data for tests and deterministic snapshots. It does not contain authorization decisions. Future routes should call services, services should call policy decisions where needed, and repositories should remain limited to persistence.
