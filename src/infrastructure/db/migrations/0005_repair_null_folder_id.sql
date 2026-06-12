-- Assign orphaned queue items to the default "All files" folder per session.
UPDATE source_items AS item
SET folder_id = folder.id
FROM backup_folders AS folder
WHERE item.folder_id IS NULL
  AND folder.session_id = item.session_id
  AND folder.name = 'All files';
