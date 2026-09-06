from backend.repositories.health_repository import (
    DatabaseHealthRepository,
    InternalApiHealthRepository,
    RedisHealthRepository,
)


class HealthService:
    def __init__(self, database, redis_store, internal_api):
        self.checkers = {
            "database": database,
            "redis": redis_store,
            "internal_api": internal_api,
        }

    def check(self) -> dict:
        checks = {}
        for name, checker in self.checkers.items():
            try:
                checks[name] = "ok" if checker.check() else "unavailable"
            except Exception:
                checks[name] = "unavailable"

        status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
        return {"status": status, "checks": checks}


def build_health_service(settings):
    return HealthService(
        database=DatabaseHealthRepository(settings),
        redis_store=RedisHealthRepository(settings),
        internal_api=InternalApiHealthRepository(settings),
    )
