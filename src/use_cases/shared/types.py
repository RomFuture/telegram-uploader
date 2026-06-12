"""Domain entity types for use_cases consumers (e.g. infrastructure type hints).

Infrastructure must not import ``domain`` directly; import entity types from here.
"""

from domain.models import ArchiveVolume, Session, SourceItem

__all__ = ["ArchiveVolume", "Session", "SourceItem"]
