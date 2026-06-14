"""Tests for restore preflight user-facing copy."""

from application.restore_preflight_messages import format_restore_preflight_message
from application.restore_preflight_scope import RestorePreflightScope
from use_cases.public.folders import DEFAULT_FOLDER_NAME
from use_cases.public.results import RestorePreflightReason, RestorePreflightResult

_ALL_FILES_SCOPE = RestorePreflightScope(
    folder_name=DEFAULT_FOLDER_NAME,
    restore_entire_session=True,
)


def test_format_stale_backup_message_includes_count() -> None:
    result = RestorePreflightResult(
        ready=False,
        reason=RestorePreflightReason.STALE_BACKUP,
        incomplete_volume_count=3,
    )

    message = format_restore_preflight_message(result, _ALL_FILES_SCOPE)

    assert "3 file(s)" in message
    assert "Start Backup to retry" in message


def test_format_ready_message_with_skipped_legacy() -> None:
    result = RestorePreflightResult(
        ready=True,
        reason=RestorePreflightReason.READY,
        restorable_count=2,
        legacy_volume_count=3,
    )

    message = format_restore_preflight_message(result, _ALL_FILES_SCOPE)

    assert "Ready to restore 2 file(s) from all files." in message
    assert "3 legacy Bot API backup volume(s)" in message
    assert "will be skipped" in message


def test_format_legacy_only_message_includes_count() -> None:
    result = RestorePreflightResult(
        ready=False,
        reason=RestorePreflightReason.LEGACY_VOLUMES,
        legacy_volume_count=2,
    )

    message = format_restore_preflight_message(result, _ALL_FILES_SCOPE)

    assert "Nothing to restore in all files." in message
    assert "2 legacy Bot API backup volume(s) skipped" in message


def test_format_ready_message_with_skipped_parts() -> None:
    result = RestorePreflightResult(
        ready=True,
        reason=RestorePreflightReason.READY,
        restorable_count=2,
        incomplete_volume_count=1,
    )

    message = format_restore_preflight_message(result, _ALL_FILES_SCOPE)

    assert "Ready to restore 2 file(s) from all files." in message
    assert "1 unfinished archive part(s)" in message
    assert "Start Backup to retry those files." in message


def test_format_empty_folder_uses_scope_folder_name() -> None:
    result = RestorePreflightResult(
        ready=False,
        reason=RestorePreflightReason.EMPTY_FOLDER,
    )
    scope = RestorePreflightScope(folder_name="Work", restore_entire_session=False)

    message = format_restore_preflight_message(result, scope)

    assert "No completed backups in Work." in message


def test_format_healthcheck_failed_message() -> None:
    result = RestorePreflightResult(
        ready=False,
        reason=RestorePreflightReason.HEALTHCHECK_FAILED,
    )

    message = format_restore_preflight_message(result, _ALL_FILES_SCOPE)

    assert "Telegram Client API is not ready" in message
    assert "telegram-uploader-login" in message
