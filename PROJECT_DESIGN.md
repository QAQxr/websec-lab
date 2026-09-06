# WebSec Lab

## Project Design

**Product name:** AcmeCloud

**Repository folder:** `~/opencode/projects/websec-lab`

**Document status:** Phase 1 design baseline

**Scope:** local-only Web security training lab; no production deployment

**Implementation status:** design only; application code has not started

---

## 0. Design Decisions

WebSec Lab will be a small but coherent SaaS product rather than a collection of isolated vulnerability pages. AcmeCloud will provide projects, team membership, files, messages, comments, profile settings, API access, and an administrator console. The security exercises will emerge from ordinary business workflows.

The application will have one Flask web application with clear internal boundaries instead of many independently deployed application services. This keeps the code readable for beginners while still exposing routing, service, repository, session, database, cache, queue, reverse-proxy, and internal-network behavior.

The lab will ship with two controlled variants:

| Variant | Purpose |
|---|---|
| `vulnerable` | Reproduces the intended lab behavior and vulnerability chains inside the local container network. This is the default learning target. |
| `patched` | Applies the final fixes and is used by regression tests and patch-diff exercises. |

The vulnerable variant is not a production fallback. It is deliberately isolated, seeded with fake accounts and fake data, and bound to localhost only.

The first implementation will prioritize these qualities, in order:

1. A reproducible application that starts and resets reliably.
2. A readable business domain with ordinary user workflows.
3. A small number of complete vulnerability chains.
4. A matching patched implementation and verification tests.
5. Additional advanced labs only after the core remains stable.

The first release will not attempt to implement every requested vulnerability at once. The map below records the full target design; the roadmap controls when each item is introduced.

---

# A. Architecture Design

## A.1 Runtime Topology

```text
Browser / Burp Suite
        |
        | http://127.0.0.1:8080
        v
      nginx
        |
        | HTML, static files, uploads, API proxy
        v
      web (Flask modular monolith)
        |          |             |
        |          |             +-- internal-api (not host published)
        |          |
        |          +-- redis (sessions, cache, queue, temporary jobs)
        |
        +------------- mysql (default) / sqlite (test profile)
```

The browser can reach only Nginx. Docker DNS names such as `internal-api`, `mysql`, and `redis` are not exposed to the host. The web container can reach internal services because it is attached to the private application network. This distinction is necessary for the SSRF and network-boundary exercises.

## A.2 Components

| Component | Responsibility | Initial implementation |
|---|---|---|
| `nginx` | Host entry point, static files, upload routing, API proxying, request headers, access log | Nginx container, host binding on `127.0.0.1:8080` |
| `web` | Flask routes, authentication, business services, HTML templates, REST API | Python 3 + Flask + SQLAlchemy-compatible repository layer |
| `mysql` | Primary relational store | MySQL 8 for the default Compose profile |
| `redis` | Session store, cache, queue simulation, temporary import data, rate-limit state | Redis 7 with no host port |
| `internal-api` | Private service containing status, configuration, and service-account fixtures | Small Flask service on the private network only |
| named volumes | Database, Redis, and uploaded file persistence | Compose-managed local volumes |

## A.3 Flask Package Layout

The implementation will use a modular monolith with dependency direction from routes to services to repositories/models. Routes will not contain raw SQL, filesystem policy, or subprocess policy except where a lab intentionally demonstrates a flawed boundary.

```text
backend/
├── app.py
├── config.py
├── extensions.py
├── routes/
│   ├── auth.py
│   ├── dashboard.py
│   ├── profile.py
│   ├── projects.py
│   ├── files.py
│   ├── messages.py
│   ├── comments.py
│   ├── api.py
│   ├── admin.py
│   ├── training.py
│   └── dev.py
├── services/
│   ├── auth_service.py
│   ├── project_service.py
│   ├── file_service.py
│   ├── message_service.py
│   ├── notification_service.py
│   ├── import_service.py
│   ├── report_service.py
│   └── training_service.py
├── repositories/
├── models/
├── middleware/
│   ├── auth.py
│   ├── permissions.py
│   ├── request_context.py
│   └── audit.py
├── utils/
├── templates/
├── static/
└── migrations/
```

The directory names are stable extension points. A new lab should normally add or adapt a business service and a test, not create a top-level `vulnerability.py` or a standalone vulnerability route.

## A.4 Request Lifecycle

Every important workflow should be traceable as:

```text
Browser form or fetch
  -> Nginx access log
  -> Flask route
  -> authentication and request context
  -> service method
  -> repository/model or external client
  -> response serializer or template
  -> browser DOM
```

The design intentionally supports both server-rendered HTML and JSON API requests for the same service methods. This lets a learner compare browser behavior, raw HTTP, and source code without learning two unrelated applications.

## A.5 Layer Boundaries

The application uses an explicit request-to-data boundary:

```text
Route
  -> Service
  -> Policy (when the operation is protected)
  -> Repository
  -> database or approved infrastructure client
```

* **Route:** Parses HTTP input, selects the service operation, and serializes the response. It does not make object-authorization decisions or build SQL.
* **Service:** Orchestrates the use case, validates business invariants, invokes policy decisions, and controls the transaction boundary.
* **Policy:** Makes the final authorization decision from the principal, action, resource, membership, role, and request context. It does not load arbitrary data or render responses.
* **Repository:** Performs persistence and narrowly scoped queries. It does not decide whether a caller may access a resource.

Public infrastructure endpoints in Phase 2.1 have no protected resource and therefore do not need an authorization policy. The boundary is still preserved so later authenticated routes cannot move authorization into individual routes or repositories.

## A.6 Configuration Profiles

Configuration will be explicit rather than inferred from host state.

| Setting | Default | Purpose |
|---|---|---|
| `LAB_VARIANT` | `vulnerable` | Selects vulnerable or patched service behavior |
| `DATABASE_URL` | MySQL Compose URL | Runtime database; SQLite is selected only by pure unit-test processes |
| `REDIS_URL` | `redis://redis:6379/0` | Session and queue backend |
| `INTERNAL_API_URL` | `http://internal-api:8081` | Private service target for the SSRF chain |
| `LAB_EGRESS` | `deny` | Application-level guard; Docker `internal` networks provide the default network-level egress boundary |
| `LEARNING_MODE` | `off` | Enables hints and data-flow views for an authenticated learner |
| `AUDIT_MODE` | `off` | Enables source/config/schema bundles only in the local lab |
| `SEED_DATA` | `true` | Creates deterministic fake users and business objects |
| `SECRET_KEY` | generated by local bootstrap | Never use a production secret or a host credential |

The vulnerable behavior is selected by a lab registry and feature flags, not by exposing routes named after vulnerability types. A learner should see the same product navigation in normal and challenge modes.

## A.7 Frontend Structure

The frontend will remain server-rendered HTML with small JavaScript modules.

```text
frontend/
├── pages/
│   ├── auth/
│   ├── dashboard/
│   ├── projects/
│   ├── files/
│   ├── messages/
│   ├── admin/
│   └── training/
└── static/
    ├── css/
    ├── js/
    │   ├── api.js
    │   ├── dashboard.js
    │   ├── project.js
    │   ├── messages.js
    │   ├── settings.js
    │   └── training.js
    └── assets/
```

The UI will use the same API endpoints that Burp can capture. JavaScript will progressively enhance pages rather than hide core operations behind client-only state.

---

# B. Database Design

## B.1 Storage Strategy

MySQL is the default runtime database and the required database for integration and security tests. SQLite is supported only for pure unit tests that do not depend on SQL dialect behavior, transactions, locking, isolation, or concurrency. SQLAlchemy models and a small repository abstraction will keep business code portable. SQLi, blind SQLi, transaction, locking, and race-condition tests must run against MySQL so their behavior matches the target runtime.

Migrations and seed data will be deterministic. A reset must remove named volumes, recreate schema, and reproduce the same identifiers and relationships.

## B.2 Core Tables

### `users`

| Column | Type / rule | Purpose |
|---|---|---|
| `id` | integer primary key | Stable object identifier used by normal routes and IDOR exercises |
| `username` | unique varchar | Display and login identifier |
| `email` | unique varchar | Login and notification address |
| `password_hash` | varchar | Password hash; seed passwords are local-only |
| `role` | enum-like varchar | `user`, `manager`, or `admin` |
| `status` | varchar | `pending`, `active`, `locked` |
| `bio` | text | Profile content and stored-rendering exercise |
| `website` | varchar | Profile URL and URL validation exercise |
| `avatar_file_id` | nullable foreign key | Uploaded profile avatar |
| `email_verified_at` | nullable datetime | Simulated verification flow |
| `last_login_at` | nullable datetime | Account activity |
| `created_at` | datetime | Audit and display |

### `sessions`

| Column | Type / rule | Purpose |
|---|---|---|
| `id` | primary key | Application session identifier |
| `user_id` | foreign key | Session owner |
| `session_key` | unique varchar | Redis key reference or database fallback |
| `remember_me` | boolean | Long-lived session behavior |
| `created_at` | datetime | Session fixation analysis |
| `last_seen_at` | datetime | Expiration and activity |
| `ip_address` | varchar | Request context and logging lab |
| `user_agent` | varchar | Session audit |

### `projects`

| Column | Type / rule | Purpose |
|---|---|---|
| `id` | primary key | Project object identifier |
| `owner_id` | foreign key to users | Project owner |
| `name` | varchar | Project title |
| `slug` | unique nullable varchar | Human-friendly URL, not the sole authorization key |
| `description` | text | Comment and stored-rendering data flow |
| `visibility` | varchar | `private`, `team`, or `shared` |
| `settings_json` | text/json | Project preferences and merge behavior |
| `created_at` | datetime | Timeline |
| `updated_at` | datetime | Timeline |

### `project_members`

Composite key `(project_id, user_id)`.

| Column | Type / rule | Purpose |
|---|---|---|
| `project_id` | foreign key | Project relation |
| `user_id` | foreign key | Member relation |
| `member_role` | varchar | `viewer`, `contributor`, `manager`, `owner` |
| `invited_by` | foreign key | Invitation audit |
| `created_at` | datetime | Membership history |

### `files`

| Column | Type / rule | Purpose |
|---|---|---|
| `id` | primary key | File object identifier |
| `project_id` | nullable foreign key | Project file relation |
| `owner_id` | foreign key | Upload owner |
| `original_name` | varchar | User-visible name |
| `storage_name` | varchar | Server storage reference |
| `storage_path` | varchar | Path used by file service |
| `mime_type` | varchar | Browser and preview metadata |
| `size_bytes` | integer | Quota and display |
| `kind` | varchar | `avatar`, `document`, `image`, `attachment` |
| `is_public` | boolean | Share behavior |
| `created_at` | datetime | Timeline |

### `messages`

| Column | Type / rule | Purpose |
|---|---|---|
| `id` | primary key | Message identifier |
| `sender_id` | foreign key | Sender |
| `recipient_id` | foreign key | Recipient |
| `subject` | varchar | Message subject |
| `body` | text | Stored message content |
| `thread_id` | nullable foreign key | Reply threading |
| `read_at` | nullable datetime | Notification state |
| `created_at` | datetime | Timeline |

### `comments`

| Column | Type / rule | Purpose |
|---|---|---|
| `id` | primary key | Comment identifier |
| `project_id` | foreign key | Parent project |
| `author_id` | foreign key | Comment author |
| `body` | text | Stored comment content |
| `created_at` | datetime | Timeline |
| `deleted_at` | nullable datetime | Soft deletion for audit |

### `notifications`

Stores project invitations, mentions, file shares, and password-reset notices.

| Column | Type / rule | Purpose |
|---|---|---|
| `id` | primary key | Notification identifier |
| `user_id` | foreign key | Recipient |
| `kind` | varchar | Notification type |
| `payload_json` | text/json | Rendered event data |
| `read_at` | nullable datetime | Read state |
| `created_at` | datetime | Timeline |

### `api_keys`

| Column | Type / rule | Purpose |
|---|---|---|
| `id` | primary key | Key identifier |
| `user_id` | foreign key | Key owner |
| `label` | varchar | User label |
| `key_hash` | varchar | Patched storage representation |
| `display_prefix` | varchar | Safe display prefix |
| `raw_key_for_lab` | nullable text | Vulnerable seed/log fixture only; excluded from patched output |
| `scopes_json` | text/json | API permissions |
| `last_used_at` | nullable datetime | Usage information |
| `created_at` | datetime | Key lifecycle |

### `audit_logs`

| Column | Type / rule | Purpose |
|---|---|---|
| `id` | primary key | Event identifier |
| `actor_id` | nullable foreign key | User or system actor |
| `event_type` | varchar | Event category |
| `method` | varchar | HTTP method |
| `path` | varchar | Request path |
| `parameters_json` | text/json | Deliberately sensitive logging fixture in a lab branch |
| `metadata_json` | text/json | IP, agent, request id |
| `created_at` | datetime | Log timeline |

### `system_settings`

| Column | Type / rule | Purpose |
|---|---|---|
| `setting_key` | primary key | Setting name |
| `setting_value` | text | Admin-managed value |
| `value_type` | varchar | `string`, `json`, or `boolean` |
| `updated_by` | foreign key | Admin audit |
| `updated_at` | datetime | Change timeline |

## B.3 Supporting Tables

The following tables support the later learning modules without changing the core domain:

| Table | Purpose |
|---|---|
| `email_verifications` | Simulated verification tokens and `/dev/mail` output |
| `password_resets` | Reset flow, expiry, reuse, and token-strength exercises |
| `shares` | File and project share links |
| `webhook_configs` | Project webhook and URL-fetch exercise |
| `import_jobs` | URL imports, XML imports, and queue state |
| `point_balances` | Race-condition exercise using local training points |
| `point_redemptions` | Idempotency and duplicate redemption tests |
| `challenge_progress` | Module completion, hint count, and findings |
| `lab_attempts` | Challenge-mode verification attempts |
| `password_history` | Password reset and account policy demonstrations |

## B.4 Seed Relationships

The seed data will be stable and intentionally interconnected:

```text
admin@example.local
  owns the Operations project
  is an administrator
  has a fake API key and audit history

manager@example.local
  manages the Product project
  is a manager in Operations
  has team invitations and notifications

alice@example.local
  owns Project Alpha
  has documents, comments, and messages

bob@example.local
  owns Project Beta
  is a viewer in Project Alpha
  has a separate message thread with Alice

charlie@example.local
  owns Project Gamma
  has a profile, avatar, and untrusted website value
```

Seed passwords are fake local-only values and will be documented by the final README. They must never be reused outside the lab.

## B.5 Important Indexes and Relations

The first schema must index:

* `users.email`, `users.username`
* `projects.owner_id`, `projects.slug`
* `project_members.project_id`, `project_members.user_id`
* `files.project_id`, `files.owner_id`, `files.storage_name`
* `messages.recipient_id`, `messages.thread_id`
* `comments.project_id`
* `audit_logs.actor_id`, `audit_logs.created_at`
* `challenge_progress.user_id`, `challenge_progress.module_id`

Foreign keys should be active in the patched and normal business paths. A vulnerable lab may intentionally omit a business authorization predicate, but it should not rely on broken database referential integrity to be interesting.

---

# C. Route Design

The route names below describe real product workflows. Vulnerability names are deliberately absent from user-facing navigation.

## C.1 Public and Authentication Routes

| Method | Route | Purpose | Auth |
|---|---|---|---|
| `GET` | `/` | Product landing page | Guest |
| `GET, POST` | `/register` | Create account | Guest |
| `GET, POST` | `/login` | Authenticate and create session | Guest |
| `POST` | `/logout` | End current session | User |
| `GET` | `/verify/<token>` | Simulated email verification | Guest |
| `GET, POST` | `/password/forgot` | Request password reset | Guest |
| `GET, POST` | `/password/reset/<token>` | Set a new password | Guest with token |
| `GET` | `/dev/mail` | Local simulated mailbox | Local training/admin policy |

## C.2 Dashboard and Profile Routes

| Method | Route | Purpose | Auth |
|---|---|---|---|
| `GET` | `/dashboard` | Recent projects, notices, and activity | User |
| `GET` | `/profile/<username>` | Public profile view | Guest/User |
| `GET, POST` | `/profile/edit` | Edit profile fields | User |
| `POST` | `/profile/avatar` | Upload avatar | User |
| `POST` | `/profile/email` | Change email and trigger verification | User |
| `POST` | `/profile/password` | Change password | User |
| `GET` | `/settings` | Personal preferences | User |
| `POST` | `/settings` | Save preferences | User |

## C.3 Project and Membership Routes

| Method | Route | Purpose | Auth |
|---|---|---|---|
| `GET` | `/projects` | List visible projects | User |
| `GET, POST` | `/projects/new` | Create project | User |
| `GET` | `/project/<project_id>` | Project dashboard | Member or intended public visibility |
| `GET, POST` | `/project/<project_id>/edit` | Edit project details | Owner/manager |
| `POST` | `/project/<project_id>/delete` | Delete project | Owner/admin |
| `GET` | `/project/<project_id>/members` | Member list | Member/manager |
| `POST` | `/project/<project_id>/members` | Invite member | Owner/manager |
| `POST` | `/project/<project_id>/members/<user_id>/role` | Change member role | Owner/admin |
| `POST` | `/project/<project_id>/members/<user_id>/remove` | Remove member | Owner/manager |
| `GET, POST` | `/project/<project_id>/template-preview` | Preview project report/template | Member |
| `POST` | `/project/<project_id>/import` | Import project metadata from a URL | Member/manager |

## C.4 Files, Messages, and Comments

| Method | Route | Purpose | Auth |
|---|---|---|---|
| `GET` | `/files` | List files visible to current user | User |
| `POST` | `/files/upload` | Upload avatar or project document | User/member |
| `GET` | `/files/<file_id>` | File detail and preview page | Intended owner/member |
| `GET` | `/files/download/<file_id>` | Download file | Intended owner/member |
| `GET` | `/files/preview/<file_id>` | Inline preview | Intended owner/member |
| `POST` | `/files/<file_id>/share` | Create or update share link | Owner/manager |
| `POST` | `/files/<file_id>/delete` | Delete file | Owner/manager |
| `GET` | `/share/<token>` | View a shared resource | Guest with token |
| `GET` | `/messages` | Message inbox | User |
| `GET` | `/messages/<message_id>` | Read one message | Recipient/sender |
| `POST` | `/messages/send` | Send message | User |
| `POST` | `/messages/<message_id>/reply` | Reply in a thread | Participant |
| `GET` | `/project/<project_id>/comments` | List project comments | Member/public project |
| `POST` | `/project/<project_id>/comments` | Add comment | Member |
| `POST` | `/comments/<comment_id>/delete` | Delete comment | Author/project manager/admin |

## C.5 REST API

JSON responses use a common envelope:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "request_id": "local-request-id"
}
```

Error responses will retain useful HTTP status codes instead of returning `200` for every failure.

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/login` | JSON login |
| `POST` | `/api/logout` | JSON logout |
| `GET` | `/api/me` | Current user and effective role |
| `GET` | `/api/users/search` | Member search and invitations |
| `GET` | `/api/users/availability` | Username/email availability check |
| `GET` | `/api/projects` | List projects |
| `POST` | `/api/projects` | Create project |
| `GET` | `/api/projects/<project_id>` | Project detail |
| `PATCH` | `/api/projects/<project_id>` | Update project |
| `DELETE` | `/api/projects/<project_id>` | Delete project |
| `GET` | `/api/projects/<project_id>/members` | Members |
| `POST` | `/api/projects/<project_id>/members` | Add member |
| `PATCH` | `/api/projects/<project_id>/members/<user_id>` | Change membership |
| `GET` | `/api/files` | File list |
| `POST` | `/api/files` | Multipart upload |
| `GET` | `/api/files/<file_id>` | File metadata |
| `GET` | `/api/files/<file_id>/download` | File bytes |
| `DELETE` | `/api/files/<file_id>` | Delete file |
| `GET` | `/api/messages` | Message list |
| `POST` | `/api/messages` | Send message |
| `GET` | `/api/messages/<message_id>` | Read message |
| `POST` | `/api/import/url` | Import/preview a remote resource |
| `POST` | `/api/import/xml` | Import project feed |
| `POST` | `/api/import/task` | Queue an import task |
| `GET` | `/api/notifications` | Notifications |
| `GET` | `/api/settings` | Preferences |
| `PATCH` | `/api/settings` | Preferences update |
| `POST` | `/api/rewards/redeem` | Spend training points |
| `GET` | `/api/docs` | Local API documentation |
| `GET` | `/api/admin/users` | Admin user list |
| `PATCH` | `/api/admin/users/<user_id>` | Admin user update |
| `GET` | `/api/admin/logs` | Admin log viewer |
| `GET` | `/api/admin/settings` | System settings |
| `PATCH` | `/api/admin/settings/<key>` | Change system setting |

## C.6 Internal Service Routes

These routes are not published by Nginx and have no host port.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/internal/health` | Health check |
| `GET` | `/internal/status` | Build, service, and dependency status |
| `GET` | `/internal/config` | Fake service configuration and lab fixture |
| `GET` | `/internal/users` | Internal service-account fixture |
| `POST` | `/internal/jobs/preview` | Internal report preview worker |

The internal service contains only fake secrets and fake user data. The design never requires access to a host metadata service or an actual cloud credential endpoint.

## C.7 Developer and Training Routes

| Method | Route | Purpose | Availability |
|---|---|---|---|
| `GET` | `/training` | Lab dashboard and progress | Training mode |
| `GET` | `/training/modules/<module_id>` | Module instructions and hints | Training mode |
| `POST` | `/training/modules/<module_id>/verify` | Verify a learner objective | Training mode |
| `GET` | `/audit/source` | Source bundle index | Audit mode |
| `GET` | `/audit/schema` | Schema and relationship view | Audit mode |
| `GET` | `/debug/request` | Request lifecycle details | Learning mode/local policy |
| `GET` | `/debug/config` | Safe or intentionally leaked configuration fixture | Local admin/lab policy |

These routes are guarded by configuration and role checks. They are not linked from the ordinary product navigation when training mode is disabled.

---

# D. Permission Model

## D.1 Roles

| Principal | Default capability |
|---|---|
| Guest | Landing page, registration, login, public profiles, valid share links |
| User | Own profile, own messages, own projects, project participation, own files |
| Manager | Team resource management for projects where the user has `manager` membership |
| Admin | Global user, project, settings, log, and training administration |

Role membership and object membership are separate. A global `manager` role does not automatically make a user an owner of every project. This distinction creates realistic authorization paths for both correct checks and intentionally flawed checks.

## D.2 Policy Evaluation

The patched application will use a small policy layer with these inputs:

```text
principal
action
resource type
resource id
project membership
global role
request context
```

Examples:

```text
can_view_project(user, project)
can_edit_project(user, project)
can_manage_member(user, project, target_user)
can_read_file(user, file)
can_read_message(user, message)
can_change_system_setting(user)
```

The UI may hide unavailable actions, but the API and HTML POST endpoints must make the final decision server-side.

## D.3 Permission Matrix

| Action | Guest | User | Manager member | Admin |
|---|---:|---:|---:|---:|
| Register/login | Yes | Yes | Yes | Yes |
| Create project | No | Yes | Yes | Yes |
| View own project | No | Owner/member | Yes | Yes |
| Edit owned project | No | Owner | Yes | Yes |
| Invite project member | No | Owner | Yes | Yes |
| Change member role | No | Owner only | Project policy | Yes |
| Read own message | No | Yes | Yes | Yes |
| Read another user's message | No | No | No by default | Support-only workflow |
| Upload project file | No | Member | Yes | Yes |
| Delete project file | No | Owner/uploader policy | Yes | Yes |
| View admin logs | No | No | No | Yes |
| Change system setting | No | No | No | Yes |
| View training dashboard | Configured | Configured | Configured | Yes |

## D.4 Deliberate Authorization Faults

The vulnerable variant will introduce faults in separate business paths rather than making all endpoints admin-free:

* Project detail API trusts a numeric `project_id` without checking membership in one response branch.
* File download checks that a file exists but not that the requester can read its parent project.
* Message detail uses sender/recipient filtering in the HTML route but only `id` in one JSON repository method.
* Member role update trusts a client-supplied `role` under a manager workflow, allowing a constrained escalation.
* Admin API checks a UI-provided role header in one lab branch instead of the server session.

Each fault will have a single source location, a verification test, and a final patched implementation. The rest of the permission layer remains correct so learners must understand the difference.

## D.5 Authentication Lifecycle

The intended lifecycle is:

```text
register -> pending account -> simulated verification -> active account
login -> session creation and rotation -> authenticated request
logout -> server-side invalidation and cookie expiry
password reset -> one-time expiring token -> session invalidation
```

The vulnerable variant will distribute authentication issues across separate flows:

* Session identifier is not rotated on one login path, demonstrating fixation.
* Password-reset token generation is predictable or reusable in an early lab.
* Remember-me session lifetime is longer than the normal session and is logged for analysis.
* Login throttling uses a Redis key derived from a client-controlled header in one branch.

The patched variant rotates identifiers, hashes reset tokens, invalidates prior sessions after password change, and applies server-derived rate-limit keys.

---

# E. Docker and Network Design

## E.1 Compose Services

The first Compose file will define:

```text
nginx
web
mysql
redis
internal-api
```

Optional test and audit profiles may add a one-shot test runner, but normal startup must not require a host-installed Python, MySQL, or Redis.

## E.2 Networks

```text
host_ingress (Docker internal: false; Nginx only)
  host loopback -> nginx

proxy_private (Docker internal: true)
  nginx <-> web

app_private (Docker internal: true)
  web <-> mysql
  web <-> redis
  web <-> internal-api
  internal-api <-> mysql (only if needed by its fixture)
```

`proxy_private` and `app_private` are declared `internal: true`. They provide the default network-level egress control for web and the data services. Docker does not expose a published port from an `internal` network, so Nginx also joins the dedicated non-internal `host_ingress` network; Nginx is the only service on that network and the only service with a host port. `app_private` has no host-published ports. MySQL, Redis, and internal-api must not publish `3306`, `6379`, or `8081` to the host.

The web container needs only `proxy_private` and `app_private`, both internal. Nginx needs `host_ingress` and `proxy_private`. Internal data services need only `app_private`. This makes the browser-to-web and web-to-internal-service boundary observable in Docker inspection and Burp traffic without giving web a public egress route.

## E.3 Host Binding and Volumes

The initial host binding will be:

```text
127.0.0.1:8080 -> nginx:80
```

Named volumes:

```text
websec_lab_mysql_data
websec_lab_redis_data
websec_lab_uploads
websec_lab_mail
```

No host source directory, Docker socket, SSH key, home directory, or arbitrary host path will be mounted into a vulnerable container. The web and internal-api images will run as non-root users where compatible with the exercise.

## E.4 Network Safety Controls

The lab must be safe by default:

* Docker `internal: true` networks provide the primary default-deny egress boundary for web and internal-api; this must be verified from inside those containers.
* Nginx's non-internal `host_ingress` attachment exists only to make the loopback port publication possible; Nginx does not perform application URL fetching in Phase 2.1.
* `LAB_EGRESS=deny` is a secondary application-level guard for experiment behavior and is not treated as the network boundary.
* SSRF fixtures target `internal-api` first and never depend on a public website.
* Containers do not receive cloud metadata credentials.
* No container gets `/var/run/docker.sock`.
* The host port binds to loopback, not `0.0.0.0`.
* The command-execution lab runs inside the container and uses fake data only.
* Reset and seed operations are deterministic and documented.

The vulnerable SSRF path can still demonstrate the difference between a browser that cannot resolve `internal-api` and a server that can. Any optional external URL test must be explicitly enabled by the learner and will not be part of the default setup.

## E.5 Reverse Proxy Responsibilities

Nginx will route:

```text
/static/    -> static assets
/api/       -> web JSON routes
/           -> web HTML routes
```

Nginx must not serve `/uploads/` or any other filesystem-backed resource directly. File responses must first pass through Flask authorization and then be streamed by the application, or use an Nginx `internal` location reached only through an application-generated internal redirect. A separate reverse-proxy lab will examine trusted `X-Forwarded-*` headers, URI normalization, upload path handling, and discrepancies between Nginx and Flask route matching. The normal patched proxy configuration will normalize paths and avoid trusting client-supplied internal identity headers.

---

# F. Vulnerability Map

All identifiers below are local training identifiers. They are not CVE records and must never be presented as real public vulnerabilities.

## F.1 Foundational Labs

| ID | Business surface | Source to sink | Intended issue | Level | Final fix |
|---|---|---|---|---:|---|
| `LAB-SQLI-001` | Project search | `q` query -> search service -> concatenated SQL -> MySQL | Classic SQL injection with project/user data exposure | 1 | Parameterized query and typed filters |
| `LAB-SQLI-002` | Username availability | `username` query -> availability repository -> boolean SQL condition -> response difference | Boolean blind SQL injection | 1 | Parameterized query and uniform response |
| `LAB-XSS-001` | Profile website and search results | request parameter -> HTML template -> response body | Reflected XSS | 1 | Contextual output encoding and safe URL validation |
| `LAB-XSS-002` | Bio, project description, comments, messages | request body -> database -> template rendering | Stored XSS / HTML injection | 1 | Contextual escaping, safe text rendering, optional allowlist |
| `LAB-XSS-003` | Notification redirect and settings merge | JSON/API value -> browser JavaScript -> unsafe DOM sink | DOM XSS | 1 | `textContent`, URL policy, safe object handling |
| `LAB-CSRF-001` | Profile email change | cross-site form -> state-changing POST -> account data | CSRF on high-value action | 2 | CSRF token, SameSite policy, origin checks |
| `LAB-IDOR-001` | Project detail and member list | path `project_id` -> repository lookup -> response without membership predicate | Project IDOR | 2 | Central object authorization |
| `LAB-IDOR-002` | File download and preview | path `file_id` -> file lookup -> bytes without project authorization | File IDOR | 2 | Authorize file and parent project before read |
| `LAB-IDOR-003` | Message detail | path `message_id` -> message lookup -> body response | Message object access flaw | 2 | Sender/recipient policy in every representation |

## F.2 Intermediate Labs

| ID | Business surface | Source to sink | Intended issue | Level | Final fix |
|---|---|---|---|---:|---|
| `LAB-AUTH-001` | Member role update | client role -> membership service -> role assignment | Privilege escalation through weak authorization | 2 | Server-derived policy and role transition rules |
| `LAB-FILE-001` | File upload and preview | filename/MIME/content -> storage -> inline browser response | Unrestricted upload and active content handling | 2 | Content inspection, generated names, safe disposition, isolated storage |
| `LAB-FILE-002` | File download | stored relative path -> path join -> filesystem read | Path traversal / arbitrary file read in a real download flow | 2 | Resolve-and-contain check and opaque storage ids |
| `LAB-AUTH-002` | Password reset | email/time/user data -> reset token -> reset endpoint | Weak, reusable, or enumerable reset token | 2 | Random hashed one-time token with expiry and invalidation |
| `LAB-AUTH-003` | Login and remember-me | pre-auth session -> login -> authenticated session | Session fixation or incomplete session rotation | 2 | Rotate session id and invalidate prior authentication state |
| `LAB-AUTH-004` | API admin route | role header or API key metadata -> middleware -> admin handler | Authentication/authorization boundary bypass | 2 | Derive identity from verified session/key and enforce scope |

## F.3 Advanced Labs

| ID | Business surface | Source to sink | Intended issue | Level | Final fix |
|---|---|---|---|---:|---|
| `LAB-SSRF-001` | Project URL import/link preview | JSON `url` -> import service -> HTTP client -> internal-api | SSRF with internal service discovery | 3 | Scheme/host allowlist, DNS/IP validation, egress policy, timeouts |
| `LAB-CMD-001` | Image thumbnail/diagnostic preview | filename/options -> shell command builder -> subprocess | Command injection | 3 | No shell, argument array, fixed executable, validation and sandbox |
| `LAB-SSTI-001` | Report/template preview | project template text -> Jinja environment -> render | SSTI | 3 | Treat input as data; fixed templates and sandboxed variables |
| `LAB-XXE-001` | XML project feed import | uploaded XML -> XML parser -> entity resolution/file access | XXE | 3 | Defused parser, external entities disabled, size limits |
| `LAB-DESER-001` | Queued import task | base64 task blob -> Redis queue -> deserialization | Insecure deserialization | 4 | JSON schema, signed messages, no pickle/eval |
| `LAB-RACE-001` | Training points redemption | balance read -> check -> decrement -> reward insert | Race condition / duplicate redemption | 3 | Transaction, row lock, unique idempotency key |
| `LAB-PROXY-001` | Proxy-aware rate limit and admin path | client headers/normalized path -> proxy/middleware -> privileged branch | Reverse-proxy trust and path discrepancy | 4 | Canonical path, trusted proxy config, server-derived identity |
| `LAB-CLIENT-001` | Frontend preference merge | JSON preferences -> recursive merge -> inherited object lookup | Prototype pollution-style client-side object mutation | 3 | Own-property checks, null-prototype objects, schema validation |

## F.4 Disclosure and Supporting Issues

| ID | Business surface | Intended issue | Chain role |
|---|---|---|---|
| `LAB-DISC-001` | Debug response and error page | Stack traces, framework versions, route/config details | Discovery entry |
| `LAB-DISC-002` | API docs and backup fixture | Undocumented endpoints, fake API keys, old settings | Discovery and token exposure |
| `LAB-DISC-003` | Admin log viewer | Sensitive URL, token, parameter, or message data in logs | Disclosure and stored-rendering path |
| `LAB-DISC-004` | Redis temporary data | Predictable key or unsafe trust in cached task state | Deserialization/session support |
| `LAB-SSRF-002` | Webhook configuration | Unvalidated callback URL and weak secret handling | SSRF and credential disclosure support |

The design does not require every support issue to be independently exploitable. Some exist to make source-to-sink and chain analysis realistic.

## F.5 Source, Propagation, and Sink Requirements

Every lab record must document a trace such as:

```text
Source: request.args["q"]
  -> route: project_search()
  -> service: search_projects()
  -> repository: find_projects()
  -> sink: raw SQL execution
```

or:

```text
Source: request.json["url"]
  -> validation helper with incomplete checks
  -> import_service.fetch_preview()
  -> requests.get()
  -> internal-api response returned to the caller
```

or:

```text
Source: message body
  -> message service
  -> messages table
  -> template/Javascript rendering
  -> browser HTML/DOM sink
```

The lab specification for each vulnerability will include the expected source, transformations, sink, impact, vulnerable request, patch diff, and a verification test.

## F.6 Patch Progression

Selected labs will have three stages:

```text
vulnerable
  -> patch-v1: plausible but incomplete mitigation
  -> final: complete boundary validation and regression test
```

Examples:

* SQL injection: blacklist quote filtering -> fragile escaping -> parameterized query.
* SSRF: block a few private strings -> hostname-only check -> DNS/IP-aware allowlist and egress restriction.
* XSS: strip selected tags -> HTML escaping in one template -> context-correct output encoding everywhere.
* File upload: extension check -> MIME check -> content handling, generated names, storage isolation, authorization.

The intermediate patch must be labeled as incomplete and must have a test demonstrating its bypass in the instructor material. The final patch must pass the security regression suite.

---

# G. Vulnerability Chain Design

## G.1 Chain A: Discovery to Administrative Access

```text
debug/error disclosure
  -> discover API documentation or route behavior
  -> project/file IDOR exposes a manager-owned object
  -> weak member role update changes role or scope
  -> admin endpoint trusts the resulting privilege state
  -> administrative data becomes available
```

The chain uses separate requests and users. No single request is an automatic admin bypass. Verification records the current identity, object ids, role transition, and final authorization decision.

## G.2 Chain B: Stored XSS to Account Modification

```text
comment or message content
  -> stored in the database
  -> rendered in a recipient's project/message view
  -> unsafe browser execution
  -> state-changing email/profile request
  -> account identifier or recovery destination changes
```

The local lab uses fake accounts and a simulated mailbox. The patched version combines contextual escaping, CSRF protection, and re-authentication for sensitive account changes.

## G.3 Chain C: SSRF to Internal Credential Disclosure

```text
project link preview
  -> server-side URL fetch
  -> internal-api DNS name
  -> /internal/config or /internal/users
  -> fake service token/config data
  -> admin/API workflow discovery
```

The internal service is reachable only from the private Docker network. Default egress policy prevents the chain from requiring a real public target.

## G.4 Chain D: Upload to Command Execution

```text
project image/document upload
  -> weak file type decision
  -> thumbnail or conversion job
  -> unsafe command construction
  -> web-container process execution
  -> application-local data or service access
```

The worker runs with fake seed data, no Docker socket, no host mounts, and no production secrets. The patched version avoids shell invocation and treats all uploaded content as untrusted.

## G.5 Chain E: SQL Injection to Token and Internal API Access

```text
project search or availability check
  -> injectable repository query
  -> sensitive rows such as api_keys/audit data
  -> leaked fake API token
  -> internal/admin API request
```

The chain demonstrates why a query bug can become an authorization and service-boundary issue. Seed tokens are synthetic and scoped to the lab.

## G.6 Chain Verification Rules

Each chain requires:

* A precondition list and required seed accounts.
* A request-by-request HTTP transcript.
* A source-to-sink trace.
* A success oracle that does not depend only on a status code.
* A patched failure case.
* A reset instruction to return to a known state.

---

# H. Learning Progression

## H.1 Difficulty Levels

| Level | Learning goals | Planned modules |
|---:|---|---|
| 1 Beginner | HTTP, forms, cookies, sessions, basic data flow | Login/session inspection, profile rendering, project search, classic SQLi, reflected/stored XSS |
| 2 Basic | Object authorization and state changes | Project/file/message IDOR, CSRF, upload, download path handling, API authorization |
| 3 Intermediate | Server-side integrations and processing | SSRF, SSTI, command injection, XXE, race condition |
| 4 Advanced | Multi-step analysis and trust boundaries | Deserialization, auth bypass variants, role escalation, proxy behavior, chained XSS/CSRF/SSRF |
| 5 Research | White-box audit and remediation | Source audit, patch-v1 bypass, final patch, local LAB report, CVE-style write-up |

## H.2 Learning Mode

Learning Mode exposes progressive assistance without showing the final payload immediately:

```text
Hint 1: What is the source of this value?
Hint 2: Which route and service receive it?
Hint 3: What transformation occurs?
Hint 4: What is the sink or authorization decision?
Hint 5: What evidence should a verification request produce?
```

The module page can show:

* Concept and prerequisite knowledge.
* Relevant endpoint and normal workflow.
* Source, propagation, and sink after hints are unlocked.
* Safe local test data.
* Patch explanation after completion.
* Security regression result.

Hints are stored in `challenge_progress` and can be reset with the lab reset operation.

## H.3 Challenge Mode

Challenge Mode shows only:

* Objective.
* Available account identities.
* Product navigation.
* Scope and reset instructions.
* A success/failure verifier.

It does not show vulnerability names, source locations, payloads, answer requests, or patch details. It should still expose ordinary HTTP behavior so Burp Proxy, Repeater, Intruder, Comparer, and Logger remain useful.

## H.4 Audit Mode

Audit Mode provides a source bundle close to the runtime structure:

```text
routes/
services/
repositories/
models/
middleware/
templates/
static/
config/
database schema and seed data
```

The learner begins with a feature or endpoint and traces the data to the sink. The bundle can be downloaded or viewed locally, but it must not collapse all vulnerable code into a special training file.

## H.5 Progress Metrics

The training dashboard records:

* Modules started and completed.
* Difficulty level.
* Hints used.
* Verification attempts.
* Vulnerability chains completed.
* Patch regression tests run.
* Source-audit findings submitted.

Progress is educational metadata only. It must not grant product permissions.

---

# I. Threat Model

## I.1 Assets

The local lab contains intentionally fake but meaningful assets:

* User identities, passwords, sessions, and reset tokens.
* Project metadata and membership relationships.
* Uploaded files and rendered content.
* Private messages and comments.
* Synthetic API keys and internal service configuration.
* Audit logs and system settings.
* Training progress and patch artifacts.

The main learning objective is to understand confidentiality, integrity, authentication, authorization, and server-side request boundaries, not to protect real-world secrets.

## I.2 Actors

| Actor | Assumption |
|---|---|
| Guest | Can send unauthenticated HTTP requests to the local app |
| Registered user | Controls one or more fake accounts and can use Burp |
| Manager | Has limited project management privileges |
| Admin | Has global product privileges in the seed data |
| Malicious content author | Can submit project, message, comment, profile, or file content |
| Internal service | Trusted by network placement but contains only synthetic data |

The learner may act as any local actor. There is no real external attacker or production operator in scope.

## I.3 Trust Boundaries

```text
Browser/Burp -> Nginx
Nginx -> Flask web
Flask request -> authenticated principal
Route -> service/repository
Web -> MySQL/Redis
Web -> internal-api
Uploaded content -> filesystem/browser/parser/worker
Training source bundle -> learner
```

Every boundary should have a corresponding log, test, or design note. The vulnerable variant intentionally weakens selected boundaries; the patched variant restores explicit validation and authorization.

## I.4 Threats Covered

* Unauthenticated access to protected objects.
* Horizontal access to another user's objects.
* Vertical privilege escalation.
* Injection into database, template, browser, shell, XML, and object parser boundaries.
* Cross-site state changes and stored browser execution.
* Server-side access to private network resources.
* File path confusion and active content handling.
* Session lifecycle and password recovery weaknesses.
* Concurrency and idempotency errors.
* Proxy/header trust mistakes.

## I.5 Out of Scope

The project will not target:

* Real credentials, real customer data, or real cloud accounts.
* Host escape, Docker socket access, kernel exploitation, or persistence.
* Exploiting arbitrary third-party websites as part of the default lab.
* Scanning networks outside the Compose private network.
* Production-grade availability or compliance guarantees.
* A claim that local `LAB-*` identifiers are CVEs.

## I.6 Safety and Reset Controls

The final setup and README must explain:

* Bind to loopback only.
* Run in a disposable local environment.
* Use fake seed credentials only.
* Keep default egress denied.
* Never mount host secrets or Docker socket.
* Reset named volumes before switching lab variants if state is incompatible.
* Stop the stack after a study session when it is not needed.

---

# J. Development Roadmap

## Phase 1: Design Baseline

**Status:** this document

Deliver:

* Architecture and request lifecycle.
* Database entities and seed relationships.
* HTML/API/internal route inventory.
* Permission policy and deliberate fault locations.
* Docker networks and safety controls.
* Vulnerability map and five chains.
* Learning modes and difficulty progression.
* Threat model and acceptance criteria.

Gate: no implementation begins until the route names, seed relationships, and initial three labs are stable.

## Phase 2: Minimal Runnable Application (parent scope)

Phase 2 is split into infrastructure and application milestones. The current implementation boundary is Phase 2.1 only; no business workflow or intentional security weakness is included before its gate passes.

### Phase 2.1: Infrastructure Baseline (current)

Implement only:

* Docker Compose with Nginx, web, MySQL, Redis, and internal-api.
* Loopback-only Nginx entry point and Docker-internal networks.
* Basic Flask landing and health responses.
* MySQL, Redis, and internal-api connectivity checks without secret disclosure.
* Health checks, deterministic bootstrap, and a reset script.

Tests:

* Compose services start and become healthy.
* Nginx -> Flask, Flask -> MySQL, Flask -> Redis, and Flask -> internal-api.
* Host cannot directly connect to private services.
* Default container egress is blocked by Docker network topology.
* Reset reproduces the same clean bootstrap state.

Gate: `docker compose up -d` starts the stack, `http://127.0.0.1:8080` and `/health` respond, private services have no host ports, and reset verification passes.

### Phase 2.2: Core Application (future)

Implement only after the Phase 2.1 gate:

* Compose startup with Nginx, web, MySQL, and Redis.
* Schema migration and deterministic seed.
* Registration, simulated verification, login, logout, and session display.
* Dashboard and project create/list/detail/edit/delete.
* Basic HTML and API parity.
* Health checks and a reset script.

Initial tests:

* Application health.
* Registration/login/logout.
* Session expiry and role loading.
* Project ownership and basic CRUD.
* MySQL repository integration tests; SQLite repository unit tests only.

Gate: `docker compose up -d` starts the stack, `http://127.0.0.1:8080` loads, and seeded credentials work.

## Phase 3: Core Business Modules

Implement:

* Files, upload metadata, download, preview, and sharing.
* Messages, threads, notifications, and comments.
* Member invitations and role changes.
* Admin user/settings/log views.
* Internal API service and private network routing.
* Redis-backed sessions, cache, queue, and temporary data.

Tests:

* Business authorization matrix.
* Multipart upload and file lifecycle.
* Message and comment ownership.
* API/HTML parity.
* Internal service not reachable from the host.

Gate: ordinary users can complete the primary SaaS workflows without lab-specific instructions.

## Phase 4: First Vulnerability Set

Add no more than three vulnerable paths at a time. The recommended order is:

1. Project search SQLi, profile reflected/stored rendering, and project IDOR.
2. File download authorization, CSRF on email change, and upload/preview handling.
3. SSRF link preview, internal API disclosure, and one chain verifier.

For each set, add vulnerable behavior, patched behavior, HTTP PoC, source-to-sink note, security test, and patch diff before moving on.

Gate: each added issue has a reliable success oracle and a patched negative test.

## Phase 5: Learning, Challenge, and Audit Modes

Implement:

* Lab registry and module metadata.
* Progressive hints and progress persistence.
* Challenge objectives and verifiers.
* Source/config/schema audit bundle.
* Instructor notes and local LAB report format.

Gate: the same feature remains usable in normal mode, challenge mode, and audit mode without exposing vulnerability labels in ordinary navigation.

## Phase 6: Advanced Labs and Patch Research

Add in separate increments:

* Blind SQLi and patch-v1 bypass.
* SSTI, XXE, command injection, and race condition.
* Deserialization and Redis task boundary.
* Proxy/header behavior and frontend object merge issue.
* Full five-chain documentation.

Gate: advanced labs are container-confined, resettable, and covered by tests that cannot reach a real external target by default.

## Phase 7: Packaging and Release Review

Deliver:

* Complete README and API documentation.
* Architecture diagram and threat model.
* Seed account table.
* Vulnerability index and chain guide.
* HTTP request PoCs.
* Vulnerable/final patch trees and diffs.
* Unit, integration, and security regression tests.
* Fresh-machine Compose verification.

Gate: a clean reset and fresh startup reproduce the documented state with no manual database edits.

---

# K. Planned Project Layout

The implementation will remain inside this project directory:

```text
websec-lab/
├── docker-compose.yml
├── README.md
├── Makefile
├── PROJECT_DESIGN.md
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── requirements.txt
│   ├── routes/
│   ├── services/
│   ├── repositories/
│   ├── models/
│   ├── middleware/
│   ├── utils/
│   ├── templates/
│   └── static/
├── frontend/
│   ├── pages/
│   └── static/
├── database/
│   ├── migrations/
│   ├── schema.sql
│   └── seed.sql
├── services/
│   └── internal-api/
├── labs/
│   ├── beginner/
│   ├── intermediate/
│   ├── advanced/
│   └── research/
├── exploits/
│   ├── http/
│   └── verification/
├── patches/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── security/
├── docs/
│   ├── architecture/
│   ├── labs/
│   └── instructor/
└── scripts/
```

The `labs/` directory will contain descriptions and fixtures, not all vulnerable runtime logic. Runtime behavior must remain distributed across the same routes, services, repositories, templates, and frontend modules used by the product.

---

# L. Test and Verification Contract

Every feature and lab is complete only when it has the following artifacts:

```text
normal workflow test
vulnerable behavior test, where applicable
patched negative test
HTTP request example
source -> propagation -> sink trace
impact statement
reset requirement
patch explanation
```

The security suite will eventually include, at minimum:

```text
tests/security/test_sqli.py
tests/security/test_xss.py
tests/security/test_csrf.py
tests/security/test_idor.py
tests/security/test_uploads.py
tests/security/test_path_handling.py
tests/security/test_ssrf.py
tests/security/test_authentication.py
tests/security/test_authorization.py
tests/security/test_race_condition.py
```

Tests must be safe to run against only the local Compose services. They must not send traffic to arbitrary public destinations.

---

# M. Acceptance Criteria for the Design Phase

This design phase is considered stable when:

* The product can be described as a normal SaaS workflow without naming a vulnerability.
* Core entities and their relationships support the five chains.
* HTML, API, and internal routes have a clear responsibility.
* Permissions distinguish global roles from project membership.
* Docker network boundaries explain why the server can reach internal-api while the browser cannot.
* Every requested vulnerability category has a planned business surface or an explicit later-phase decision.
* Vulnerabilities are mapped to source, propagation, sink, impact, patch, and test artifacts.
* Learning, challenge, and audit modes do not change the core product into separate fake applications.
* The threat model prevents accidental use against real systems.
* The roadmap limits each vulnerability increment to two or three issues before verification.

The next approved implementation step is Phase 2.1: create and verify the infrastructure baseline before adding any business workflow or intentional vulnerability.

---

# N. Deferred Decisions

These choices are intentionally deferred until implementation exposes a concrete need:

* Exact Flask extension set, beyond Flask, SQLAlchemy-compatible database access, Redis client, and test tooling.
* Whether the default local port remains `8080` or is made configurable in the first Compose file.
* Exact visual theme and typography after the first usable dashboard exists.
* Whether SQLite support uses the same migration path or a separate test bootstrap.
* The final number of advanced labs included in the first public learning release.

None of these deferred decisions should change the route ownership, data model, network isolation, or initial vulnerability map without updating this document first.
