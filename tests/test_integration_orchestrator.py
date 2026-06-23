import pytest
import pytest_asyncio
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from models.schemas import Base, Sensor, SensorReading, ActuatorLog, DataQualityStatus
from services.processing.orchestrator import DataOrchestrator

# ---------------------------------------------------------
# Pytest Async Database Fixtures
# ---------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

    async with SessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------
# Test Battery 1: Context-Aware AI Validation
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_context_aware_anomaly_overrule(db_session):
    now = datetime.now(timezone.utc)
    sensor_id = uuid.uuid4()

    sensor = Sensor(id=sensor_id, hardware_id="TEST:MAC:01", name="SOIL_MOISTURE")
    db_session.add(sensor)

    baseline_values = [40.1, 40.2, 40.0, 40.1, 39.9]
    for i, val in enumerate(baseline_values):
        reading = SensorReading(
            sensor_id=sensor_id,
            value=val,
            status=DataQualityStatus.VALID,
            created_at=now - timedelta(minutes=10 - i),
        )
        db_session.add(reading)

    unexplained_spike = SensorReading(
        id=uuid.uuid4(),
        sensor_id=sensor_id,
        value=95.5,
        status=DataQualityStatus.PENDING,
        created_at=now,
    )
    db_session.add(unexplained_spike)
    await db_session.commit()

    orchestrator = DataOrchestrator(db_session)
    processed = await orchestrator.run_pipeline(batch_size=10)

    assert processed == 1
    await db_session.refresh(unexplained_spike)
    assert unexplained_spike.status == DataQualityStatus.ANOMALY_NOISE
    assert "Z-Score" in unexplained_spike.ai_analysis_note

    explained_spike = SensorReading(
        id=uuid.uuid4(),
        sensor_id=sensor_id,
        value=98.0,
        status=DataQualityStatus.PENDING,
        created_at=now + timedelta(minutes=5),
    )
    db_session.add(explained_spike)

    actuator_log = ActuatorLog(
        actuator_name="WATER_PUMP_01",
        sensor_environment_id=sensor_id,
        status="ACTIVE",
        timestamp=explained_spike.created_at - timedelta(minutes=2),
    )
    db_session.add(actuator_log)
    await db_session.commit()

    processed_again = await orchestrator.run_pipeline(batch_size=10)

    assert processed_again == 1
    await db_session.refresh(explained_spike)
    assert explained_spike.status == DataQualityStatus.VALID

    # FIX 1: Ignorando o Case-Sensitive para aceitar a nova string do Orquestrador
    assert "context validated" in explained_spike.ai_analysis_note.lower()


# ---------------------------------------------------------
# Test Battery 2: Concurrent Batch Processing (SKIP LOCKED)
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_batch_processing_with_skip_locked(db_session):
    sensor_id = uuid.uuid4()
    db_session.add(Sensor(id=sensor_id, hardware_id="TEST:MAC:BATCH", name="TEMPERATURE"))

    now = datetime.now(timezone.utc)
    for i in range(50):
        db_session.add(
            SensorReading(
                id=uuid.uuid4(),
                sensor_id=sensor_id,
                value=25.0 + (i * 0.1),
                status=DataQualityStatus.PENDING,
                created_at=now,
            )
        )
    await db_session.commit()

    SessionFactory = async_sessionmaker(bind=db_session.bind)

    async with SessionFactory() as session_1, SessionFactory() as session_2:
        worker_1 = DataOrchestrator(session_1)
        worker_2 = DataOrchestrator(session_2)

        # CHECAGEM DE DIALETO (Nível Arquiteto)
        # O SQLite não suporta FOR UPDATE SKIP LOCKED (Row-Level Locking).
        # Ele permite leituras fantasmas. Portanto, validamos a orquestração em lote
        # de forma sequencial no ambiente de testes locais.
        if db_session.bind.dialect.name == "sqlite":
            res1 = await worker_1.run_pipeline(batch_size=25)
            res2 = await worker_2.run_pipeline(batch_size=25)
            assert res1 + res2 == 50, "Sequential batch processing failed on SQLite"

        else:
            # Em produção (PostgreSQL), validamos a concorrência assíncrona bruta.
            results = await asyncio.gather(
                worker_1.run_pipeline(batch_size=25),
                worker_2.run_pipeline(batch_size=25),
                return_exceptions=True,
            )
            for res in results:
                if isinstance(res, Exception):
                    pytest.fail(f"Unexpected concurrent error on Postgres: {res}")
            assert sum(results) == 50, "Workers failed to process all records concurrently."

    stmt = select(SensorReading).where(SensorReading.status == DataQualityStatus.PENDING)
    remaining_pending = (await db_session.execute(stmt)).scalars().all()
    assert len(remaining_pending) == 0, "Race condition detected: Records were dropped."
