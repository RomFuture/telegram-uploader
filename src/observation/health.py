"""Optional health checks for postgres, redis, and telegram provider."""

from __future__ import annotations

import redis

from infrastructure.bootstrap import build_storage_provider
from infrastructure.config import load_config
from infrastructure.db.migrate import apply_migrations


def check_postgres(dsn: str) -> bool:
    try:
        apply_migrations(dsn)
        return True
    except Exception:
        return False


def check_redis(url: str) -> bool:
    try:
        client = redis.Redis.from_url(url, decode_responses=False)
        client.ping()
        return True
    except Exception:
        return False


def check_telegram() -> bool:
    cfg = load_config()
    if not cfg.telegram_target_chat_id:
        return False
    provider = build_storage_provider(cfg)
    return provider.healthcheck()


def main() -> int:
    cfg = load_config()
    checks = {
        "postgres": check_postgres(cfg.postgres_dsn),
        "redis": check_redis(cfg.redis_url),
        "telegram": check_telegram(),
    }
    for name, ok in checks.items():
        print(f"{name}: {'ok' if ok else 'fail'}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
