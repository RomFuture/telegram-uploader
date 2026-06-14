import ast
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from application.backend_receiver import BackendReceiver
from use_cases.public.results import (
    QueueItemResult,
    QueueItemSnapshotResult,
    RestoreResult,
    SessionQueueSnapshotResult,
    SessionResult,
)


def test_backend_receiver_imports_only_use_cases_public() -> None:
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

    assert layer_imports == [
        "application.restore_preflight_messages",
        "application.restore_preflight_scope",
        "application.settings_values",
        "use_cases.public",
        "use_cases.public.commands",
    ]


def test_unlock_session_delegates_to_api() -> None:
    api = MagicMock()
    session_id = uuid4()
    api.unlock_session.return_value = SessionResult(
        session_id=session_id,
        profile_name="default",
        status="created",
    )
    receiver = BackendReceiver(api)

    view = receiver.unlock_session("default", "secret")

    api.unlock_session.assert_called_once()
    assert view.session_id == session_id
    assert view.profile_name == "default"


def test_create_database_delegates_to_api() -> None:
    api = MagicMock()
    session_id = uuid4()
    api.create_database.return_value = SessionResult(
        session_id=session_id,
        profile_name="vault",
        status="created",
    )
    receiver = BackendReceiver(api)

    view = receiver.create_database("vault", "secret")

    api.create_database.assert_called_once()
    assert view.profile_name == "vault"


def test_list_profiles_delegates_to_api() -> None:
    api = MagicMock()
    api.list_profiles.return_value = ("default", "work")
    receiver = BackendReceiver(api)

    assert receiver.list_profiles() == ("default", "work")


def test_enqueue_file_passes_display_name_to_api(tmp_path: Path) -> None:
    api = MagicMock()
    session_id = uuid4()
    source_item_id = uuid4()
    source_file = tmp_path / "disk-name.bin"
    source_file.write_bytes(b"x")
    api.enqueue_file.return_value = QueueItemResult(
        source_item_id=source_item_id,
        display_name="User facing title",
        status="queued",
    )
    receiver = BackendReceiver(api)

    item = receiver.enqueue_file(session_id, source_file, "User facing title")

    api.enqueue_file.assert_called_once()
    command = api.enqueue_file.call_args[0][0]
    assert command.session_id == session_id
    assert command.source_path == source_file
    assert command.display_name == "User facing title"
    assert item.display_name == "User facing title"
    assert item.display_name != source_file.name


def test_get_session_queue_snapshot_returns_display_name_from_api() -> None:
    api = MagicMock()
    session_id = uuid4()
    source_item_id = uuid4()
    api.get_queue_snapshot.return_value = SessionQueueSnapshotResult(
        session_id=session_id,
        items=(
            QueueItemSnapshotResult(
                source_item_id=source_item_id,
                display_name="Shown in UI",
                status="queued",
            ),
        ),
    )
    receiver = BackendReceiver(api)

    snapshot = receiver.get_session_queue_snapshot(session_id)

    api.get_queue_snapshot.assert_called_once_with(session_id)
    assert len(snapshot.items) == 1
    assert snapshot.items[0].display_name == "Shown in UI"


def test_request_restore_delegates_to_api(tmp_path: Path) -> None:
    api = MagicMock()
    session_id = uuid4()
    dest = tmp_path / "restored"
    api.restore_session.return_value = RestoreResult(
        session_id=session_id,
        downloaded_paths=(str(dest / "vol.7z.001"),),
    )
    receiver = BackendReceiver(api)

    result = receiver.request_restore(session_id, dest)

    api.restore_session.assert_called_once()
    command = api.restore_session.call_args[0][0]
    assert command.session_id == session_id
    assert command.dest_path == dest
    assert result.downloaded_paths == (str(dest / "vol.7z.001"),)
