from pathlib import Path

import pytest

import domain as domain
from use_cases.restore.dest_path import validate_restore_dest_path


def test_validate_restore_dest_path_accepts_writable_directory(tmp_path: Path) -> None:
    dest = tmp_path / "restored"
    validate_restore_dest_path(dest)
    assert dest.is_dir()


def test_validate_restore_dest_path_rejects_non_writable_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "readonly"
    dest.mkdir()

    def deny_write(_path: Path, _mode: int) -> bool:
        return False

    monkeypatch.setattr("use_cases.restore.dest_path.os.access", deny_write)

    with pytest.raises(domain.DomainError) as exc_info:
        validate_restore_dest_path(dest)
    assert exc_info.value.code == "restore_destination_not_writable"
