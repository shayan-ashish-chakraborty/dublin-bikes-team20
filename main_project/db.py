from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

@dataclass(frozen=True)
class DbConfig:
    host: str
    port: str
    user: str
    password: str
    db_name: str

    def connection_string(self) -> str:
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"


def create_engine_for(cfg: DbConfig, *, echo: bool = False) -> Engine:
    return create_engine(
        cfg.connection_string(),
        echo=echo,
        pool_pre_ping=True,   # detect stale connections before use
        pool_recycle=1800,    # recycle connections every 30 min (before MySQL wait_timeout)
        pool_timeout=10,      # raise after 10s if no connection available
        future=True,
    )

