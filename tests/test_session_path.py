from pathlib import Path

from infrastructure.paths import session_path_for_use


def test_session_path_migrates_when_tmp_owned_by_root() -> None:
    path = session_path_for_use("/tmp/telegram_uploader/session.session")
    assert path.parent.name == "telegram-uploader"
    assert str(Path.home()) in str(path)
    assert path.parent.is_dir()
    assert path.parent.stat().st_uid != 0 or Path.home().as_posix() == "/root"
