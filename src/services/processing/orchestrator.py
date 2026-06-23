import logging
from typing import List, Dict
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import SensorReading, DataQualityStatus
from services.detector.engine import DetectionEngine
from services.detector.context import ContextValidator

logger = logging.getLogger(__name__)


class DataOrchestrator:
    """
    Enterprise-grade Orchestrator for asynchronous data quality validation.
    Optimized for zero N+1 query footprint via SQLAlchemy Window Functions.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def run_pipeline(self, batch_size: int = 50) -> int:
        # Fetch PENDING records with horizontal scaling protection (SKIP LOCKED)
        stmt = (
            select(SensorReading)
            .where(SensorReading.status == DataQualityStatus.PENDING)
            .with_for_update(skip_locked=True)
            .limit(batch_size)
        )

        result = await self.session.execute(stmt)
        readings = result.scalars().all()

        if not readings:
            return 0

        # Extract unique sensor IDs to restrict the CTE scan scope
        sensor_ids = list({r.sensor_id for r in readings})

        # Single Batch Fetch: Window Function to map the last 20 VALID readings per sensor
        # Fixed column mapping to use 'created_at' to prevent database schema mismatch
        subq = (
            select(
                SensorReading.sensor_id,
                SensorReading.value,
                func.row_number()
                .over(
                    partition_by=SensorReading.sensor_id, order_by=SensorReading.created_at.desc()
                )
                .label("rn"),
            )
            .where(
                SensorReading.sensor_id.in_(sensor_ids),
                SensorReading.status == DataQualityStatus.VALID,
            )
            .subquery()
        )

        hist_stmt = select(subq.c.sensor_id, subq.c.value).where(subq.c.rn <= 20)
        hist_result = await self.session.execute(hist_stmt)

        # Build memory map (O(1) access)
        history_map: Dict[UUID, List[float]] = {sid: [] for sid in sensor_ids}
        for row in hist_result.all():
            history_map[row.sensor_id].append(row.value)

        # Process entirely in memory (Zero DB roundtrips)
        for reading in readings:
            baseline = history_map.get(reading.sensor_id, [])

            # Cross-checking timelines safely using created_at stamps
            status, note = DetectionEngine.analyze(
                reading_value=reading.value,
                baseline_values=baseline,
                device_timestamp=reading.created_at,
                ingestion_timestamp=reading.created_at,
            )

            # Physical context validation overrule
            if status == DataQualityStatus.ANOMALY_NOISE:
                has_context, ctx_note = await ContextValidator.has_correlating_activity(
                    self.session, reading.sensor_id, reading.created_at
                )
                if has_context:
                    status = DataQualityStatus.VALID
                    note = f"Context Validated Override: {ctx_note} | Orig: {note}"

            reading.status = status
            reading.ai_analysis_note = note

        await self.session.commit()
        logger.debug(f"Batch processed successfully: {len(readings)} rows.")
        return len(readings)
