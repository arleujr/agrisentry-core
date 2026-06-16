# AgriSentry Core (AI & Data Quality Engine)

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-Async-red.svg)
![Pytest](https://img.shields.io/badge/Pytest-Passing-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green)


Enterprise-grade asynchronous data processing engine for the AgriSentry IoT ecosystem. This microservice is responsible for validating, cleaning, and contextually analyzing high-throughput agricultural telemetry data using statistical models and physical context validation.

## System Architecture

```mermaid
graph LR
    A[Edge Sensors] -->|MQTT| B(Rust Gateway)
    B -->|Ingestion| C[(PostgreSQL / TimescaleDB)]
    C -->|SKIP LOCKED Fetch| D{AgriSentry Core}
    D -->|Z-Score Math| E[Statistical Filter]
    E -->|Anomaly Detected| F[Context Validator]
    F -->|Pump Active?| G[Overrule Anomaly]
    F -->|No Context| H[Flag as Noise]
    E -->|Valid| I[Mark as VALID]
    G --> I
    I --> C
    H --> C
```

## Key Architectural Decisions (Senior-Level Features)

* **Zero N+1 Query Footprint:** Utilizes SQLAlchemy Window Functions (`ROW_NUMBER() OVER`) and Single Batch Fetching to pull historical baseline data without hammering the database inside loops.
* **Race Condition Immunity:** Implements `FOR UPDATE SKIP LOCKED` to allow multiple background workers to process pending data concurrently without deadlocks or phantom reads.
* **Context-Aware AI Overrule:** Doesn't just rely on blind math. If a statistical anomaly (Z-Score > 4.0) is detected, the engine queries the physical state of the farm (e.g., "Was the water pump turned on recently?") to gracefully overrule false positives.
* **Indestructible Polling:** The background worker implements **Exponential Backoff with Jitter** to survive database downtime without causing DoS loops.
* **Clock Drift Mitigation:** Validates and tracks timeline data using the `created_at` timestamp matrix to map network latency and handle physical edge hardware stability.

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

### 3. Run the AI Worker

```bash
python src/main.py
```

## Testing Strategy

The test suite is built with `pytest` and `pytest-asyncio`. It features **Dialect-Aware logic** to handle the physical limitations of SQLite during local testing versus PostgreSQL in production.

To run the integration suite locally (uses in-memory SQLite):

```bash
pytest tests/ -v
```
