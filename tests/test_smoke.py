from application.ports import StorageProviderPort


def test_storage_provider_port_is_runtime_protocol() -> None:
    assert isinstance(StorageProviderPort, type)
