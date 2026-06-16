import asyncio
import logging
import sys
import uvicorn
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from core.database import engine
from services.worker import start_data_worker

# Enterprise Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Server] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AgriSentry Core API",
    description="Central AI & Data Quality engine handling telemetry orchestration.",
    version="1.0.0"
)

# Configure CORS for dashboard integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Liveness and Readiness probe endpoint for infrastructure monitoring (K8s/AWS).
    Verifies API availability and underlying database pool connectivity.
    """
    try:
        # Optimistically check if database pool can execute a primitive command
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed due to database friction: {e}")
        return Response(
            content='{"status": "unhealthy", "database": "disconnected"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )

@app.on_event("startup")
async def startup_event():
    """
    Asynchronously fires the background Data Quality Worker task loop
    on a separate thread context when the FastAPI server ignites.
    """
    logger.info("Starting background Data Quality Worker pipeline...")
    asyncio.create_task(start_data_worker(batch_size=50))

if __name__ == "__main__":
    # Runs the server engine on default port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
