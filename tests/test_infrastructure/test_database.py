# tests/test_infrastructure/test_database.py
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from csqaq.infrastructure.database.connection import Database
from csqaq.infrastructure.database.models import Alert, Base, PriceSnapshot, Watchlist


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_database_converts_sqlite_url():
    """Database class should auto-convert sqlite:/// to sqlite+aiosqlite:///."""
    db = Database("sqlite:///data/test.db")
    # Verify it doesn't crash and the engine URL was converted
    assert "aiosqlite" in str(db._engine.url)
    await db.close()


@pytest.mark.asyncio
async def test_database_init_creates_tables():
    """Database.init() should create all tables."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    async with db.session() as session:
        # Should not raise — tables exist
        result = await session.execute(select(Watchlist))
        assert result.all() == []
    await db.close()


@pytest.mark.asyncio
async def test_create_watchlist_item(db_session: AsyncSession):
    item = Watchlist(good_id=7310, name="AK-47 | 红线", market_hash_name="AK-47 | Redline (FT)")
    db_session.add(item)
    await db_session.commit()

    result = await db_session.execute(select(Watchlist).where(Watchlist.good_id == 7310))
    row = result.scalar_one()
    assert row.name == "AK-47 | 红线"
    assert row.alert_threshold_pct == 5.0  # default


@pytest.mark.asyncio
async def test_create_price_snapshot(db_session: AsyncSession):
    snap = PriceSnapshot(
        good_id=7310,
        buff_sell=85.5,
        buff_buy=82.0,
        steam_sell=12.35,
        yyyp_sell=80.0,
        sell_num=15234,
        buy_num=8921,
    )
    db_session.add(snap)
    await db_session.commit()

    result = await db_session.execute(select(PriceSnapshot).where(PriceSnapshot.good_id == 7310))
    row = result.scalar_one()
    assert row.buff_sell == 85.5


@pytest.mark.asyncio
async def test_create_alert(db_session: AsyncSession):
    alert = Alert(
        alert_type="price_change",
        good_id=7310,
        title="AK红线涨幅异常",
        message="日涨幅 8.5%，超过阈值 5%",
        data_snapshot={"price": 85.5, "change": 8.5},
    )
    db_session.add(alert)
    await db_session.commit()

    result = await db_session.execute(select(Alert))
    row = result.scalar_one()
    assert row.alert_type == "price_change"
    assert row.acknowledged is False
