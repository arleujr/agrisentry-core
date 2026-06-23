import pytest
import uuid
from datetime import datetime, timedelta
from services.detector.context import ContextValidator
from models.schemas import ActuatorLog


@pytest.mark.asyncio
async def test_context_validator_no_activity(db_session):
    sensor_id = uuid.uuid4()
    now = datetime.utcnow()
    has_ctx, note = await ContextValidator.has_correlating_activity(db_session, sensor_id, now)
    assert not has_ctx
    assert "No correlating actuator activity found" in note


@pytest.mark.asyncio
async def test_context_validator_with_active_actuator(db_session):
    sensor_id = uuid.uuid4()
    now = datetime.utcnow()

    actuator_log = ActuatorLog(
        id=uuid.uuid4(),
        actuator_name="Exhaust Fan Delta",
        sensor_environment_id=sensor_id,
        status="ACTIVE",
        timestamp=now - timedelta(minutes=2),
    )
    db_session.add(actuator_log)
    await db_session.commit()

    has_ctx, note = await ContextValidator.has_correlating_activity(db_session, sensor_id, now)
    assert has_ctx
    assert "Context match" in note
    assert "Exhaust Fan Delta" in note
