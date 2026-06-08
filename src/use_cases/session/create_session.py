from dataclasses import dataclass

import domain as domain
from use_cases.mappers import domain_to_session_record
from use_cases.repositories.session import SessionRepository
from use_cases.types import Session


@dataclass(frozen=True, slots=True)
class CreateSessionUseCase:
    sessions: SessionRepository

    def execute(self, profile_name: str, encryption_key: str) -> Session:
        session = domain.create_session(profile_name, encryption_key)
        self.sessions.add(domain_to_session_record(session))
        return session
