# src/csqaq/infrastructure/database/connection.py
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base


class Database:
    """Manages async SQLAlchemy engine and session factory."""

    def __init__(self, url: str):
        # Convert sqlite:/// to sqlite+aiosqlite:///
        if url.startswith("sqlite:///") and "aiosqlite" not in url:
            url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        self._engine = create_async_engine(url, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    async def init(self) -> None:
        """Create all tables."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session

    async def close(self) -> None:
        await self._engine.dispose()
