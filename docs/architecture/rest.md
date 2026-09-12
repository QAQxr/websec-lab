# REST Project API

## Phase Status

Phase 2.2c REST project parity, Phase 2.2d membership mutation, and Phase 2.2e ownership transfer are implemented for the normal project API. The API uses the same active session principal, project/membership/ownership-transfer services, `ProjectPolicy`, repository query scopes, field validation, ownership rules, membership rules, and visibility rules as the HTML workflow.

Share-token access, CSRF protection, and intentional vulnerability variants remain deferred.

## Endpoints

| Method | Endpoint | Service operation | Success |
|---|---|---|---|
| `GET` | `/api/projects` | `ProjectService.list_projects()` | `200` |
| `POST` | `/api/projects` | `ProjectService.create_project()` | `201` |
| `GET` | `/api/projects/<project_id>` | `ProjectService.get_project()` | `200` |
| `PATCH` | `/api/projects/<project_id>` | `ProjectService.update_project()` | `200` |
| `DELETE` | `/api/projects/<project_id>` | `ProjectService.delete_project()` | `200` |
| `GET` | `/api/projects/<project_id>/members` | `MembershipService.list_members()` | `200` |
| `POST` | `/api/projects/<project_id>/members` | `MembershipService.invite_member()` | `201` |
| `PATCH` | `/api/projects/<project_id>/members/<user_id>` | `MembershipService.change_member_role()` | `200` |
| `DELETE` | `/api/projects/<project_id>/members/<user_id>` | `MembershipService.remove_member()` | `200` |
| `POST` | `/api/projects/<project_id>/ownership-transfer` | `OwnershipTransferService.transfer_ownership()` | `200` |

The REST blueprint does not access project or membership repositories directly. The request path is:

```text
REST route
  -> ProjectService or MembershipService
  -> ProjectPolicy
  -> ProjectRepository or MembershipRepository
  -> MySQL
```

## Authentication

The API uses the existing opaque session cookie and `AuthService.authenticate_request()` request loader. Only an active server-side principal reaches the project service. Guest, pending, and locked requests receive:

```json
{
  "error": {
    "code": "unauthenticated",
    "message": "Authentication is required."
  }
}
```

with status `401`. The API never accepts `user_id`, `owner_id`, membership roles, or global roles from the client.

## Response Contract

Successful responses use a `data` envelope:

```json
{
  "data": {
    "id": 1,
    "name": "Example",
    "slug": "example",
    "description": "...",
    "visibility": "private"
  }
}
```

List responses contain an array in `data`. Errors use:

```json
{
  "error": {
    "code": "project_not_found",
    "message": "Project not found."
  }
}
```

The API maps errors as follows:

| Status | Meaning |
|---:|---|
| `400` | Invalid content type, JSON, project fields, or membership fields |
| `401` | No active authenticated principal |
| `403` | The principal can see the object but cannot perform the action |
| `404` | The project/member/user is outside the object scope or does not exist |
| `409` | Project or membership conflict |
| `500`/`503` | Generic server or infrastructure failure without internal details |

## Serialization Boundary

Project responses explicitly serialize:

```text
id, name, slug, description, visibility
created_at, updated_at
membership_role, effective_role, global_role
is_owner, is_global_admin
can_edit_metadata, can_edit_visibility, can_delete, can_manage_members, can_view_members
```

Member responses explicitly serialize only `user_id`, `username`, and membership `role`. Project responses do not expose `owner_id`, `settings_json`, raw `member_role`, the internal `ProjectAccess` object, session data, passwords, or database details. Global admin capability remains separate from project membership.

## Input Contract

Mutation requests require `Content-Type: application/json` and a JSON object. Accepted project fields are `name`, `description`, and `visibility`. Membership invite accepts `user_id` and `role`; role change accepts only `role`; remove has no body. Unknown fields, including ownership and global-role fields, return `400` rather than being assigned.

The service owns validation for both HTML and REST:

```text
name: required, maximum 160 characters
description: maximum 10000 characters
visibility: private, team, or shared
```

`PATCH` accepts partial project fields and fills omitted values from the authorized current project before calling the existing full update service method. Managers can update only metadata; owners and global admins can update visibility.

Membership requests use:

```json
POST /api/projects/<project_id>/members
{"user_id": 42, "role": "viewer"}

PATCH /api/projects/<project_id>/members/<user_id>
{"role": "contributor"}
```

`owner` is a protected role, not an ordinary mutation target. Target-aware policy denies owner assignment, owner demotion, owner removal, self mutation, manager escalation, and global-manager-without-membership confusion.

Ownership transfer is an explicit action endpoint. Its JSON body accepts only `target_user_id`; the target must be an active existing project member with a normal role. It updates the project owner and both membership roles in one locked transaction.

## Authorization and Visibility

The API preserves the HTML authorization matrix:

```text
private: owner, member, or global admin
team: active users can read; non-members are read-only
shared: private-like until share-token support exists
```

Global managers without project membership do not gain project manager capabilities. Global admins can access private projects without a project membership row. Owner mismatch cases remain fail closed for owner-only actions.

List and detail operations use the explicit `none`, `authenticated`, and `global` repository scopes. An authorized project ID is required in addition to knowing the numeric ID, so private objects are not exposed through IDOR-style lookups.

Member listing is allowed for project members, owners, and global admins. A team-visible non-member may read the project but receives `403` for member listing and all membership mutations. Private-project non-members receive `404` from the project scope.

## Verification

`tests/integration/test_project_api.py` covers:

* active authentication and pending/locked rejection
* create, list, detail, partial update, delete, validation, and slug behavior
* private, team, and shared visibility
* viewer, contributor, manager, owner, global manager, and admin capabilities
* global admin without a membership row
* private-project IDOR read/update/delete and list filtering
* owner membership mismatch behavior
* serialization and mass-assignment boundaries
* HTML/REST authorization parity

`tests/integration/test_membership.py` covers:

* owner, manager, viewer, contributor, global manager, and global admin boundaries
* invite, role change, removal, self-mutation, owner protection, and duplicate membership
* private/team object scope and IDOR/BOLA regression behavior
* HTML/REST parity and owner invariant checks

`tests/integration/test_ownership_transfer.py` covers:

* owner/global-admin success and old-owner-to-manager semantics
* actor and target authorization boundaries
* private/team object scope and IDOR/BOLA behavior
* invariant failures, target validation, and HTML/REST parity

The normal project API does not contain intentional IDOR, role injection, mass-assignment, or privilege-escalation behavior.
