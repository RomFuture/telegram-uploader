"""Domain-level exceptions. No I/O, no layer imports."""

from dataclasses import dataclass


class DomainError(Exception):
    """Base class for domain errors."""


class SessionNotFound(DomainError):
    """Raised when a session cannot be found."""


class SourceItemNotFound(DomainError):
    """Raised when a source item cannot be found."""


class ArchiveVolumeNotFound(DomainError):
    """Raised when an archive volume cannot be found."""


@dataclass(slots=True)
class InvalidStatusTransition(DomainError):
    """Raised when an entity status transition is not allowed."""

    entity: str
    from_status: str
    to_status: str

    def __post_init__(self) -> None:
        super().__init__(
            f"{self.entity}: cannot transition from {self.from_status!r} to {self.to_status!r}",
        )

    @classmethod
    def create(cls, entity: str, from_status: str, to_status: str) -> "InvalidStatusTransition":
        return cls(entity=entity, from_status=from_status, to_status=to_status)
