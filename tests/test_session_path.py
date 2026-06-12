from pathlib import Path

from infrastructure.paths import session_path_for_use


def test_session_path_migrates_when_parent_not_writable(tmp_path: Path) -> None:
    readonly_dir = tmp_path / "readonly_session"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o555)
    session = readonly_dir / "session.session"
    try:
        fallback = session_path_for_use(str(session))
        assert fallback.parent.name == "telegram-uploader"
        assert str(Path.home()) in str(fallback)
        assert fallback.parent.is_dir()
    finally:
        readonly_dir.chmod(0o755)


def test_session_path_keeps_writable_candidate(tmp_path: Path) -> None:
    session = tmp_path / "sessions" / "session.session"
    session.parent.mkdir()
    assert session_path_for_use(str(session)) == session.resolve()
