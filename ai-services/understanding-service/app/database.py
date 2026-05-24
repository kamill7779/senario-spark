from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class MySQLConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


def mysql_config_from_env() -> MySQLConfig:
    dsn = os.environ.get("MYSQL_DSN")
    if dsn:
        parsed = urlparse(dsn)
        if parsed.scheme not in {"mysql", "mysql+pymysql"}:
            raise ValueError("MYSQL_DSN must use mysql:// or mysql+pymysql://")
        database = parsed.path.lstrip("/")
        if not database:
            raise ValueError("MYSQL_DSN must include a database name")
        return MySQLConfig(
            host=parsed.hostname or "127.0.0.1",
            port=parsed.port or 3306,
            user=unquote(parsed.username or ""),
            password=unquote(parsed.password or ""),
            database=unquote(database),
        )
    database = os.environ.get("MYSQL_DATABASE")
    if not database:
        raise ValueError("MYSQL_DSN or MYSQL_DATABASE is required")
    return MySQLConfig(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=database,
    )


def connect_mysql(config: MySQLConfig | None = None):
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError as exc:
        raise RuntimeError("PyMySQL is required. Install requirements.txt first.") from exc

    config = config or mysql_config_from_env()
    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )
