import asyncio
import logging
import random
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from services.processing.orchestrator import DataOrchestrator
from db.database import engine  # Assuming standard path for async_engine

logger = logging.getLogger(__name__)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def start_data_worker(batch_size: int = 50):
    """
    Indestructible infinite polling loop. Implements Exponential Backoff 
    with Jitter to gracefully survive TimescaleDB/PostgreSQL downtime 
    without causing DoS via connection thrashing.
    """
    BASE_DELAY = 1.0
    MAX_DELAY = 60.0
    current_delay = BASE_DELAY

    logger.info("Initializing Enterprise Data Quality Worker...")

    while True:
        try:
            async with AsyncSessionLocal() as session:
                orchestrator = DataOrchestrator(session)
                processed_count = await orchestrator.run_pipeline(batch_size=batch_size)
                
                if processed_count > 0:
                    # Healthy state: reset backoff and process immediately
                    current_delay = BASE_DELAY
                else:
                    # Idle state: brief pause to prevent CPU pegging
                    await asyncio.sleep(0.5)

        except SQLAlchemyError as db_err:
            # Network/DB Failure state: Apply Exponential Backoff with Jitter
            jitter = random.uniform(0.1, 1.0)
            sleep_time = current_delay + jitter
            
            logger.error(f"Database connectivity lost: {db_err}. Backing off for {sleep_time:.2f}s")
            
            await asyncio.sleep(sleep_time)
            
            # Increment delay exponentially, capped at MAX_DELAY
            current_delay = min(current_delay * 2, MAX_DELAY)
            
        except Exception as critical_err:
            # Catch-all for application panics to keep container alive
            logger.critical(f"Unhandled Worker Panic: {critical_err}")
            await asyncio.sleep(MAX_DELAY)