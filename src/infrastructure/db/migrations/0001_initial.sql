CREATE TABLE IF NOT EXISTS upload_sessions (
    id UUID PRIMARY KEY,
    profile_name TEXT NOT NULL,
    encryption_key TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS source_items (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES upload_sessions(id) ON DELETE CASCADE,
    source_path TEXT NOT NULL,
    display_name TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS archive_volumes (
    id UUID PRIMARY KEY,
    source_item_id UUID NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    local_path TEXT NOT NULL,
    part_number INTEGER NOT NULL,
    status TEXT NOT NULL,
    external_file_id TEXT,
    external_message_id TEXT,
    provider_download_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_source_items_session_id ON source_items(session_id);
CREATE INDEX IF NOT EXISTS ix_source_items_status ON source_items(status);
CREATE INDEX IF NOT EXISTS ix_archive_volumes_source_item_id ON archive_volumes(source_item_id);
CREATE INDEX IF NOT EXISTS ix_archive_volumes_status ON archive_volumes(status);
CREATE INDEX IF NOT EXISTS ix_archive_volumes_external_file_id ON archive_volumes(external_file_id);
