from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

@dataclass(frozen=True)
class DbConfig:
    """Immutable database connection parameters for a single MySQL database.

    Attributes:
        host: MySQL server hostname or IP address.
        port: MySQL port number as a string (e.g. ``"3306"``).
        user: MySQL username.
        password: MySQL password.
        db_name: Name of the target database schema.
    """

    host: str
    port: str
    user: str
    password: str
    db_name: str

    def connection_string(self) -> str:
        """Build a SQLAlchemy-compatible MySQL connection URI.

        Returns:
            A ``mysql+pymysql://`` URI string with credentials and database name
            embedded, ready to pass to ``create_engine``.
        """
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"


def create_engine_for(cfg: DbConfig, *, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine with connection-pool settings tuned for MySQL.

    Uses ``pool_pre_ping`` to discard stale connections and ``pool_recycle``
    to stay within MySQL's default ``wait_timeout`` of 28 800 s.

    Args:
        cfg: Database connection parameters.
        echo: If ``True``, SQLAlchemy logs all SQL statements. Defaults to ``False``.

    Returns:
        A configured SQLAlchemy ``Engine`` instance.
    """
    return create_engine(
        cfg.connection_string(),
        echo=echo,
        pool_pre_ping=True,   # detect stale connections before use
        pool_recycle=1800,    # recycle connections every 30 min (before MySQL wait_timeout)
        pool_timeout=10,      # raise after 10s if no connection available
        future=True,
    )

