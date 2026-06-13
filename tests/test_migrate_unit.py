from unittest.mock import MagicMock, patch

from infrastructure.db.migrate import apply_migrations


@patch("infrastructure.db.migrate.connect")
def test_apply_migrations_inserts_each_file_once(mock_connect: MagicMock) -> None:
    conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = conn
    mock_connect.return_value.__exit__.return_value = None

    conn.execute.return_value.fetchone.return_value = None

    apply_migrations("postgresql://u:p@localhost/db")

    assert conn.execute.call_count >= 2
    insert_calls = [
        call for call in conn.execute.call_args_list if "INSERT INTO schema_migrations" in str(call)
    ]
    assert len(insert_calls) >= 1
