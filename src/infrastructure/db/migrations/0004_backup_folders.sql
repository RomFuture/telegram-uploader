-- Virtual folders per session (ownCloud-style sidebar).
CREATE TABLE IF NOT EXISTS backup_folders (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES upload_sessions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (session_id, name)
);

ALTER TABLE source_items ADD COLUMN IF NOT EXISTS folder_id UUID REFERENCES backup_folders(id);

CREATE INDEX IF NOT EXISTS ix_backup_folders_session_id ON backup_folders(session_id);
CREATE INDEX IF NOT EXISTS ix_source_items_folder_id ON source_items(folder_id);
