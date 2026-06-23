import logging
from typing import Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from models.schemas import ActuatorLog

# Mock import - Assume you have an ActuatorLog model defined in schemas
from models.schemas import ActuatorLog

logger = logging.getLogger(__name__)


class ContextValidator:
    """
    Validates if physical sensor spikes match with actuator state transitions.
    Prevents false positives during normal machine operation.
    """

    @staticmethod
    async def has_correlating_activity(
        session: AsyncSession, sensor_id: UUID, timestamp: datetime
    ) -> Tuple[bool, str]:
        """
        Checks if an actuator was active within a 5-minute window preceding the reading.
        """
        window_start = timestamp - timedelta(minutes=5)

        # Query logs for active actuators associated with the environment
        stmt = select(ActuatorLog).where(
            and_(
                ActuatorLog.timestamp >= window_start,
                ActuatorLog.timestamp <= timestamp,
                ActuatorLog.status == "ACTIVE",
            )
        )

        result = await session.execute(stmt)
        activity = result.scalars().first()

        if activity:
            return True, f"Context match: {activity.actuator_name} was active within 5m window."

        return False, "No correlating actuator activity found."
