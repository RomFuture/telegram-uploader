"""Launch the backup GUI: python -m application.gui"""

from application.backend_receiver import BackendReceiver
from application.gui.app import BackupApp
from infrastructure.bootstrap import build_facade
from infrastructure.config import load_config


def main() -> None:
    receiver = BackendReceiver(build_facade(load_config()))
    BackupApp(receiver).run()


if __name__ == "__main__":
    main()
