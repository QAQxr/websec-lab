# Open Questions

**Phase 2.2a:** complete

**Phase 2.2b:** complete after final verification.

**Phase 2.2c HTML foundation:** complete after final verification.

**Phase 2.2c authorization finalization:** complete after final verification.

**Phase 2.2c REST project parity:** complete after final verification.

**Phase 2.2d membership mutation:** complete locally after final verification.

**Open Questions:** resolved for this phase.

Phase 2.2a closeout decisions:

* `websec_lab_public_edge` was inspected and had `Containers: {}`. It was removed. No other Docker network was deleted or modified.
* Docker buildx was not installed. Compose fallback builder works, and the project build/tests do not require a buildx plugin.
* The external host listener on `127.0.0.1:3306` was not stopped, restarted, or modified. WebSec Lab MySQL has no `ports` mapping.
* The Phase 2.2a baseline and schema idempotency fix were verified and pushed.
* Phase 2.2b implementation commit: `31fc67e Implement Phase 2.2b authentication foundation`.
* Phase 2.2b closeout fix commit: `c3b10f0 Fix Phase 2.2b mailbox access and registration consistency`.
* Phase 2.2c REST parity commit: `ba008a4 Implement Phase 2.2c REST project parity`.
* Current local `HEAD` and `origin/main` remain synchronized at `ba008a4`; Phase 2.2d changes are intentionally uncommitted and unpushed.
* Phase 2.2c HTML and REST CRUD plus Phase 2.2d membership mutation are implemented locally; ownership transfer and share-token access remain deferred.
* `ProjectPolicy.access_for()` is the single authorization source; repository scopes are explicit and team visibility is read-only for non-members.
* Global admin capability is separate from project membership; ownership uses `projects.owner_id` and mismatch cases fail closed.
* REST routes reuse `ProjectService`, `ProjectPolicy`, and repository scopes; API serialization excludes internal project fields.
* Membership routes reuse `MembershipService`, target-aware `ProjectPolicy`, and `MembershipRepository`; ordinary mutation cannot assign, demote, or remove an owner.

Verification:

* Phase 2.2a baseline and Phase 2.2b authentication tests pass.
* Full unit and integration suite after membership mutation: `88 passed`.
* REST project API integration and service-delegation suite: `17 passed`.
* Membership unit and integration suite: `19 targeted unit tests` and `9 integration tests passed`.
* HTML/REST authorization parity and IDOR regression tests pass.
* `/dev/mail` permission tests and registration compensation tests pass.
* `schema.sql` executed twice consecutively without errors.
* determinism verification passed.
* Phase 2.1 regression passed.
* Two full volume resets produced identical deterministic seed snapshots.

There are no unresolved Phase 2.2a, Phase 2.2b, Phase 2.2c, or Phase 2.2d questions. The next approved design increments are ownership transfer or share-token access; CSRF and intentional vulnerabilities remain deferred.
