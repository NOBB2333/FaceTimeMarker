from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def sqlite_url_from_path(path: Path) -> str:
    """把本地数据库路径转换为 SQLAlchemy URL。"""
    return f"sqlite:///{path.expanduser().resolve()}"


def make_engine(path: Path, url: str | None = None) -> Engine:
    """创建数据库引擎，默认使用本地 SQLite，允许切换到 PostgreSQL 等 URL。"""
    database_url = url.strip() if url is not None and url.strip() else sqlite_url_from_path(path)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """创建 ORM Session 工厂。"""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """提供带提交/回滚语义的 Session 上下文。"""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
