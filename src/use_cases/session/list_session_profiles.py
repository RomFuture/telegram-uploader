"""List profile names for the Unlock screen dropdown."""

from dataclasses import dataclass

from use_cases.shared.repositories.session import SessionRepository


@dataclass(frozen=True, slots=True)
class ListSessionProfilesUseCase:
    sessions: SessionRepository

    def execute(self) -> tuple[str, ...]:
        return self.sessions.list_profiles()
