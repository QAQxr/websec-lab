from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_env: str
    lab_egress: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    redis_host: str
    redis_port: int
    redis_db: int
    internal_api_url: str
    public_base_url: str
    session_cookie_name: str
    session_ttl_seconds: int
    remember_session_ttl_seconds: int
    verification_ttl_seconds: int
    cookie_secure: bool
    cookie_samesite: str
    mailbox_enabled: bool

    @classmethod
    def from_env(cls) -> "Settings":
        app_env = os.getenv("APP_ENV", "local")
        return cls(
            app_env=app_env,
            lab_egress=os.getenv("LAB_EGRESS", "deny"),
            db_host=os.getenv("DB_HOST", "mysql"),
            db_port=int(os.getenv("DB_PORT", "3306")),
            db_name=os.getenv("DB_NAME", "websec_lab"),
            db_user=os.getenv("DB_USER", "websec"),
            db_password=os.getenv("DB_PASSWORD", "websec_lab_password"),
            redis_host=os.getenv("REDIS_HOST", "redis"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            internal_api_url=os.getenv("INTERNAL_API_URL", "http://internal-api:8081"),
            public_base_url=os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8080"),
            session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "session"),
            session_ttl_seconds=int(os.getenv("SESSION_TTL_SECONDS", "3600")),
            remember_session_ttl_seconds=int(
                os.getenv("REMEMBER_SESSION_TTL_SECONDS", "2592000")
            ),
            verification_ttl_seconds=int(os.getenv("VERIFICATION_TTL_SECONDS", "3600")),
            cookie_secure=os.getenv("SESSION_COOKIE_SECURE", "false").lower()
            in {"1", "true", "yes", "on"},
            cookie_samesite=os.getenv("SESSION_COOKIE_SAMESITE", "Lax"),
            mailbox_enabled=app_env in {"local", "test"},
        )
