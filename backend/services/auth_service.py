from dataclasses import dataclass
from datetime import timedelta
import hashlib
import re
import secrets

from backend.config import Settings
from backend.repositories.mailbox_repository import MailboxRepository
from backend.repositories.session_repository import RedisSessionStore, SessionRepository
from backend.repositories.user_repository import DuplicateAccountError, UserRepository
from backend.repositories.verification_repository import VerificationRepository
from backend.services.password_service import PasswordService
from backend.services.session_service import SessionService
from backend.utils.time import utc_now


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class AuthDependencies:
    users: UserRepository
    verifications: VerificationRepository
    mailbox: MailboxRepository
    sessions: SessionService


class AuthService:
    USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,64}$")
    EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, settings: Settings, dependencies: AuthDependencies, clock=utc_now):
        self.settings = settings
        self.users = dependencies.users
        self.verifications = dependencies.verifications
        self.mailbox = dependencies.mailbox
        self.sessions = dependencies.sessions
        self.clock = clock

    def register(self, username: str, email: str, password: str, confirmation: str) -> None:
        username = username.strip()
        email = email.strip().lower()
        self._validate_registration(username, email, password, confirmation)
        if self.users.find_by_username(username):
            raise AuthError("That username is already in use.", 409)
        if self.users.find_by_email(email):
            raise AuthError("That email address is already in use.", 409)

        now = self.clock()
        password_hash = PasswordService.hash_password(password)
        try:
            user_id = self.users.create_pending(username, email, password_hash, now)
        except DuplicateAccountError as error:
            raise AuthError("That username or email is already in use.", 409) from error

        raw_token = secrets.token_urlsafe(32)
        verification_id = self.verifications.create(
            user_id,
            self._hash_token(raw_token),
            now + timedelta(seconds=self.settings.verification_ttl_seconds),
            now,
        )
        self.mailbox.put_verification(
            verification_id,
            {
                "id": verification_id,
                "to": email,
                "subject": "Verify your AcmeCloud account",
                "verification_url": f"{self.settings.public_base_url.rstrip('/')}/verify/{raw_token}",
                "created_at": now.isoformat(),
            },
            self.settings.verification_ttl_seconds,
        )

    def verify_email(self, token: str) -> None:
        if not token or len(token) > 200:
            raise AuthError("This verification link is invalid.", 400)
        outcome = self.verifications.consume(self._hash_token(token), self.clock())
        if outcome.status == "invalid":
            raise AuthError("This verification link is invalid.", 400)
        if outcome.status == "expired":
            self.mailbox.remove_verification(outcome.verification_id)
            raise AuthError("This verification link has expired.", 400)
        if outcome.status == "already_used":
            raise AuthError("This verification link has already been used.", 409)
        self.mailbox.remove_verification(outcome.verification_id)

    def login(
        self,
        identifier: str,
        password: str,
        remember_me: bool,
        old_session_key: str | None,
        ip_address: str,
        user_agent: str,
    ) -> str:
        user = self.users.find_by_identifier(identifier.strip()) if identifier else None
        if user is None or not PasswordService.verify_password(password, user["password_hash"]):
            raise AuthError("Invalid username or password.", 401)
        if user["status"] == "pending":
            raise AuthError("Please verify your email before signing in.", 403)
        if user["status"] == "locked":
            raise AuthError("This account is locked.", 403)
        session_key = self.sessions.rotate(
            old_session_key,
            user["id"],
            remember_me,
            ip_address,
            user_agent,
        )
        self.users.update_last_login(user["id"], self.clock())
        return session_key

    def authenticate_request(self, session_key: str | None):
        session = self.sessions.load(session_key)
        if session is None:
            return None, None
        user = self.users.find_by_id(session["user_id"])
        if user is None or user["status"] != "active":
            self.sessions.invalidate(session_key)
            return None, None
        return user, session

    def logout(self, session_key: str | None) -> None:
        self.sessions.invalidate(session_key)

    def mailbox_messages(self) -> list[dict]:
        return self.mailbox.list_verifications()

    @classmethod
    def _validate_registration(cls, username, email, password, confirmation):
        if not cls.USERNAME_PATTERN.fullmatch(username):
            raise AuthError("Username must be 3-64 letters, numbers, or underscores.")
        if not cls.EMAIL_PATTERN.fullmatch(email):
            raise AuthError("Enter a valid email address.")
        if len(password) < 12:
            raise AuthError("Password must be at least 12 characters.")
        if len(password) > 128:
            raise AuthError("Password must be no more than 128 characters.")
        if password != confirmation:
            raise AuthError("Password confirmation does not match.")

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_auth_service(settings: Settings) -> AuthService:
    session_repository = SessionRepository(settings)
    dependencies = AuthDependencies(
        users=UserRepository(settings),
        verifications=VerificationRepository(settings),
        mailbox=MailboxRepository(settings),
        sessions=SessionService(
            session_repository,
            RedisSessionStore(settings),
            settings,
        ),
    )
    return AuthService(settings, dependencies)
