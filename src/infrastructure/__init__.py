"""Infrastructure adapters, composition root, and runtime wiring."""

from infrastructure.bootstrap import bootstrap, wire_celery_entrypoint, wire_gui_entrypoint

__all__ = ["bootstrap", "wire_celery_entrypoint", "wire_gui_entrypoint"]
