# Open Questions

**Phase 2.2a:** complete

**Open Questions:** resolved for this phase.

Phase 2.2a closeout decisions:

* `websec_lab_public_edge` was inspected and had `Containers: {}`. It was removed. No other Docker network was deleted or modified.
* Docker buildx was not installed. Compose fallback builder works, and the project build/tests do not require a buildx plugin.
* The external host listener on `127.0.0.1:3306` was not stopped, restarted, or modified. WebSec Lab MySQL has no `ports` mapping.
* The Phase 2.2a baseline commits were verified and pushed. The current schema idempotency fix is local pending its closeout push.
* Implementation commit: `5f6e62e Fix Phase 2.2a schema idempotency and handoff metadata`.
* Current functional verification HEAD: `5f6e62e`.
* `origin/main` remains synchronized through `634c749` until the current closeout commit is pushed.
* Phase 2.2b is deferred and must be separately approved.

Verification:

* `12 passed`
* `schema.sql` executed twice consecutively without errors.
* determinism verification passed.
* Phase 2.1 regression passed.

There are no unresolved Phase 2.2a operational questions.
