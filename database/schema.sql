SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) NOT NULL PRIMARY KEY,
    applied_at DATETIME(6) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    bio TEXT NOT NULL,
    website VARCHAR(512) NULL,
    avatar_file_id BIGINT UNSIGNED NULL,
    email_verified_at DATETIME(6) NULL,
    last_login_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT chk_users_role CHECK (role IN ('user', 'manager', 'admin')),
    CONSTRAINT chk_users_status CHECK (status IN ('pending', 'active', 'locked')),
    KEY idx_users_role_status (role, status),
    KEY idx_users_created_at (created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS projects (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    owner_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(160) NOT NULL,
    slug VARCHAR(180) NOT NULL,
    description TEXT NOT NULL,
    visibility VARCHAR(16) NOT NULL,
    settings_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_projects_slug UNIQUE (slug),
    CONSTRAINT chk_projects_visibility CHECK (visibility IN ('private', 'team', 'shared')),
    CONSTRAINT fk_projects_owner FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    KEY idx_projects_owner_id (owner_id),
    KEY idx_projects_visibility (visibility)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS project_members (
    project_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    member_role VARCHAR(16) NOT NULL,
    invited_by BIGINT UNSIGNED NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (project_id, user_id),
    CONSTRAINT chk_project_members_role CHECK (member_role IN ('viewer', 'contributor', 'manager', 'owner')),
    CONSTRAINT fk_project_members_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_project_members_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_project_members_invited_by FOREIGN KEY (invited_by) REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE,
    KEY idx_project_members_user_id (user_id),
    KEY idx_project_members_role (project_id, member_role)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS files (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    project_id BIGINT UNSIGNED NULL,
    owner_id BIGINT UNSIGNED NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    storage_name VARCHAR(255) NOT NULL,
    storage_path VARCHAR(1024) NOT NULL,
    mime_type VARCHAR(160) NOT NULL,
    size_bytes BIGINT UNSIGNED NOT NULL,
    kind VARCHAR(32) NOT NULL,
    is_public BOOLEAN NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_files_storage_name UNIQUE (storage_name),
    CONSTRAINT chk_files_kind CHECK (kind IN ('avatar', 'document', 'image', 'attachment')),
    CONSTRAINT fk_files_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_files_owner FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    KEY idx_files_project_id (project_id),
    KEY idx_files_owner_id (owner_id),
    KEY idx_files_storage_path (storage_path(191))
) ENGINE=InnoDB;

-- Add the cross-referenced FK after files exists, while allowing schema replay.
SET @fk_users_avatar_file_exists = (
    SELECT COUNT(*)
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND CONSTRAINT_NAME = 'fk_users_avatar_file'
      AND CONSTRAINT_TYPE = 'FOREIGN KEY'
);

SET @add_users_avatar_file_fk = IF(
    @fk_users_avatar_file_exists = 0,
    'ALTER TABLE users ADD CONSTRAINT fk_users_avatar_file FOREIGN KEY (avatar_file_id) REFERENCES files (id) ON DELETE SET NULL ON UPDATE CASCADE',
    'SET @schema_noop = 1'
);

PREPARE add_users_avatar_file_fk FROM @add_users_avatar_file_fk;
EXECUTE add_users_avatar_file_fk;
DEALLOCATE PREPARE add_users_avatar_file_fk;

CREATE TABLE IF NOT EXISTS sessions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    session_key VARCHAR(255) NOT NULL,
    remember_me BOOLEAN NOT NULL,
    created_at DATETIME(6) NOT NULL,
    last_seen_at DATETIME(6) NOT NULL,
    ip_address VARCHAR(64) NOT NULL,
    user_agent VARCHAR(512) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_sessions_session_key UNIQUE (session_key),
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    KEY idx_sessions_user_last_seen (user_id, last_seen_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS messages (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    sender_id BIGINT UNSIGNED NOT NULL,
    recipient_id BIGINT UNSIGNED NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    thread_id BIGINT UNSIGNED NULL,
    read_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_messages_sender FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_messages_recipient FOREIGN KEY (recipient_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_messages_thread FOREIGN KEY (thread_id) REFERENCES messages (id) ON DELETE SET NULL ON UPDATE CASCADE,
    KEY idx_messages_recipient_created (recipient_id, created_at),
    KEY idx_messages_sender_created (sender_id, created_at),
    KEY idx_messages_thread_id (thread_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comments (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    project_id BIGINT UNSIGNED NOT NULL,
    author_id BIGINT UNSIGNED NOT NULL,
    body TEXT NOT NULL,
    created_at DATETIME(6) NOT NULL,
    deleted_at DATETIME(6) NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_comments_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_comments_author FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    KEY idx_comments_project_created (project_id, created_at),
    KEY idx_comments_author_id (author_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    kind VARCHAR(64) NOT NULL,
    payload_json JSON NOT NULL,
    read_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    KEY idx_notifications_user_read_created (user_id, read_at, created_at),
    KEY idx_notifications_kind (kind)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS api_keys (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    label VARCHAR(120) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    display_prefix VARCHAR(32) NOT NULL,
    raw_key_for_lab TEXT NULL,
    scopes_json JSON NOT NULL,
    last_used_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_api_keys_key_hash UNIQUE (key_hash),
    CONSTRAINT fk_api_keys_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    KEY idx_api_keys_user_id (user_id),
    KEY idx_api_keys_display_prefix (display_prefix)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    actor_id BIGINT UNSIGNED NULL,
    event_type VARCHAR(80) NOT NULL,
    method VARCHAR(12) NOT NULL,
    path VARCHAR(512) NOT NULL,
    parameters_json JSON NOT NULL,
    metadata_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_audit_logs_actor FOREIGN KEY (actor_id) REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE,
    KEY idx_audit_logs_actor_created (actor_id, created_at),
    KEY idx_audit_logs_event_created (event_type, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS system_settings (
    setting_key VARCHAR(120) NOT NULL,
    setting_value TEXT NOT NULL,
    value_type VARCHAR(16) NOT NULL,
    updated_by BIGINT UNSIGNED NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (setting_key),
    CONSTRAINT chk_system_settings_value_type CHECK (value_type IN ('string', 'json', 'boolean')),
    CONSTRAINT fk_system_settings_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE,
    KEY idx_system_settings_updated_at (updated_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS email_verifications (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at DATETIME(6) NOT NULL,
    used_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_email_verifications_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_email_verifications_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    KEY idx_email_verifications_user (user_id),
    KEY idx_email_verifications_expires (expires_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS password_resets (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at DATETIME(6) NOT NULL,
    used_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_password_resets_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_password_resets_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    KEY idx_password_resets_user (user_id),
    KEY idx_password_resets_expires (expires_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS shares (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    token_hash VARCHAR(255) NOT NULL,
    created_by BIGINT UNSIGNED NOT NULL,
    project_id BIGINT UNSIGNED NULL,
    file_id BIGINT UNSIGNED NULL,
    expires_at DATETIME(6) NULL,
    revoked_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_shares_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_shares_created_by FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_shares_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_shares_file FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE ON UPDATE CASCADE,
    KEY idx_shares_project_id (project_id),
    KEY idx_shares_file_id (file_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS webhook_configs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    project_id BIGINT UNSIGNED NOT NULL,
    created_by BIGINT UNSIGNED NOT NULL,
    target_url VARCHAR(2048) NOT NULL,
    secret_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_webhook_configs_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_webhook_configs_created_by FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    KEY idx_webhook_configs_project_active (project_id, is_active)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS import_jobs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    project_id BIGINT UNSIGNED NULL,
    requested_by BIGINT UNSIGNED NOT NULL,
    source_url VARCHAR(2048) NOT NULL,
    source_format VARCHAR(32) NOT NULL,
    status VARCHAR(24) NOT NULL,
    payload_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT chk_import_jobs_status CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    CONSTRAINT fk_import_jobs_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_import_jobs_requested_by FOREIGN KEY (requested_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    KEY idx_import_jobs_status_created (status, created_at),
    KEY idx_import_jobs_project_id (project_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS point_balances (
    user_id BIGINT UNSIGNED NOT NULL,
    balance BIGINT NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (user_id),
    CONSTRAINT chk_point_balances_nonnegative CHECK (balance >= 0),
    CONSTRAINT fk_point_balances_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS point_redemptions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    points_spent BIGINT NOT NULL,
    reward_code VARCHAR(80) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_point_redemptions_idempotency_key UNIQUE (idempotency_key),
    CONSTRAINT chk_point_redemptions_positive CHECK (points_spent > 0),
    CONSTRAINT fk_point_redemptions_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    KEY idx_point_redemptions_user_created (user_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS challenge_progress (
    user_id BIGINT UNSIGNED NOT NULL,
    module_id VARCHAR(120) NOT NULL,
    status VARCHAR(24) NOT NULL,
    hints_used INT UNSIGNED NOT NULL,
    findings_count INT UNSIGNED NOT NULL,
    completed_at DATETIME(6) NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (user_id, module_id),
    CONSTRAINT chk_challenge_progress_status CHECK (status IN ('not_started', 'in_progress', 'completed')),
    CONSTRAINT fk_challenge_progress_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    KEY idx_challenge_progress_status (status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS lab_attempts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NULL,
    module_id VARCHAR(120) NOT NULL,
    objective VARCHAR(255) NOT NULL,
    result VARCHAR(24) NOT NULL,
    request_hash CHAR(64) NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT chk_lab_attempts_result CHECK (result IN ('success', 'failure', 'submitted')),
    CONSTRAINT fk_lab_attempts_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE,
    KEY idx_lab_attempts_user_module (user_id, module_id),
    KEY idx_lab_attempts_created_at (created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS password_history (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_password_history_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    KEY idx_password_history_user_created (user_id, created_at)
) ENGINE=InnoDB;
