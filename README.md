# AgriSentry Core (AI & Data Quality Engine)

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-Async-red.svg)
![Pytest](https://img.shields.io/badge/Pytest-Passing-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green)

Enterprise-grade asynchronous data processing engine and AI inference server for the AgriSentry IoT ecosystem. This microservice operates dual lifecycles: it acts as a high-performance REST API for synchronous batch evaluation, while concurrently running an indestructible background loop validating telemetry streams directly against physical contexts and statistical baselines.

## System Architecture

```mermaid
graph LR
    A[Edge Sensors] -->|MQTT| B(Rust Gateway)
    B -->|Ingestion| C[(PostgreSQL / TimescaleDB)]
    C -->|SKIP LOCKED Fetch| D{AgriSentry Core Worker}
    B -->|HTTP Batch Post| K[FastAPI API Engine]
    K -->|Simulated AI Inference| L[Rule/Threshold Matrix]
    D -->|Z-Score Math| E[Statistical Filter]
    E -->|Anomaly Detected| F[Context Validator]
    F -->|Pump Active?| G[Overrule Anomaly]
    F -->|No Context| H[Flag as Noise]
    E -->|Valid| I[Mark as VALID]
    G --> I
    I --> C
    H --> C
    L -->|JSON Response| B

```

## Key Architectural Decisions (Senior-Level Features)

* **Dual-Engine Execution Framework:** Seamlessly hosts both a high-throughput FastAPI ASGI REST instance and a decoupled, cooperative background task loop running on the standard asyncio runtime event stream.
* **Zero N+1 Query Footprint:** Utilizes SQLAlchemy Window Functions (`ROW_NUMBER() OVER`) and Single Batch Fetching to pull historical baseline data without hammering the database inside loops.
* **Race Condition Immunity:** Implements `FOR UPDATE SKIP LOCKED` to allow multiple background workers to process pending data concurrently without deadlocks or phantom reads.
* **Context-Aware AI Overrule:** Doesn't just rely on blind math. If a statistical anomaly (Z-Score > 4.0) is detected, the engine queries the physical state of the farm (e.g., "Was the water pump turned on recently?") to gracefully overrule false positives.
* **Indestructible Polling:** The background worker implements **Exponential Backoff with Jitter** to survive database downtime without causing DoS loops or connection thrashing.
* **Clock Drift Mitigation:** Validates and tracks timeline data using the `created_at` timestamp matrix to map network latency and handle physical edge hardware stability.

## Core API Contract Specification

The engine exposes dedicated endpoints designed to orchestrate low-latency classifications for downstream microservices (such as the `agrisentry-iot-gateway`).

### 🧠 Telemetry Analytics Batch Evaluation

* **Endpoint:** `POST /v1/analyze` (with structural fallback matching `POST /analyze`)
* **Payload Structure (`AnalysisRequest`):**

```json
{
  "readings": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "value": 94.20,
      "created_at": "2026-06-20T23:25:00Z"
    }
  ]
}

```

* **Response Framework (`AnalysisResponse`):**

```json
{
  "results": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "created_at": "2026-06-20T23:25:00Z",
      "status": "ANOMALY_CRITICAL",
      "note": "AI detected critical anomaly: Value exceeded operational safety threshold."
    }
  ]
}

```

---

## Quick Start

### 1. Environment Setup

Do not use hardcoded credentials. Copy the example environment file and configure your local settings:

```bash
cp .env.example .env

```

**`.env` reference:**

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agrisentry
WORKER_BATCH_SIZE=50
LOG_LEVEL=INFO

```

### 2. Installation (Virtual Environment)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

```

### 3. Run the Service Engine

To start the FastAPI production stack paired with the background processing worker framework:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000

```

---

## Testing Strategy

The test suite is built with `pytest` and `pytest-asyncio`. It features **Dialect-Aware logic** to handle the physical limitations of SQLite during local testing versus PostgreSQL in production.

To run the integration suite locally (uses in-memory SQLite):

```bash
pytest tests/ -v

```

---

## 📄 License

Distributed under the MIT License.

```

```
