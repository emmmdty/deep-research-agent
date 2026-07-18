"""Invite-only authentication with Argon2id passwords and opaque sessions."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.low_level import Type

from deep_research_agent.product.repositories import ProductRepository
from deep_research_agent.product.tables import InvitationTable, SessionTable, UserTable


SESSION_COOKIE_NAME = "dra_session"
SESSION_TTL = timedelta(hours=12)
INVITATION_TTL = timedelta(days=7)
_PASSWORD_HASHER = PasswordHasher(type=Type.ID)


def _id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(16)}"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _expired(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value <= _utc_now()


def _normalize_email(value: str) -> str:
    email = value.strip().casefold()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("a valid email address is required")
    return email


@dataclass(frozen=True)
class SessionIdentity:
    user_id: str
    tenant_id: str
    email: str
    role: str
    session_token_hash: str
    csrf_hash: str


@dataclass(frozen=True)
class LoginSession:
    identity: SessionIdentity
    session_token: str
    csrf_token: str


class AuthService:
    """Authentication service that never persists plaintext bearer values."""

    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    @staticmethod
    def hash_password(password: str) -> str:
        if len(password) < 12:
            raise ValueError("password must contain at least 12 characters")
        return _PASSWORD_HASHER.hash(password)

    @staticmethod
    def verify_password(password_hash: str, password: str) -> bool:
        try:
            return _PASSWORD_HASHER.verify(password_hash, password)
        except (InvalidHashError, VerifyMismatchError):
            return False

    def bootstrap_admin(self, *, email: str, password: str, tenant_id: str = "system") -> UserTable:
        """Create the first administrator without opening public registration."""

        existing = self.repository.get_user_by_email(_normalize_email(email))
        if existing is not None:
            return existing
        if self.repository.user_count() != 0:
            raise PermissionError("bootstrap is disabled after the first user is created")
        return self.repository.create_user(
            UserTable(
                user_id=_id("usr"),
                tenant_id=tenant_id,
                email=_normalize_email(email),
                role="admin",
                password_hash=self.hash_password(password),
            )
        )

    def register(self, *, email: str, password: str) -> UserTable:
        """Create a new tenant owner for the explicitly enabled local demo mode."""

        normalized = _normalize_email(email)
        if self.repository.get_user_by_email(normalized) is not None:
            raise ValueError("a user with this email already exists")
        return self.repository.create_user(
            UserTable(
                user_id=_id("usr"),
                tenant_id=_id("tenant"),
                email=normalized,
                role="admin",
                password_hash=self.hash_password(password),
            )
        )

    def create_invitation(
        self,
        *,
        email: str,
        tenant_id: str,
        role: str,
        invited_by: str,
    ) -> tuple[InvitationTable, str]:
        if role not in {"user", "admin"}:
            raise ValueError("role must be user or admin")
        if not tenant_id.strip():
            raise ValueError("tenant_id cannot be blank")
        normalized = _normalize_email(email)
        if self.repository.get_user_by_email(normalized) is not None:
            raise ValueError("a user with this email already exists")
        token = secrets.token_urlsafe(32)
        invitation = InvitationTable(
            invitation_id=_id("inv"),
            token_hash=_digest(token),
            tenant_id=tenant_id.strip(),
            email=normalized,
            role=role,
            invited_by=invited_by,
            expires_at=_utc_now() + INVITATION_TTL,
        )
        return self.repository.create_invitation(invitation), token

    def accept_invitation(self, token: str, *, password: str) -> UserTable:
        invitation = self.repository.get_invitation_by_token_hash(_digest(token))
        if invitation is None or invitation.accepted_at is not None or _expired(invitation.expires_at):
            raise PermissionError("the invitation is invalid or expired")
        if self.repository.get_user_by_email(invitation.email) is not None:
            raise ValueError("a user with this email already exists")
        user = self.repository.create_user(
            UserTable(
                user_id=_id("usr"),
                tenant_id=invitation.tenant_id,
                email=invitation.email,
                role=invitation.role,
                password_hash=self.hash_password(password),
            )
        )
        self.repository.accept_invitation(invitation.invitation_id, _utc_now())
        return user

    def login(self, *, email: str, password: str) -> LoginSession:
        user = self.repository.get_user_by_email(_normalize_email(email))
        if user is None or not user.active or not self.verify_password(user.password_hash, password):
            raise PermissionError("invalid email or password")
        session_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        record = SessionTable(
            session_id=_id("ses"),
            token_hash=_digest(session_token),
            csrf_hash=_digest(csrf_token),
            user_id=user.user_id,
            expires_at=_utc_now() + SESSION_TTL,
        )
        self.repository.create_session(record)
        return LoginSession(
            identity=SessionIdentity(
                user_id=user.user_id,
                tenant_id=user.tenant_id,
                email=user.email,
                role=user.role,
                session_token_hash=record.token_hash,
                csrf_hash=record.csrf_hash,
            ),
            session_token=session_token,
            csrf_token=csrf_token,
        )

    def authenticate(self, session_token: str | None) -> SessionIdentity | None:
        if not session_token:
            return None
        token_hash = _digest(session_token)
        record = self.repository.get_session_by_token_hash(token_hash)
        if record is None or _expired(record.expires_at):
            if record is not None:
                self.repository.delete_session_by_token_hash(token_hash)
            return None
        user = self.repository.get_user(record.user_id)
        if user is None or not user.active:
            return None
        return SessionIdentity(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            email=user.email,
            role=user.role,
            session_token_hash=record.token_hash,
            csrf_hash=record.csrf_hash,
        )

    @staticmethod
    def verify_csrf(identity: SessionIdentity, csrf_token: str | None) -> bool:
        return bool(csrf_token) and hmac.compare_digest(identity.csrf_hash, _digest(csrf_token or ""))

    def logout(self, session_token: str | None) -> None:
        if session_token:
            self.repository.delete_session_by_token_hash(_digest(session_token))


__all__ = [
    "AuthService",
    "LoginSession",
    "SESSION_COOKIE_NAME",
    "SESSION_TTL",
    "SessionIdentity",
]
