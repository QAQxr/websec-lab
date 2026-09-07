# Authentication Foundation

## Phase Status

Phase 2.2b implements the normal AcmeCloud authentication foundation. It does not include Project CRUD, REST business APIs, or any intentional vulnerability.

## Request Path

```text
Browser
  -> Nginx
  -> Flask route
  -> AuthService
  -> UserRepository / VerificationRepository / SessionService
  -> MySQL and Redis
  -> redirect and HttpOnly cookie
```

Routes parse form input and render responses. `AuthService` owns the registration, verification, login, and logout workflows. Repositories perform persistence only.

## Passwords

New registration passwords use Werkzeug's maintained `scrypt` implementation with a unique salt. MySQL stores only the generated password hash. The password service also verifies the legacy PBKDF2 fixture representation used by the Phase 2.2a seed without reimplementing the cryptographic primitive.

Password values are not written to application responses, logs, Redis, or the database.

## Registration and Verification

```text
POST /register
  -> validate username, email, password, confirmation
  -> create pending user
  -> generate random verification token
  -> store SHA-256 token representation in email_verifications
  -> store the raw local link only in the Redis mailbox fixture

GET /dev/mail
  -> local/test-only mailbox view

GET /verify/<token>
  -> hash presented token
  -> lock and consume one unused, unexpired verification row
  -> activate user and set email_verified_at
```

The verification token is random, expires after the configured TTL, and can be consumed once. Normal product pages and error responses do not expose it.

## Sessions

```text
anonymous request
  -> optional old opaque cookie
  -> successful login invalidates old key
  -> new random session identifier
  -> Redis session state with TTL
  -> MySQL sessions row for persistence and audit
  -> authenticated request
  -> logout deletes Redis state and MySQL row
```

Session identifiers are generated with `secrets.token_urlsafe(32)`. They do not encode a user id or timestamp. Redis is the active session store; the MySQL row records the session lifecycle fields and is checked during authentication. Missing or expired Redis state invalidates the corresponding MySQL row.

Normal sessions use a one-hour TTL. Remember-me sessions use a thirty-day TTL. `last_seen_at` is updated on authenticated requests.

## Cookies

The `session` cookie contains only the opaque session identifier. Defaults are:

```text
HttpOnly=true
SameSite=Lax
Secure=false for local HTTP
Path=/
Max-Age=session or remember-me TTL
```

`SESSION_COOKIE_SECURE=true` can be set for HTTPS-like deployments. Logout sends an expired cookie and invalidates server-side state; deleting the browser cookie alone is not the invalidation mechanism.

## Local Mailbox

`/dev/mail` is enabled only when `APP_ENV` is `local` or `test`. It does not send mail or connect to SMTP. Its purpose is to expose the local verification link during training. It is not linked as a normal product workflow.

## Current Scope

Implemented routes:

* `GET, POST /register`
* `GET /verify/<token>`
* `GET /dev/mail` in local/test mode
* `GET, POST /login`
* `POST /logout`
* `GET /profile`
* `GET /dashboard`

Project CRUD, REST APIs, password reset, and all intentional vulnerability variants remain deferred to later phases.
