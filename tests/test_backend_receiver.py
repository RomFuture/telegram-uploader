import ast
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from application.backend_receiver import BackendReceiver
from infrastructure.facade import (
    EnqueueResult,
    SessionProgressView,
    SessionView,
    SourceItemProgressView,
)


def test_backend_receiver_imports_only_infrastructure_facade() -> None:
    path = Path("src/application/backend_receiver.py")
    tree = ast.parse(path.read_text())
    layer_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in {"domain", "use_cases", "infrastructure", "application"}:
                    layer_imports.append(alias.name)
        if isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top in {"domain", "use_cases", "infrastructure", "application"}:
                layer_imports.append(node.module)

    assert layer_imports == ["infrastructure.facade"]


def test_start_session_delegates_to_facade() -> None:
    facade = MagicMock()
    session_id = uuid4()
    facade.start_session.return_value = SessionView(
        id=session_id,
        profile_name="default",
        status="created",
    )
    receiver = BackendReceiver(facade)

    view = receiver.start_session("default", "secret")

    facade.start_session.assert_called_once_with("default", "secret")
    assert view.session_id == session_id
    assert view.profile_name == "default"
    assert view.status == "created"


def test_enqueue_file_passes_display_name_to_facade(tmp_path: Path) -> None:
    facade = MagicMock()
    session_id = uuid4()
    source_item_id = uuid4()
    source_file = tmp_path / "disk-name.bin"
    source_file.write_bytes(b"x")
    facade.enqueue_file.return_value = EnqueueResult(
        source_item_id=source_item_id,
        display_name="User facing title",
        status="queued",
    )
    receiver = BackendReceiver(facade)

    item = receiver.enqueue_file(session_id, source_file, "User facing title")

    facade.enqueue_file.assert_called_once_with(session_id, source_file, "User facing title")
    assert item.display_name == "User facing title"
    assert item.display_name != source_file.name


def test_get_session_progress_returns_display_name_from_facade() -> None:
    facade = MagicMock()
    session_id = uuid4()
    source_item_id = uuid4()
    facade.get_session_progress.return_value = SessionProgressView(
        session_id=session_id,
        items=(
            SourceItemProgressView(
                source_item_id=source_item_id,
                display_name="Shown in UI",
                status="queued",
            ),
        ),
    )
    receiver = BackendReceiver(facade)

    progress = receiver.get_session_progress(session_id)

    facade.get_session_progress.assert_called_once_with(session_id)
    assert len(progress.items) == 1
    assert progress.items[0].display_name == "Shown in UI"


def test_request_restore_delegates_to_facade(tmp_path: Path) -> None:
    facade = MagicMock()
    session_id = uuid4()
    dest = tmp_path / "restored"
    downloaded = [dest / "vol.7z.001"]
    facade.request_restore.return_value = downloaded
    receiver = BackendReceiver(facade)

    result = receiver.request_restore(session_id, dest)

    facade.request_restore.assert_called_once_with(session_id, dest)
    assert result.downloaded_paths == (str(downloaded[0]),)
