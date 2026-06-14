from pathlib import Path

from application.gui.messages import (
    count_backup_outcomes,
    format_backup_complete_message,
    format_restore_saved_message,
    is_backup_pipeline_idle,
)


def test_format_restore_saved_message_folder_first(tmp_path: Path) -> None:
    dest = tmp_path / "Restored"
    message = format_restore_saved_message(dest, (str(dest / "a.mkv"),))
    assert message.startswith("Your file(s) were saved to this folder:")
    assert str(dest.resolve()) in message
    assert "Extracted 1 file(s):" in message
    assert "a.mkv" in message


def test_format_restore_saved_message_empty_paths(tmp_path: Path) -> None:
    dest = tmp_path / "Restored"
    message = format_restore_saved_message(dest, ())
    assert str(dest.resolve()) in message
    assert "Nothing was extracted" in message


def test_is_backup_pipeline_idle() -> None:
    assert is_backup_pipeline_idle(["completed", "failed"]) is True
    assert is_backup_pipeline_idle(["uploading", "completed"]) is False
    assert is_backup_pipeline_idle([]) is False


def test_format_backup_complete_message() -> None:
    assert "2 file(s) uploaded" in format_backup_complete_message(2, 0)
    assert "1 file(s) failed" in format_backup_complete_message(1, 1)
    assert count_backup_outcomes(["completed", "failed"]) == (1, 1)
