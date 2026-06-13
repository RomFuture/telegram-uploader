from pathlib import Path

from infrastructure.config import default_log_file_path, load_config


def test_default_log_file_path_uses_install_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("INSTALL_ROOT", str(tmp_path))
    assert default_log_file_path() == tmp_path / "telegram-uploader.log"


def test_load_config_app_log_file_override(tmp_path: Path, monkeypatch) -> None:
    custom = tmp_path / "custom.log"
    monkeypatch.setenv("APP_LOG_FILE", str(custom))
    monkeypatch.delenv("INSTALL_ROOT", raising=False)
    cfg = load_config()
    assert cfg.log_file_path == custom


def test_load_config_default_log_file_under_install_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("APP_LOG_FILE", raising=False)
    monkeypatch.setenv("INSTALL_ROOT", str(tmp_path / "project"))
    cfg = load_config()
    assert cfg.log_file_path == tmp_path / "project" / "telegram-uploader.log"
