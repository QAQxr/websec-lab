SET NAMES utf8mb4;
SET time_zone = '+00:00';

INSERT IGNORE INTO users
    (id, username, email, password_hash, role, status, bio, website, email_verified_at, created_at, updated_at)
VALUES
    (1, 'admin', 'admin@example.local', 'pbkdf2_sha256$600000$d2Vic2VjLWxhYjphZG1pbg$E1XtFq1TL3tSpGiZHF9hFyWdIeV4yArGbI8nYC-tPKg', 'admin', 'active', 'Operations administrator for the local AcmeCloud lab.', 'https://admin.example.local', '2026-01-01 00:00:00.000000', '2026-01-01 00:00:00.000000', '2026-01-01 00:00:00.000000'),
    (2, 'manager', 'manager@example.local', 'pbkdf2_sha256$600000$d2Vic2VjLWxhYjptYW5hZ2Vy$hWfC2JnhpVF7lL8KrUKwzF2WlAcr8Env7VS2aEUYLSU', 'manager', 'active', 'Product team manager for the local AcmeCloud lab.', 'https://manager.example.local', '2026-01-01 00:00:00.000000', '2026-01-01 00:01:00.000000', '2026-01-01 00:01:00.000000'),
    (3, 'alice', 'alice@example.local', 'pbkdf2_sha256$600000$d2Vic2VjLWxhYjphbGljZQ$Rptzpxi7M0ce4xD0KOerMvO2oVRY3qtJlpb0GXDx9nk', 'user', 'active', 'Product designer working on the Alpha workspace.', 'https://alice.example.local', '2026-01-01 00:00:00.000000', '2026-01-01 00:02:00.000000', '2026-01-01 00:02:00.000000'),
    (4, 'bob', 'bob@example.local', 'pbkdf2_sha256$600000$d2Vic2VjLWxhYjpib2I$0ZFzOrHjvBsiusVGiF_u-zFaB-FQa-kVT0Xr1PlImAQ', 'user', 'active', 'Engineer collaborating on Alpha and owning Beta.', 'https://bob.example.local', '2026-01-01 00:00:00.000000', '2026-01-01 00:03:00.000000', '2026-01-01 00:03:00.000000'),
    (5, 'charlie', 'charlie@example.local', 'pbkdf2_sha256$600000$d2Vic2VjLWxhYjpjaGFybGll$cwGGVKoQw9kupk5p0KIc5jTyF1sBXNLz1EgmD6KqLgc', 'user', 'active', 'Independent contributor with a separate Gamma workspace.', 'https://charlie.example.local', '2026-01-01 00:00:00.000000', '2026-01-01 00:04:00.000000', '2026-01-01 00:04:00.000000');

INSERT IGNORE INTO projects
    (id, owner_id, name, slug, description, visibility, settings_json, created_at, updated_at)
VALUES
    (1, 1, 'Operations', 'operations', 'Internal operations and deployment coordination.', 'private', '{"theme":"ops","region":"local"}', '2026-01-02 00:00:00.000000', '2026-01-02 00:00:00.000000'),
    (2, 2, 'Product', 'product', 'Product planning and delivery workspace.', 'team', '{"theme":"product","region":"local"}', '2026-01-02 00:01:00.000000', '2026-01-02 00:01:00.000000'),
    (3, 3, 'Project Alpha', 'project-alpha', 'Alice project for design and research notes.', 'private', '{"theme":"alpha","region":"local"}', '2026-01-02 00:02:00.000000', '2026-01-02 00:02:00.000000'),
    (4, 4, 'Project Beta', 'project-beta', 'Bob project for engineering reports.', 'team', '{"theme":"beta","region":"local"}', '2026-01-02 00:03:00.000000', '2026-01-02 00:03:00.000000'),
    (5, 5, 'Project Gamma', 'project-gamma', 'Charlie project for profile and media work.', 'shared', '{"theme":"gamma","region":"local"}', '2026-01-02 00:04:00.000000', '2026-01-02 00:04:00.000000');

INSERT IGNORE INTO project_members
    (project_id, user_id, member_role, invited_by, created_at)
VALUES
    (1, 1, 'owner', 1, '2026-01-02 01:00:00.000000'),
    (1, 2, 'manager', 1, '2026-01-02 01:01:00.000000'),
    (2, 2, 'owner', 2, '2026-01-02 01:02:00.000000'),
    (2, 1, 'viewer', 2, '2026-01-02 01:03:00.000000'),
    (3, 3, 'owner', 3, '2026-01-02 01:04:00.000000'),
    (3, 4, 'viewer', 3, '2026-01-02 01:05:00.000000'),
    (4, 4, 'owner', 4, '2026-01-02 01:06:00.000000'),
    (5, 5, 'owner', 5, '2026-01-02 01:07:00.000000');

INSERT IGNORE INTO files
    (id, project_id, owner_id, original_name, storage_name, storage_path, mime_type, size_bytes, kind, is_public, created_at)
VALUES
    (1, 1, 1, 'deployment-notes.txt', 'seed-operations-deployment-notes.txt', 'projects/1/seed-operations-deployment-notes.txt', 'text/plain', 1280, 'document', 0, '2026-01-03 00:00:00.000000'),
    (2, 2, 2, 'roadmap.pdf', 'seed-product-roadmap.pdf', 'projects/2/seed-product-roadmap.pdf', 'application/pdf', 40960, 'document', 0, '2026-01-03 00:01:00.000000'),
    (3, 3, 3, 'alice-private.txt', 'seed-alpha-alice-private.txt', 'projects/3/seed-alpha-alice-private.txt', 'text/plain', 960, 'document', 0, '2026-01-03 00:02:00.000000'),
    (4, 4, 4, 'bob-report.txt', 'seed-beta-bob-report.txt', 'projects/4/seed-beta-bob-report.txt', 'text/plain', 2048, 'document', 0, '2026-01-03 00:03:00.000000'),
    (5, 5, 5, 'charlie-profile.png', 'seed-gamma-charlie-profile.png', 'projects/5/seed-gamma-charlie-profile.png', 'image/png', 8192, 'image', 0, '2026-01-03 00:04:00.000000');

INSERT IGNORE INTO messages
    (id, sender_id, recipient_id, subject, body, thread_id, read_at, created_at)
VALUES
    (1, 3, 4, 'Alpha review', 'Can you review the latest Alpha notes?', NULL, '2026-01-04 00:10:00.000000', '2026-01-04 00:00:00.000000'),
    (2, 4, 3, 'Re: Alpha review', 'I added comments to the design section.', 1, NULL, '2026-01-04 00:01:00.000000'),
    (3, 2, 3, 'Product planning', 'Please check the next planning draft.', NULL, NULL, '2026-01-04 00:02:00.000000'),
    (4, 1, 2, 'Operations update', 'The local deployment notes are ready.', NULL, '2026-01-04 00:11:00.000000', '2026-01-04 00:03:00.000000');

INSERT IGNORE INTO comments
    (id, project_id, author_id, body, created_at, deleted_at)
VALUES
    (1, 3, 3, 'Alpha discovery notes are ready for review.', '2026-01-05 00:00:00.000000', NULL),
    (2, 3, 4, 'The review checklist is clear.', '2026-01-05 00:01:00.000000', NULL),
    (3, 2, 2, 'The roadmap now includes the infrastructure milestone.', '2026-01-05 00:02:00.000000', NULL),
    (4, 4, 4, 'Beta report is ready for the team.', '2026-01-05 00:03:00.000000', NULL),
    (5, 5, 5, 'Gamma media inventory is complete.', '2026-01-05 00:04:00.000000', NULL);

INSERT IGNORE INTO notifications
    (id, user_id, kind, payload_json, read_at, created_at)
VALUES
    (1, 2, 'project_invitation', '{"project_id":1,"from_user_id":1}', NULL, '2026-01-06 00:00:00.000000'),
    (2, 3, 'mention', '{"project_id":3,"comment_id":2}', NULL, '2026-01-06 00:01:00.000000'),
    (3, 4, 'file_share', '{"project_id":4,"file_id":4}', '2026-01-06 00:10:00.000000', '2026-01-06 00:02:00.000000'),
    (4, 2, 'password_reset_notification', '{"requested_by":"local-seed"}', NULL, '2026-01-06 00:03:00.000000');

INSERT IGNORE INTO api_keys
    (id, user_id, label, key_hash, display_prefix, raw_key_for_lab, scopes_json, last_used_at, created_at)
VALUES
    (1, 1, 'Local admin automation', 'sha256:lab-admin-key-hash-001', 'lab_admin_', 'LAB_ONLY_ADMIN_KEY_001', '["admin:read","admin:write"]', NULL, '2026-01-07 00:00:00.000000'),
    (2, 2, 'Local manager integration', 'sha256:lab-manager-key-hash-002', 'lab_manager_', 'LAB_ONLY_MANAGER_KEY_002', '["projects:read","projects:write"]', '2026-01-07 00:10:00.000000', '2026-01-07 00:01:00.000000'),
    (3, 3, 'Local user export', 'sha256:lab-user-key-hash-003', 'lab_user_', 'LAB_ONLY_USER_KEY_003', '["projects:read"]', NULL, '2026-01-07 00:02:00.000000');

INSERT IGNORE INTO audit_logs
    (id, actor_id, event_type, method, path, parameters_json, metadata_json, created_at)
VALUES
    (1, 1, 'login', 'POST', '/login', '{"source":"seed"}', '{"ip":"127.0.0.1","request_id":"seed-001"}', '2026-01-08 00:00:00.000000'),
    (2, 1, 'project.create', 'POST', '/projects', '{"project_id":1}', '{"source":"seed"}', '2026-01-08 00:01:00.000000'),
    (3, 1, 'project.member.add', 'POST', '/project/1/members', '{"user_id":2,"role":"manager"}', '{"source":"seed"}', '2026-01-08 00:02:00.000000'),
    (4, 3, 'file.upload', 'POST', '/files/upload', '{"file_id":3}', '{"source":"seed"}', '2026-01-08 00:03:00.000000'),
    (5, 3, 'message.send', 'POST', '/messages/send', '{"message_id":1}', '{"source":"seed"}', '2026-01-08 00:04:00.000000'),
    (6, 1, 'settings.update', 'PATCH', '/admin/settings/site_name', '{"value":"AcmeCloud"}', '{"source":"seed"}', '2026-01-08 00:05:00.000000');

INSERT IGNORE INTO system_settings
    (setting_key, setting_value, value_type, updated_by, updated_at)
VALUES
    ('site_name', 'AcmeCloud', 'string', 1, '2026-01-09 00:00:00.000000'),
    ('default_project_visibility', 'private', 'string', 1, '2026-01-09 00:01:00.000000'),
    ('max_upload_size', '10485760', 'json', 1, '2026-01-09 00:02:00.000000'),
    ('maintenance_mode', 'false', 'boolean', 1, '2026-01-09 00:03:00.000000');
