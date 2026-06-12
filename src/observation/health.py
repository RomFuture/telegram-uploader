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


def check_telegram(target_chat_id: str) -> bool:
    if not target_chat_id:
        return False
    cfg = load_config()
    provider = build_storage_provider(cfg)
    return provider.healthcheck(target_chat_id)


def main() -> int:
    cfg = load_config()
    checks = {
        "postgres": check_postgres(cfg.postgres_dsn),
        "redis": check_redis(cfg.redis_url),
        "telegram": check_telegram(cfg.telegram_target_chat_id),
    }
    for name, ok in checks.items():
        print(f"{name}: {'ok' if ok else 'fail'}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
