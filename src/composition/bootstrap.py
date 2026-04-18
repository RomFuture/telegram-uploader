import logging
import sys

import redis

from infrastructure.config import load_config
from infrastructure.db.migrate import apply_migrations


def bootstrap() -> None:
    """Composition root: config, DB migrations, Redis connectivity."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    log = logging.getLogger("composition.bootstrap")
    cfg = load_config()
    log.info("Environment: %s", cfg.app_env)
    apply_migrations(cfg.postgres_dsn)
    log.info("Database migrations applied.")
    client = redis.Redis.from_url(cfg.redis_url, decode_responses=False)
    client.ping()
    log.info("Redis ping OK.")


if __name__ == "__main__":
    bootstrap()
