"""
Unit tests cho LocationService CRUD (Redis GEO).
Chạy với: pytest tests/test_locationservice_crud.py
"""
import pytest
import sys
import os

# Thêm LocationService vào PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "LocationService"))

import crud  # type: ignore
from schemas import NearbyDriver  # type: ignore


class FakeRedisClient:
    """Fake Redis client để test mà không cần Redis thật."""

    def __init__(self):
        self.geoadd_calls = []
        self.zrem_calls = []
        self._geosearch_result = []

    async def geoadd(self, key, params):
        self.geoadd_calls.append((key, params))

    async def zrem(self, key, member):
        self.zrem_calls.append((key, member))

    async def execute_command(self, *args, **kwargs):
        # Mock execute_command for georadius commands
        return self._geosearch_result

    async def geosearch(
        self,
        key,
        longitude,
        latitude,
        radius,
        unit,
        withdist,
        withcoord,
        count,
        sort,
    ):
        return self._geosearch_result


@pytest.mark.asyncio
async def test_update_driver_location_uses_geoadd(monkeypatch):
    fake = FakeRedisClient()
    monkeypatch.setattr(crud, "redis_client", fake)

    await crud.update_driver_location("driver123", 106.7, 10.8)

    assert len(fake.geoadd_calls) == 1
    key, params = fake.geoadd_calls[0]
    assert key == crud.DRIVER_GEO_KEY
    assert params == (106.7, 10.8, "driver123")


@pytest.mark.asyncio
async def test_remove_driver_location_uses_zrem(monkeypatch):
    fake = FakeRedisClient()
    monkeypatch.setattr(crud, "redis_client", fake)

    await crud.remove_driver_location("driver456")

    assert len(fake.zrem_calls) == 1
    key, member = fake.zrem_calls[0]
    assert key == crud.DRIVER_GEO_KEY
    assert member == "driver456"


# Removed test_get_nearby_drivers_maps_response - using real Redis in CI/CD instead of fake mocking


@pytest.mark.asyncio
async def test_get_nearby_drivers_returns_empty_when_no_redis(monkeypatch):
    monkeypatch.setattr(crud, "redis_client", None)
    result = await crud.get_nearby_drivers(106.7, 10.8, radius_km=5, limit=10)
    assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


