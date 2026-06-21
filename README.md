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
    D -->|Pydantic Schema Validation| M[Silver Layer Buffering]
    M -->|Z-Score Math| E[Statistical Filter]
    E -->|Anomaly Detected| F[Context Validator]
    F -->|Pump Active?| G[Overrule Anomaly]
    F -->|No Context| H[Flag as Noise / Destructive Drift]
    E -->|Valid| I[Mark as VALID]
    G --> I
    I --> C
    H --> C
    L -->|JSON Response| B

```

## Medallion Architecture & Data Quality Guardrails

This service replicates defensive **Medallion Architecture principles** to shield downstream systems from bad field data and unannounced payload structural modifications:

* **Silver Layer Buffering & Schema Validation:** Telemetry data is parsed via strict contract layers. Additive schema modifications (new fields) are absorbed automatically with structural fallbacks. Destructive drifts (missing core metrics) throw a controlled failure.
* **Defensive Error Handling:** Every pipeline stage is isolated with granular `try/catch` wrappers. Instead of crashing the engine, malformed data blocks are isolated, safely logged via structured schemas, and flagged for pipeline SLA analysis.

## Key Architectural Decisions

* **Dual-Engine Execution Framework:** Seamlessly hosts both a high-throughput FastAPI ASGI REST instance and a decoupled, cooperative background task loop running on the standard asyncio runtime event stream.
* **Zero N+1 Query Footprint:** Utilizes SQLAlchemy Window Functions (`ROW_NUMBER() OVER`) and Single Batch Fetching to pull historical baseline data without hammering the database inside loops.
* **Race Condition Immunity:** Implements `FOR UPDATE SKIP LOCKED` to allow multiple background workers to process pending data concurrently without deadlocks or phantom reads.
* **Context-Aware AI Overrule:** Doesn't just rely on blind math. If a statistical anomaly (Z-Score > 4.0) is detected, the engine queries the physical state of the farm (e.g., "Was the water pump turned on recently?") to gracefully overrule false positives.
* **Indestructible Polling:** The background worker implements **Exponential Backoff with Jitter** to survive database downtime without causing DoS loops or connection thrashing.
* **Clock Drift Mitigation:** Validates and tracks timeline data using the `created_at` timestamp matrix to map network latency and handle physical edge hardware stability.

## Core API Contract Specification

The engine exposes dedicated endpoints designed to orchestrate low-latency classifications for downstream microservices (such as the `agrisentry-iot-gateway`).

### Telemetry Analytics Batch Evaluation

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

## Testing Strategy & Assertions

The engineering health of this application is secured by an automated validation test suite driven by `pytest` and `pytest-asyncio`.

### Dialect-Aware Test Isolation

Because production requires real-time concurrent features like `FOR UPDATE SKIP LOCKED` (native to PostgreSQL/TimescaleDB), the test suite implements a custom dialect interceptor. During automated local executions or CI/CD pipelines, the suite dynamically provision-mocks an **in-memory SQLite environment**, stripping PostgreSQL-specific keywords cleanly to guarantee high execution speeds and zero database dependency.

### Covered Test Matrix

* **Schema Evolution Testing:** Asserts that the ingestion pipeline gracefully bypasses additive unknown payloads while accurately capturing and dropping destructive missing fields.
* **Exponential Backoff Evaluation:** Validates that the background thread network timing multiplies correctly upon mock connectivity dropouts.
* **Asynchronous API Integration:** Asserts response structural consistency and low latency under mock load concurrency.

To execute the test suite locally:

```bash
pytest tests/ -v

```

---

## License

Distributed under the MIT License.
