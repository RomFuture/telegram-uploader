import secrets
from dataclasses import dataclass

import domain as domain
from use_cases.shared.mappers import domain_to_session_record
from use_cases.shared.repositories.session import SessionRepository
from use_cases.shared.types import Session


@dataclass(frozen=True, slots=True)
class SessionCreateOutcome:
    session: Session
    generated_encryption_key: str | None


@dataclass(frozen=True, slots=True)
class CreateSessionUseCase:
    sessions: SessionRepository

    def execute(self, profile_name: str, encryption_key: str | None) -> SessionCreateOutcome:
        generated_key: str | None = None
        resolved_key = encryption_key.strip() if encryption_key else ""
        if not resolved_key:
            resolved_key = secrets.token_urlsafe(32)
            generated_key = resolved_key

        session = domain.create_session(profile_name, resolved_key)
        self.sessions.add(domain_to_session_record(session))
        return SessionCreateOutcome(session=session, generated_encryption_key=generated_key)
