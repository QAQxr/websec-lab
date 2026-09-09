# Project Authorization Model

## Phase Status

Phase 2.2c finalizes the normal HTML and REST project authorization model. This document describes the policy contract used by the project service, repository query scope, routes, serializers, templates, and tests.

Membership mutation routes, ownership transfer workflows, share-token routes, CSRF protection, and intentional vulnerabilities remain deferred.

## Authorization Pipeline

```text
authentication state
    -> global capability
    -> project owner / membership
    -> visibility
    -> action capability
    -> repository object scope
```

`ProjectPolicy.access_for()` is the single authorization truth source. It returns a `ProjectAccess` value containing authentication state, global role, raw membership role, owner/admin flags, visibility, and action-specific capabilities. `ProjectService` does not recalculate roles.

## Authentication

Only `status == "active"` users receive a normal project principal.

| Principal | Project policy |
|---|---|
| Guest | Deny |
| Pending | Deny |
| Locked | Deny |
| Active | Continue to global/project policy |

Global `admin` does not bypass the active-status check.

## Global Roles

Global roles are `user`, `manager`, and `admin`.

Global `manager` is not a project manager. Without a project membership row, a manager cannot edit, delete, or manage members. An active non-member can read a `team` project, but that is read-only access.

Global `admin` is a global capability, not a project membership role. An admin can view, edit, delete, and manage any project without a `project_members` row. The UI displays global admin capability separately from project membership.

## Ownership and Membership

`projects.owner_id` is the only ownership source of truth:

```text
is_owner = project.owner_id == principal.user_id
```

The database invariant remains one owner membership row matching `owner_id`, but a mismatched `member_role = "owner"` never grants owner-only capabilities. The policy fails closed for delete, ownership, visibility, and member-management decisions in that state.

Project membership roles are `owner`, `manager`, `contributor`, and `viewer`.

| Capability | Owner | Manager member | Contributor | Viewer | Global admin |
|---|---:|---:|---:|---:|---:|
| View project | Yes | Yes | Yes | Yes | Yes |
| Edit name/description | Yes | Yes | No | No | Yes |
| Edit visibility | Yes | No | No | No | Yes |
| Delete project | Yes | No | No | No | Yes |
| Manage members | Yes | Yes, scoped | No | No | Yes |
| Invite viewer/contributor | Yes | Yes | No | No | Yes |
| Invite manager/owner | Yes/future boundary | No | No | No | Yes/future boundary |
| Transfer ownership | Future owner-only workflow | No | No | No | Future global capability |

Membership mutation is not implemented in this phase. The policy exposes the boundaries so future routes can reuse them without rebuilding authorization logic.

## Visibility

`private` projects are visible to owners, members, and global admins.

`team` projects are visible to every active authenticated user, including non-members. This is read-only visibility and does not grant edit, delete, member-management, or membership capabilities.

`shared` projects have no public route in this phase. Ordinary project list/detail routes treat a shared project as private-like for non-members. A future share-token capability is out of scope.

## Action Boundaries

The policy exposes separate capabilities:

```text
can_view
can_edit_metadata
can_edit_visibility
can_delete
can_manage_members
can_invite_viewer
can_invite_contributor
can_invite_manager
can_invite_owner
can_change_member_role
can_remove_member
can_transfer_ownership
```

The HTML edit GET and POST paths use the same metadata-edit boundary. A viewer or contributor cannot see the edit form, and a manager cannot change visibility even though a manager can edit ordinary metadata.

## Repository Scope

The service computes an explicit query scope through `ProjectPolicy.query_scope()`:

| Scope | Meaning |
|---|---|
| `none` | Guest, pending, locked, or invalid principal |
| `authenticated` | Owner/member projects plus all `team` projects |
| `global` | Global admin can query all projects |

`ProjectRepository` applies the scope in SQL as defense-in-depth. It does not infer whether a caller is an admin. The service still evaluates the returned object through `ProjectPolicy` before exposing it.

Unauthorized or nonexistent project lookups use the existing indistinguishable 404 behavior where the object is not in the caller's repository scope.

## REST Parity

The REST project blueprint exposes the same list, create, detail, update, and delete workflows as HTML. It calls `ProjectService` only; it does not query the repository or calculate role decisions itself. The service continues to call `ProjectPolicy.access_for()` and supplies the explicit repository scope.

REST mutations accept only project metadata fields and use the service validation and capability boundaries. The JSON serializer keeps global role/capability separate from project membership and excludes internal database fields and the raw policy object. API errors use stable JSON envelopes while retaining the HTML authorization decisions: unauthorized private objects return 404, visible read-only objects return 403 for mutations, and owner/admin capabilities remain unchanged.

## UI Contract

Templates display:

* Global role/capability separately from project membership.
* Owner status from the policy result, not from a raw membership role.
* Team non-member access as read-only.
* Edit controls only when `can_edit_metadata` is true.

Raw `member_role = "admin"` is never used or generated by the project authorization model.
