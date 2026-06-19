import asyncio
import logging
import sys
import uvicorn
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from core.database import engine
from services.worker import start_data_worker

from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

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

# ----------------------------------------------------------------------
# 📦 Pydantic Schemas for strong typing
# ----------------------------------------------------------------------
class TelemetryItem(BaseModel):
    id: uuid.UUID
    value: float
    created_at: datetime

class AnalysisRequest(BaseModel):
    readings: List[TelemetryItem]

class AnalysisResultItem(BaseModel):
    id: uuid.UUID
    created_at: datetime
    status: str       # 'VALID', 'ANOMALY_NOISE', 'ANOMALY_CRITICAL'
    note: str

class AnalysisResponse(BaseModel):
    results: List[AnalysisResultItem]

# ----------------------------------------------------------------------
# 🌐 Routes
# ----------------------------------------------------------------------
@app.get("/")
async def root_redirect():
    return {"message": "AgriSentry Core API is running. Head over to /health for status check."}

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Liveness and Readiness probe endpoint for infrastructure monitoring (K8s/AWS).
    Verifies API availability and underlying database pool connectivity.
    """
    try:
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

@app.post("/v1/analyze", response_model=AnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_telemetry_batch(payload: AnalysisRequest):
    """
    Receives a batch of telemetry readings from the Rust Gateway,
    runs anomaly detection logic (ML model or rules),
    and returns classification results.
    """
    logger.info(f"🧠 Received batch of {len(payload.readings)} readings for AI analysis.")
    
    analysis_results = []
    for item in payload.readings:
        # ------------------------------------------------------------------
        # 🔮 Here you plug in your ML model (XGBoost, Isolation Forest, etc.)
        # Example: prediction = model.predict([[item.value]])[0]
        # ------------------------------------------------------------------
        
        # Simulated anomaly detection logic
        if item.value > 90.0:
            status_classification = "ANOMALY_CRITICAL"
            ai_note = "AI detected critical anomaly: Value exceeded operational safety threshold."
        elif item.value < 5.0:
            status_classification = "ANOMALY_NOISE"
            ai_note = "AI detected noise: Sudden drop inconsistent with sensor behavior."
        else:
            status_classification = "VALID"
            ai_note = "AI validated data: Reading within normal statistical range."

        analysis_results.append(
            AnalysisResultItem(
                id=item.id,
                created_at=item.created_at,
                status=status_classification,
                note=ai_note
            )
        )
        
    return AnalysisResponse(results=analysis_results)

# ----------------------------------------------------------------------
# ⚙️ Startup Event
# ----------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """
    Fires the background Data Quality Worker task loop
    when the FastAPI server starts.
    """
    logger.info("Starting background Data Quality Worker pipeline...")
    asyncio.create_task(start_data_worker(batch_size=50))

if __name__ == "__main__":
    # Runs the server engine on default port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
