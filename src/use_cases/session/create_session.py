from dataclasses import dataclass

from use_cases.domain.factories import session_create
from use_cases.domain.mappers import domain_to_session_record
from use_cases.domain.models import Session
from use_cases.repositories.session import SessionRepository


@dataclass(frozen=True, slots=True)
class CreateSessionUseCase:
    sessions: SessionRepository

    def execute(self, profile_name: str, encryption_key: str) -> Session:
        session = session_create(profile_name, encryption_key)
        self.sessions.add(domain_to_session_record(session))
        return session
