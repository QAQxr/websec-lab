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

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", "local"),
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
        )
