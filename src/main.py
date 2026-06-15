import asyncio
import logging
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core.database import get_db_session
from services.worker import data_quality_worker_loop

# Professional JSON-friendly logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("AgriPlanumCore")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Control Plane and Data Quality AI Engine for Agricultural Telemetry."
)

# Reference to store the background task
worker_task = None

@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 Starting {settings.PROJECT_NAME}...")
    global worker_task
    # Fire and forget the background worker
    worker_task = asyncio.create_task(data_quality_worker_loop())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API. Cancelling background workers...")
    if worker_task:
        worker_task.cancel()

@app.get("/health", tags=["Monitoring"])
async def healthcheck(db: AsyncSession = Depends(get_db_session)):
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "version": settings.VERSION,
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Healthcheck failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")

if __name__ == "__main__":
    import uvicorn
    # Inicia o servidor travando o terminal para vermos os logs
    uvicorn.run(app, host="0.0.0.0", port=8000)