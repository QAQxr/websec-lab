# AcmeCloud Product Model

## Status and Scope

This document records the product model for the WebSec Lab application, AcmeCloud. It is a design artifact only. Phase 2.2f and later workflows must not be inferred as implemented from this document.

The current implementation baseline is:

```text
Phase 2.1   infrastructure and network boundary
Phase 2.2a  MySQL schema, deterministic seed, and data snapshot
Phase 2.2b  authentication and server-side sessions
Phase 2.2c  project HTML/REST CRUD and project authorization
Phase 2.2d  membership listing, invite, role change, and removal
Phase 2.2e  independent project ownership transfer
```

This phase adds no Python code, route, API, database table, schema column, seed row, or vulnerability behavior.

## Product Positioning

AcmeCloud is a small-team collaboration and file-management SaaS. A team uses a project as a shared work container for project metadata, members, files, comments, notifications, and related collaboration activity.

WebSec Lab remains a local, closed, disposable security-learning environment. All identities, files, API keys, messages, and service data are synthetic. The normal product must be coherent and maintainable before later vulnerable variants are introduced.

The product model follows these principles:

* Normal business rules are implemented before security exercises weaken selected boundaries.
* Project membership and global account roles are separate concepts.
* Ownership, visibility, and access are explicit server-side decisions.
* A resource's owner is not automatically the only person who can access it, and access is not ownership.
* HTML and REST workflows use the same service and policy decisions.
* A UI control is never an authorization boundary.

## Core Vocabulary

### Project Is the Core Container

The existing `projects` model is sufficient as AcmeCloud's core team workspace. A separate `workspace` entity is not justified by the current product requirements and would add a second ownership and membership hierarchy.

In AcmeCloud, a project is the user-facing container for:

* project identity, description, slug, and visibility;
* one owner identified by `projects.owner_id`;
* project memberships and project roles;
* future folders and files;
* comments, notifications, and project activity;
* future project-scoped sharing and webhooks.

If an enterprise account, billing boundary, or multi-project team hierarchy becomes necessary later, it should be proposed as a separate design phase rather than silently redefining `Project`.

## Account Model

### User and Profile

The current `users` table is the account identity and profile record. It contains the login identifiers, password hash, global role, account status, profile bio/website, verification and login timestamps, and the avatar file reference.

The product distinguishes:

* `User`: authenticated account identity and global role.
* `Profile`: user-facing bio, website, avatar, and display information owned by that user.
* `Account status`: `pending`, `active`, or `locked`; only active users become normal project principals.
* `Session`: an opaque client cookie backed by Redis state and a MySQL session lifecycle row.

Profile ownership is user-scoped. A profile must not inherit project membership just because the user is visible in a project, and project access must not expose session or password data.

### Global Roles

The current global roles are:

| Global role | Meaning |
|---|---|
| `user` | Normal account with no global management capability |
| `manager` | Global account classification; it does not grant manager access to arbitrary projects |
| `admin` | Global capability for administration and project access without a membership row |

`admin` is never stored as `project_members.member_role`. A global `manager` is not a project manager unless that user has a `manager` membership in the specific project.

## Project and Membership Model

### Ownership

`projects.owner_id` is the ownership source of truth. Every project must have exactly one owner membership whose `user_id` matches `owner_id` and whose `member_role` is `owner`.

The existing project policy treats a mismatched owner membership as fail-closed for owner capabilities. Ordinary membership mutation cannot assign, demote, or remove an owner. Phase 2.2e implements ownership transfer as a separate atomic workflow with an active existing-member target; it does not create memberships or use ordinary role mutation.

### Project Roles

The current membership roles are:

| Project role | Product meaning |
|---|---|
| `owner` | Owns the project and controls owner-only project actions |
| `manager` | Manages project metadata and bounded membership operations |
| `contributor` | Participates in project work without membership administration |
| `viewer` | Read-oriented project participant |

The normal membership mutation boundary is target-aware:

* Owners may manage normal roles and may manage managers.
* Project managers may invite/remove viewers and contributors and may change viewer/contributor roles in either direction.
* Contributors and viewers do not mutate membership.
* Global admins may manage normal roles without a project membership row.
* Global managers without project membership do not gain project-manager capability.
* No ordinary operation assigns `owner`, demotes `owner`, removes `owner`, or mutates the actor's own membership.

### Visibility

The current project visibility values remain:

| Visibility | Product meaning |
|---|---|
| `private` | Owner, project members, and global admins can access the project |
| `team` | Active authenticated users can read the project; non-members remain read-only |
| `shared` | Private-like until a future share-link capability is explicitly implemented |

Reading a team-visible project does not grant member-list, file, edit, or membership-mutation access. Object-level authorization must be evaluated again for every child resource.

### Current Entity Relationship

```text
User 1 ---- owns ---- N Project
User N ---- member -- N Project       through project_members
Project 1 ---------- N Comment
Project 1 ---------- N File            future application workflow
User 1 ------------ N Message          sender or recipient
User 1 ------------ N Notification
User 1 ------------ N ApiKey
User 1 ------------ N AuditLog         actor
Project 1 ---------- N Share           future project/file target
Project 1 ---------- N WebhookConfig   future project configuration
```

The executable schema already contains several future tables, but table presence is not an implementation commitment. Current routes and services only cover authentication, projects, and membership.

## File Management Model

### File Concepts

The existing `files` table is a metadata and storage-reference foundation. It currently contains `project_id`, `owner_id`, `original_name`, `storage_name`, `storage_path`, MIME type, size, kind, public flag, and creation time. File application behavior is not implemented yet.

The future product model separates these concepts:

| Concept | Meaning |
|---|---|
| File identity | Stable opaque file object ID; not a filesystem path or authorization decision |
| File ownership | The `owner_id` accountable for the file's lifecycle and ownership-level actions |
| File location | The project and optional folder containing the file |
| File storage | Internal generated storage key/path; never a public URL by itself |
| File metadata | Name, MIME type, byte size, checksum, kind, timestamps, and lifecycle state |
| File access | A policy decision based on project context, file state, actor, and possible share grant |
| Upload | A state-changing workflow that validates actor, project, content, metadata, and storage result |
| Download | A child-object authorization workflow that checks the file and its parent context before bytes are returned |

### Ownership Is Not Access

The normal file model must preserve this distinction:

```text
file.owner_id       = who owns and is accountable for the file
file.project_id     = where the file is located
file access policy   = who may read, download, edit, move, delete, or share it
```

An owner may be the uploader without being the only reader. A project manager may manage project files without becoming the owner of every file. A project viewer may read/download an allowed file without receiving edit, delete, or share authority. A global admin may have administrative access without being written as a project member or file owner.

The future `FilePolicy` or equivalent child-resource policy must take the parent project and file state into account. `ProjectPolicy` remains the source of truth for project-level access; it must not be duplicated or replaced by route-local file checks.

### Proposed File Access Baseline

This is a future design baseline, not an implemented permission contract:

| Actor | Read/download | Upload | Edit/move | Delete/share |
|---|---:|---:|---:|---:|
| Project owner | Yes | Yes | Project policy | Project policy |
| Project manager | Yes | Yes | Project policy | Project policy |
| Contributor | Allowed project files | Yes | Own files or explicit project capability | Own files or explicit project capability |
| Viewer | Allowed project files | No by default | No | No |
| Team non-member | No file access from team visibility alone | No | No | No |
| Global admin | Administrative access | Yes | Administrative access | Administrative access |

The exact matrix must be approved with the File/Share phase. It must not silently turn `team` visibility into public file access.

### Folders and Location

Folders are a future organization layer inside a project. A folder should have a project owner context, a stable opaque ID, a parent folder or root state, a name, and lifecycle timestamps. A file should reference at most one folder location and must not escape its project through a client-supplied path.

The model should support a project root without requiring a synthetic global folder. Moving a file is a state-changing authorization decision, not merely a path rename. Cross-project moves should be a separately designed operation because they affect ownership, access, shares, comments, and audit history.

### Upload, Download, and Lifecycle

Future upload flow:

```text
authenticated actor
  -> project/file policy
  -> metadata and content validation
  -> generated storage key
  -> durable file metadata transaction
  -> project-scoped response
```

Future download flow:

```text
file ID
  -> load file metadata
  -> load parent project context
  -> evaluate file and project access
  -> resolve-and-contain storage key
  -> stream bytes through an authorized application path
```

Nginx must not expose the upload volume as a public filesystem path. The current design already requires Flask authorization before file delivery or a controlled internal redirect.

Soft delete/recycle-bin behavior is recommended for normal file management because it preserves recovery and audit semantics. A future schema change may add lifecycle fields such as `deleted_at` only after the behavior and retention policy are approved. No such fields are added here.

## Sharing Model

The existing `shares` table is reserved for future project/file share links. A share record should target exactly one project or file, store a hash of an opaque token, identify the creator, support expiration and revocation, and remain separate from project membership.

### Access Modes

The product should distinguish:

| Mode | Meaning |
|---|---|
| Private | Only normal object policy grants access |
| Project members | Access is derived from membership and child-resource policy |
| Shared link | A bearer capability grants only the explicitly configured target/action until expiry/revocation |
| Public | Unauthenticated broad access; not required for the initial product and should remain disabled by default |

The default share-link capability should be read or download only. Edit-through-link is not a default and would require a separate threat model, authorization model, and audit design.

Share links need:

* high-entropy opaque tokens represented by a database hash;
* a single explicit target and scope;
* expiration and server-side revocation;
* creator and creation timestamp;
* bounded actions such as `read` or `download`;
* no implicit project membership or ownership;
* audit events without logging the raw token.

The `shared` project visibility value must not be treated as a working share token. Until this phase is approved, it remains private-like as in the current implementation.

## Collaboration Model

### Comments

Comments are project-scoped collaboration records authored by a user. They support discussion attached to a project and later may attach to a file or other child object if that relationship is explicitly designed. Comment visibility follows the parent project/child-resource policy. The existing `deleted_at` field supports soft deletion and audit-friendly display.

### Messages

Messages are direct user-to-user communication and threads. They are not project membership records and must be authorized by sender/recipient or an explicitly defined participant relation. A project ID in a message payload, if added later, must not replace recipient/participant authorization.

### Notifications

Notifications are delivery records for events such as project invitations, mentions, file shares, and password notices. A notification tells a user that an event occurred; it does not itself grant access to the referenced project, file, message, or share. Following a notification must perform the target object's normal authorization check.

## API and Service Boundaries

### User API Keys

The existing `api_keys` table models user-owned API credentials with a hash, safe display prefix, lifecycle timestamps, and scopes. Future API key authentication should:

* store only a hash for normal operation;
* derive the actor from the key, never from a client `user_id` field;
* apply global capability and object-level project/file policy after scope checking;
* support revocation and rotation;
* keep API-key scope separate from project membership role;
* never expose the lab-only raw fixture value in normal responses.

An API key is a credential, not an administrator role and not a share link.

### Webhooks

`webhook_configs` is a future project-scoped integration configuration. Owners or explicitly authorized project managers may configure it; an internal worker should perform delivery using a stored secret/signature policy.

Webhook configuration and delivery have different trust boundaries:

* User input selects a destination and event scope.
* The application validates and stores configuration under project policy.
* A worker performs outbound delivery under the configured egress policy.
* Response content from the destination is untrusted and must not become authenticated application state.

URL validation, private-address policy, redirects, DNS rebinding, secrets, retry state, and delivery audit records require a dedicated phase. The current `webhook_configs` table does not mean webhooks are implemented.

### Internal API

The existing `internal-api` is a private Compose service-to-service boundary. It is not a user-facing API and must not be made reachable through an ordinary browser or public REST route merely because the web service can reach it.

The internal service contains synthetic status/configuration fixtures only. Future internal calls need service-level authentication or a narrowly scoped network contract, explicit response schemas, and no trust in client-supplied internal identity headers.

### HTML and REST

Future File, Share, and Collaboration APIs should follow the current route-to-service-to-policy-to-repository direction. HTML and REST must invoke the same use-case service and policy decision. Serializers must expose product fields, not password/session data, raw storage paths, share tokens, database internals, or policy implementation objects.

## Administration Boundary

Global administration is separate from project membership:

| Area | Global admin responsibility | Project-level responsibility |
|---|---|---|
| Users | Account status, support actions, global roles, profile support | No automatic membership grant |
| Projects | Global visibility/access where policy allows, support operations | Owner/manager project operations |
| Audit logs | Read protected audit history and investigate events | Project actions emit actor/project context |
| System settings | Manage product-wide settings | Project settings remain project-scoped |
| API keys | Support/revoke according to global policy | User owns key lifecycle and scopes |
| Training data | Manage local lab fixtures and progress controls | Training progress never grants product access |

Audit logs are evidence, not an authorization source. System settings are not project membership. A global admin response must continue to represent `global_role=admin` separately from `membership_role`.

## Security Assets and Trust Boundaries

The most important future assets are:

* Account credentials, sessions, verification/reset tokens, and profile data.
* Project metadata, `owner_id`, membership rows, visibility, and role transitions.
* File bytes, file metadata, storage keys, folder locations, and lifecycle state.
* Share-link token capabilities and expiration/revocation state.
* Private messages, comments, notification payloads, and their referenced objects.
* API key hashes/scopes, webhook secrets/configuration, and internal service responses.
* Audit logs, system settings, and training state.

The critical trust boundaries are:

```text
Browser/Burp
  -> Nginx
  -> Flask authenticated principal
  -> Route
  -> Service
  -> ProjectPolicy or future child-resource policy
  -> Repository/object scope
  -> MySQL/Redis/filesystem/internal-api
```

For files and shares, the important boundary is:

```text
client-supplied object ID or bearer link
  -> target lookup
  -> parent project context
  -> actor/share capability decision
  -> storage or response
```

Knowing a project ID, file ID, folder ID, or share token must not bypass the applicable object-level policy. A team-visible project must not make private file bytes public. A notification, API key scope, or global manager role must not be confused with project membership.

## Future Roadmap

This roadmap is design guidance only. No item below is implemented by this document.

### 2.2e Ownership Transfer (complete and pushed)

Implemented as an explicit owner-only/global-admin workflow that atomically updates `projects.owner_id` and the unique owner membership invariant. The old owner becomes a manager, the active existing member target becomes owner, and the HTML/REST action uses one locked transaction with rollback.

Ownership transfer is complete locally. File ownership policy, project administration, share creation, and audit accountability can now build on a stable ownership transition.

### 2.2g CSRF and Security Hardening

The nominal numbering places this after the File/Share design, but implementation priority should be evaluated before adding more browser state-changing workflows. Existing HTML mutations currently rely on authentication and same-site cookie behavior but do not implement a CSRF token. A hardening phase should establish a reusable, tested CSRF boundary for project and future file/share forms without mixing in intentional vulnerabilities.

### 2.2f File and Share Access Baseline

After ownership semantics and the browser mutation boundary are approved, define folders, file lifecycle, child-resource authorization, upload/download handling, and bounded share links. File access must be implemented before share links so a share cannot hide an undefined parent-object policy.

### Phase 3 Core File and Collaboration Modules

Implement the normal file/folder lifecycle, comments, messages, notifications, API key workflows, and selected webhooks only after their object and trust boundaries are approved. Keep project policy as the project-level source of truth and introduce child-resource policies only where the resource needs distinct rules.

### Phase 4 Vulnerable Variants

Only after the normal workflows are stable and regression-covered, add isolated vulnerable variants for IDOR/BOLA, broken access control, CSRF, path handling, SSRF, XSS, and related exercises. Each variant must have a local-only fixture, a success oracle, a patched behavior, and a regression test. No real credentials, third-party targets, or production deployment are in scope.

## Explicitly Not Implemented

The following remain design-only or deferred:

* Folder and File routes/services/storage lifecycle.
* File access policy and download/upload behavior.
* Share links, public access, expiration, and revocation workflows.
* CSRF protection and broader security hardening.
* API key authentication and management routes.
* Webhook configuration/delivery.
* Message, comment, and notification routes beyond the existing schema/seed foundation.
* Administration UI for users, audit logs, and system settings.
* Any intentional vulnerability, vulnerable variant, exploit path, or training-mode implementation.

## Design Gate

Before the next implementation phase, the approved design should answer:

1. Which owner transitions are allowed and how is the owner invariant locked atomically?
2. Which project roles can read, upload, edit, move, delete, and share each file state?
3. Which file and project targets can a share link reference, and which actions can it grant?
4. How are upload storage, download authorization, soft delete, and recovery represented?
5. Which browser and API mutations require CSRF or equivalent request binding?
6. Which API key scopes and internal service identities are trusted for each operation?

Until those decisions are approved, the current Phase 2.2d implementation remains the normal business baseline and must not be expanded by assumption.
