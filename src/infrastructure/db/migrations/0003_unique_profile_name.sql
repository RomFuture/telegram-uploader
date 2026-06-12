-- One database per profile name (KeePassXC-style unlock model).
-- Dev DBs may have duplicates from old auto-create Unlock; keep newest per name.
DELETE FROM upload_sessions
WHERE id NOT IN (
    SELECT DISTINCT ON (profile_name) id
    FROM upload_sessions
    ORDER BY profile_name, created_at DESC
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_upload_sessions_profile_name ON upload_sessions (profile_name);
