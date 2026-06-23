import pytest
import uuid
from datetime import datetime, timedelta
from services.processing.orchestrator import DataOrchestrator
from models.schemas import Sensor, SensorReading, DataQualityStatus


@pytest.mark.asyncio
async def test_orchestrator_empty_pipeline(db_session):
    orchestrator = DataOrchestrator(db_session)
    count = await orchestrator.run_pipeline(batch_size=10)
    assert count == 0


@pytest.mark.asyncio
async def test_orchestrator_successful_processing_flow(db_session):
    sensor_id = uuid.uuid4()
    now = datetime.utcnow()

    sensor = Sensor(id=sensor_id, hardware_id="HARDWARE-TEST-01", name="DHT22 Ground")
    db_session.add(sensor)

    seed_values = [24.0, 24.1, 23.9, 24.2, 24.0, 24.1, 23.8, 24.3, 24.0, 24.1]
    for i in range(10):
        reading = SensorReading(
            id=uuid.uuid4(),
            value=seed_values[i],
            sensor_id=sensor_id,
            status=DataQualityStatus.VALID,
            created_at=now - timedelta(minutes=15 - i),
        )
        db_session.add(reading)

    pending_reading = SensorReading(
        id=uuid.uuid4(),
        value=24.2,
        sensor_id=sensor_id,
        status=DataQualityStatus.PENDING,
        created_at=now,
    )
    db_session.add(pending_reading)
    await db_session.commit()

    orchestrator = DataOrchestrator(db_session)
    processed_count = await orchestrator.run_pipeline(batch_size=5)

    assert processed_count[0] == 1 if isinstance(processed_count, tuple) else processed_count == 1
    await db_session.refresh(pending_reading)
    assert pending_reading.status == DataQualityStatus.VALID
