import asyncio
import pytest
from csqaq.infrastructure.cache.memory_cache import MemoryCache


@pytest.mark.asyncio
async def test_get_returns_none_for_missing_key():
    cache = MemoryCache()
    assert await cache.get("nonexistent") is None


@pytest.mark.asyncio
async def test_set_and_get():
    cache = MemoryCache()
    await cache.set("key1", {"price": 85.5}, ttl=60)
    result = await cache.get("key1")
    assert result == {"price": 85.5}


@pytest.mark.asyncio
async def test_ttl_expiry():
    cache = MemoryCache()
    await cache.set("key1", "value", ttl=0)  # expires immediately
    await asyncio.sleep(0.01)
    assert await cache.get("key1") is None


@pytest.mark.asyncio
async def test_delete():
    cache = MemoryCache()
    await cache.set("key1", "value", ttl=60)
    await cache.delete("key1")
    assert await cache.get("key1") is None
