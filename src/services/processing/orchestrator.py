import logging
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models.schemas import SensorReading, DataQualityStatus
from services.detector.engine import AnomalyDetector
from services.detector.context import ContextValidator

logger = logging.getLogger(__name__)

class DataOrchestrator:
    """
    Orchestrates the ingestion, anomaly detection, and context validation pipeline.
    Ensures thread-safe batch processing using PostgreSQL SKIP LOCKED.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def run_pipeline(self, batch_size: int = 100) -> int:
        """
        Executes the processing pipeline:
        1. Fetches a batch of PENDING records with SKIP LOCKED.
        2. Applies statistical Z-Score analysis.
        3. Validates against actuator context (if anomaly detected).
        4. Performs bulk status updates.
        """
        # 1. Fetch pending records and lock them for this specific worker instance
        stmt = (
            select(SensorReading)
            .where(SensorReading.status == DataQualityStatus.PENDING)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        
        result = await self.session.execute(stmt)
        readings = result.scalars().all()

        if not readings:
            return 0

        logger.info(f"Orchestrator starting analysis on {len(readings)} records.")

        for reading in readings:
            # 2. Fetch baseline history (last 20 valid readings for this sensor)
            history_stmt = (
                select(SensorReading.value)
                .where(
                    SensorReading.sensor_id == reading.sensor_id,
                    SensorReading.status == DataQualityStatus.VALID,
                    SensorReading.created_at < reading.created_at
                )
                .order_by(SensorReading.created_at.desc())
                .limit(20)
            )
            history_res = await self.session.execute(history_stmt)
            history = history_res.scalars().all()

            # 3. Statistical Analysis (Z-Score)
            is_anomaly, note = AnomalyDetector.calculate_zscore_analysis(
                reading.value, history
            )

            # 4. Contextual Validation (Cross-referencing actuators)
            if is_anomaly:
                context_match, context_note = await ContextValidator.has_correlating_activity(
                    self.session, reading.sensor_id, reading.created_at
                )
                
                if context_match:
                    # Anomaly overruled by valid actuator activity
                    reading.status = DataQualityStatus.VALID
                    reading.ai_analysis_note = f"Context validated: {context_note}"
                else:
                    # Confirming noise
                    reading.status = DataQualityStatus.ANOMALY_NOISE
                    reading.ai_analysis_note = f"Anomaly confirmed: {note}"
            else:
                # Normal reading
                reading.status = DataQualityStatus.VALID
                reading.ai_analysis_note = note

        # 5. Bulk commit to release locks and update DB state
        await self.session.commit()
        return len(readings)