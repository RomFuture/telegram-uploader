"""Unlock an existing database by profile name and encryption key."""

import secrets
from dataclasses import dataclass

import domain as domain
from use_cases.shared.mappers import session_record_to_domain
from use_cases.shared.repositories.session import SessionRepository
from use_cases.shared.types import Session


@dataclass(frozen=True, slots=True)
class UnlockSessionUseCase:
    sessions: SessionRepository

    def execute(self, profile_name: str, encryption_key: str) -> Session:
        record = self.sessions.find_by_profile_name(profile_name.strip())
        if record is None:
            raise domain.DomainError.session_not_found_by_profile(profile_name.strip())
        if not secrets.compare_digest(record.encryption_key, encryption_key):
            raise domain.DomainError.wrong_encryption_key(profile_name.strip())
        return session_record_to_domain(record)
