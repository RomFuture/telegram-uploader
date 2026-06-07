-- Idempotent alignment for DBs created before schema matched domain.models.
ALTER TABLE source_items ADD COLUMN IF NOT EXISTS display_name TEXT NOT NULL DEFAULT '';

ALTER TABLE archive_volumes DROP COLUMN IF EXISTS provider_name;
ALTER TABLE archive_volumes DROP COLUMN IF EXISTS provider_file_name;
