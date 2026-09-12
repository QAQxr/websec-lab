# Project Ownership Transfer

## Phase Status

Phase 2.2e implements the normal Project Ownership Transfer workflow. It is an independent action and is not a special case of membership role mutation.

This phase does not implement File/Folder, Share Link, CSRF, Webhooks, API Keys, learning modes, challenge modes, or intentional vulnerabilities.

## Business Purpose

Ownership transfer changes the accountable owner of an existing Project while preserving the old owner's project relationship. It is used when responsibility for a project moves between existing team members.

The target must already be an active member. Transfer does not invite a user, create a membership, or use the normal membership role-change endpoint.

## Actor Authorization

| Actor | Transfer |
|---|---:|
| Current project owner | Allow to an existing active normal member |
| Global admin | Allow to an existing active normal member without project membership |
| Project manager | Deny |
| Contributor | Deny |
| Viewer | Deny |
| Global manager without project membership | Deny; a team-visible project does not change this |
| Guest, pending, or locked user | `401` |

The owner decision is target-aware and fail-closed. A project owner must have the matching owner membership row in the invariant-checked transaction. A mismatched or missing owner row is not repaired automatically.

`ProjectPolicy.can_transfer_ownership()` evaluates the active actor, project owner source, actor membership role, target role, and target identity. The service separately verifies target existence, account status, membership, and the owner invariant while the relevant rows are locked.

## Target Constraints

The target must:

* exist as a user;
* have `status = 'active'`;
* already have a membership row for the project;
* have `member_role` of `viewer`, `contributor`, or `manager`;
* not be the current owner;
* not be the actor.

The target cannot be made an owner by posting `role=owner` to the normal membership role endpoint. Ordinary membership mutation continues to reject owner assignment, owner demotion, and owner removal.

## Resulting State

For old owner `A` and target member `B`, a successful transfer produces:

```text
projects.owner_id = B
project_members(A).member_role = 'manager'
project_members(B).member_role = 'owner'
```

The old owner remains a project member and retains manager capabilities. The target becomes the sole owner. The global role of either user is unchanged.

The invariant is:

```text
projects.owner_id
    == the only project_members.user_id with member_role = 'owner'
```

## Endpoints

HTML:

```text
GET  /project/<project_id>/ownership/transfer
POST /project/<project_id>/ownership/transfer
```

The HTML form accepts an existing member `target_user_id`. It is a usability surface only; the service and policy enforce every rule.

REST:

```text
POST /api/projects/<project_id>/ownership-transfer
```

Request:

```json
{
  "target_user_id": 42
}
```

Success returns the normal project `data` representation for the authenticated actor. This means the former owner sees their new manager membership, while the target's subsequent project read shows owner state. The response excludes passwords, session data, storage internals, raw membership internals, and database implementation details.

## Transaction and Locking Strategy

`OwnershipTransferRepository` owns a transaction context but no authorization decisions. The service performs policy and invariant decisions using the locked data.

The transaction order is:

```text
BEGIN
  lock project row FOR UPDATE
  lock all project membership rows FOR UPDATE in user_id order
  lock actor and target user rows FOR UPDATE
  re-check active actor/target status
  re-check exactly one owner membership matching projects.owner_id
  evaluate target-aware ProjectPolicy
  update projects.owner_id and updated_at
  change old owner membership to manager
  change target membership to owner
COMMIT
```

Any exception, failed expected-row count, invariant violation, or commit failure rolls back the complete transaction. The project row serializes transfers for the same project, and membership rows are locked deterministically before updates. No Python-only check is treated as the concurrency guarantee.

The repository updates expected rows with role predicates and checks affected row counts. It does not create a missing membership or repair inconsistent owner data.

## Error Mapping

| Condition | Result |
|---|---|
| Guest, pending, or locked actor | `401 unauthenticated` |
| Private project outside actor scope | Existing `404 project_not_found` |
| Visible project but actor lacks transfer capability | `403 forbidden` |
| Target user does not exist | `404 target_user_not_found` |
| Target is not a project member | `404 member_not_found` |
| Target is inactive, self, owner, or disallowed actor | `403 forbidden` |
| Owner membership missing, duplicated, or mismatched | `409 ownership_invariant` |
| Invalid target user ID | `400 validation_error` |
| Concurrent/expected-row update failure | `409 ownership_invariant` after rollback |

The existing object-scoped project lookup happens before the transfer transaction. Private-project IDOR behavior therefore remains the same as other project mutations. Team visibility permits project reading but does not grant ownership transfer.

## HTML/REST Parity

Both endpoints call `OwnershipTransferService.transfer_ownership()`:

```text
HTML route                  REST route
      \                         /
       -> OwnershipTransferService
       -> ProjectService object scope
       -> ProjectPolicy
       -> OwnershipTransferRepository transaction
       -> MySQL
```

The normal membership PATCH endpoint remains unchanged as the role-mutation boundary. It cannot assign `owner`.

## Audit Boundary

The current codebase has no mature audit abstraction suitable for a new cross-entity event. This phase does not create a new audit framework or write ad hoc audit rows. A future audit phase may record actor, project, old owner, new owner, operation, and timestamp without storing credentials or raw tokens.

## Verification Coverage

The Phase 2.2e tests cover:

* owner and global-admin success;
* manager, contributor, viewer, global-manager, guest, pending, and locked denial;
* viewer/contributor/manager existing-member targets;
* non-member, inactive, owner, and self targets;
* private/team object scope and IDOR/BOLA behavior;
* exact owner invariant after success and failed requests;
* invariant failure without automatic repair;
* mid-transaction failure rollback in the service transaction boundary;
* HTML/REST decision parity;
* full-suite regression behavior.
