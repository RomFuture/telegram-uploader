"""Infrastructure adapters, composition root, and runtime wiring."""

from infrastructure.bootstrap import bootstrap, build_facade
from infrastructure.facade import BackupFacade

__all__ = ["BackupFacade", "bootstrap", "build_facade"]
