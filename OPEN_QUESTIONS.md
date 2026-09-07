# Open Questions

**Phase 2.2a:** complete

**Phase 2.2b:** complete locally after final verification.

**Open Questions:** resolved for this phase.

Phase 2.2a closeout decisions:

* `websec_lab_public_edge` was inspected and had `Containers: {}`. It was removed. No other Docker network was deleted or modified.
* Docker buildx was not installed. Compose fallback builder works, and the project build/tests do not require a buildx plugin.
* The external host listener on `127.0.0.1:3306` was not stopped, restarted, or modified. WebSec Lab MySQL has no `ports` mapping.
* The Phase 2.2a baseline and schema idempotency fix were verified and pushed.
* Phase 2.2b implementation commit: `31fc67e Implement Phase 2.2b authentication foundation`.
* Current functional verification HEAD: `31fc67e`.
* Phase 2.2b closeout fix commit: `c3b10f0 Fix Phase 2.2b mailbox access and registration consistency`.
* Current functional verification HEAD: `c3b10f0`.
* The closeout fix is verified and pushed; local `main` and `origin/main` are synchronized through `f84f033`.
* Phase 2.2c is deferred and must be separately approved.

Verification:

* Phase 2.2a baseline and Phase 2.2b authentication tests pass.
* Full unit and integration suite: `34 passed`.
* `/dev/mail` permission tests and registration compensation tests pass.
* `schema.sql` executed twice consecutively without errors.
* determinism verification passed.
* Phase 2.1 regression passed.

There are no unresolved Phase 2.2a or Phase 2.2b operational questions.
