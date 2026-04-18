from infrastructure.archive.seven_zip_service import build_hashed_volume_name
from infrastructure.db.migrate import list_migration_files


def test_build_hashed_volume_name_is_stable() -> None:
    first_name = build_hashed_volume_name("holiday.mov", 1)
    second_name = build_hashed_volume_name("holiday.mov", 1)
    assert first_name == second_name
    assert first_name.endswith(".7z.001")


def test_build_hashed_volume_name_changes_for_different_sources() -> None:
    first_name = build_hashed_volume_name("holiday.mov", 1)
    second_name = build_hashed_volume_name("work.mov", 1)
    assert first_name != second_name


def test_initial_migration_exists() -> None:
    migration_files = list_migration_files()
    file_names = {path.name for path in migration_files}
    assert "0001_initial.sql" in file_names
    assert all(path.parent.name == "migrations" for path in migration_files)


def test_display_name_migration_exists() -> None:
    migration_files = list_migration_files()
    file_names = {path.name for path in migration_files}
    assert "0002_add_display_name.sql" in file_names
