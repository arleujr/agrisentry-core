import asyncio
import logging
from core.database import AsyncSessionLocal
from core.config import settings
from services.processing.orchestrator import DataOrchestrator

logger = logging.getLogger(__name__)

async def data_quality_worker_loop():
    logger.info("Background Worker initialized.")
    while True:
        try:
            async with AsyncSessionLocal() as session:
                orchestrator = DataOrchestrator(session)
                processed = await orchestrator.run_pipeline(settings.WORKER_BATCH_SIZE)
                
            if processed == 0:
                await asyncio.sleep(settings.WORKER_SLEEP_SECONDS)
            else:
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Worker loop fatal error: {e}")
            await asyncio.sleep(settings.WORKER_SLEEP_SECONDS)