# Project Membership Mutation

## Phase Status

Phase 2.2d implements the normal membership workflow. It provides invite, role change, removal, member listing, and matching HTML/REST authorization decisions without intentional vulnerability behavior.

Share-token access, CSRF protection, and vulnerable variants remain deferred. Ownership transfer is implemented as the separate Phase 2.2e workflow documented in `docs/architecture/ownership-transfer.md`.

## Data Model

`project_members` uses `(project_id, user_id)` as its primary key. `member_role` is one of:

```text
owner
manager
contributor
viewer
```

The owner invariant is:

```text
projects.owner_id == the only project_members.user_id with member_role = 'owner'
```

This phase never assigns `owner` through ordinary membership mutation, never demotes an owner, and never removes an owner. Ownership transfer is a separate workflow.

Global roles remain independent. `admin` is a value in `users.role`, not a project membership role. A global admin can manage a project without a membership row; a global manager without a project membership is not a project manager.

## Request Flow

```text
HTML or REST route
    -> MembershipService
    -> ProjectService object scope
    -> ProjectPolicy target-aware decision
    -> UserRepository / MembershipRepository
    -> MySQL transaction
```

`MembershipRepository` performs parameterized SQL, lookup, and transaction work only. It does not decide whether an actor, target role, or requested role is allowed. `MembershipService` performs authentication boundary handling, project and target lookup, input validation, policy invocation, and error mapping.

## Target-Aware Policy

The service calls these policy methods:

```python
can_invite_member(actor, project, requested_role, target_user_id)
can_change_member_role(actor, project, target_role, requested_role, target_user_id)
can_remove_member(actor, project, target_role, target_user_id)
```

The policy evaluates actor capability and target constraints together. Routes and templates do not implement role hierarchy.

| Actor | Invite | Role change | Remove |
|---|---|---|---|
| Owner | viewer, contributor, manager | any normal role to another normal role | viewer, contributor, manager |
| Project manager | viewer, contributor | viewer <-> contributor | viewer, contributor |
| Contributor/viewer | none | none | none |
| Global manager without membership | none | none | none |
| Global admin | viewer, contributor, manager | any normal role to another normal role | viewer, contributor, manager |

The following are always denied:

```text
assign owner
demote owner
remove owner
self invite
self role change
self removal
```

## Endpoints

HTML routes:

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/project/<project_id>/members` | List members for an authorized project member/admin |
| `GET` | `/project/<project_id>/members/new` | Render the invite form for a manager-capable actor |
| `POST` | `/project/<project_id>/members` | Invite a normal member role |
| `POST` | `/project/<project_id>/members/<user_id>/role` | Change a target member role |
| `POST` | `/project/<project_id>/members/<user_id>/remove` | Remove a target member |

REST routes:

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/projects/<project_id>/members` | List members |
| `POST` | `/api/projects/<project_id>/members` | Invite a member with `user_id` and `role` |
| `PATCH` | `/api/projects/<project_id>/members/<user_id>` | Change a member's `role` |
| `DELETE` | `/api/projects/<project_id>/members/<user_id>` | Remove a member |

Member responses contain only:

```json
{
  "data": {
    "user_id": 42,
    "username": "alice",
    "role": "viewer"
  }
}
```

Passwords, session data, internal tokens, invitation internals, and database details are not serialized.

## Validation and Errors

Only `viewer`, `contributor`, and `manager` are normal mutation roles. `owner` is recognized as a protected target/request and is denied by policy. Other role values return `400` validation errors.

The service handles:

* Unknown target user: `404 user_not_found`.
* Missing target membership: `404 member_not_found`.
* Duplicate membership: `409 membership_conflict`.
* Invalid user ID or role: `400 validation_error`.
* Disallowed actor/target operation: `403 forbidden`.
* Private project outside the caller's scope: `404 project_not_found`.
* Team project visible to a non-member but not manageable: `403 forbidden` for member listing and mutation.

The database unique key remains the final duplicate defense. A duplicate-key race is rolled back by the repository and mapped to the same stable `409` response.

## HTML/REST Parity

Both route families call the same `MembershipService` and `ProjectPolicy`. Given the same actor, project, target, current role, and requested role, HTML and REST return the same authorization decision and status class. UI controls are usability only; backend policy remains the security boundary.

## Audit Boundary

The current codebase has no mature audit service abstraction. A dedicated membership audit framework is therefore deferred rather than introduced as an unrelated Phase 2.2d module.
