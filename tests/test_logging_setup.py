import logging
from pathlib import Path

import pytest

from observation.logging_setup import reset_logging_for_tests, setup_logging


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    reset_logging_for_tests()
    yield
    reset_logging_for_tests()


def test_setup_logging_writes_to_file(tmp_path: Path) -> None:
    log_file = tmp_path / "telegram-uploader.log"
    setup_logging(log_file=log_file, level="INFO", also_console=False)

    logging.getLogger("test.logging").info("hello from test")

    assert log_file.is_file()
    assert "hello from test" in log_file.read_text(encoding="utf-8")


def test_setup_logging_is_idempotent(tmp_path: Path) -> None:
    log_file = tmp_path / "telegram-uploader.log"
    setup_logging(log_file=log_file, level="INFO", also_console=False)
    handler_count = len(logging.getLogger().handlers)

    setup_logging(log_file=log_file, level="DEBUG", also_console=False)

    assert len(logging.getLogger().handlers) == handler_count


def test_setup_logging_respects_level(tmp_path: Path) -> None:
    log_file = tmp_path / "telegram-uploader.log"
    setup_logging(log_file=log_file, level="WARNING", also_console=False)

    logging.getLogger("test.level").info("hidden")
    logging.getLogger("test.level").warning("visible")

    content = log_file.read_text(encoding="utf-8")
    assert "hidden" not in content
    assert "visible" in content
