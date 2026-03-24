# tests/test_api/test_health.py
import pytest


class TestHealthEndpoint:
    async def test_health_returns_200(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_health_includes_version(self, client):
        response = await client.get("/api/v1/health")
        data = response.json()
        assert "version" in data
