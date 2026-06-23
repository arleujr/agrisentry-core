import pytest
import uuid
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_root_redirect():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert "AgriSentry Core API is running" in response.json()["message"]


@pytest.mark.asyncio
async def test_health_check_healthy():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "connected"}


@pytest.mark.asyncio
async def test_analyze_telemetry_batch():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        payload = {
            "readings": [
                {
                    "id": str(uuid.uuid4()),
                    "value": 25.5,
                    "created_at": datetime.utcnow().isoformat(),
                },
                {
                    "id": str(uuid.uuid4()),
                    "value": 95.0,
                    "created_at": datetime.utcnow().isoformat(),
                },
                {
                    "id": str(uuid.uuid4()),
                    "value": 2.0,
                    "created_at": datetime.utcnow().isoformat(),
                },
            ]
        }
        response = await ac.post("/v1/analyze", json=payload)

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3
    assert results[0]["status"] == "VALID"
    assert results[1]["status"] == "ANOMALY_CRITICAL"
    assert results[2]["status"] == "ANOMALY_NOISE"
