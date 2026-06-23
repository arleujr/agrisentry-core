import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from services.worker import start_data_worker


@pytest.mark.asyncio
async def test_start_data_worker_polling_loop():
    with patch(
        "services.processing.orchestrator.DataOrchestrator.run_pipeline", new_callable=AsyncMock
    ) as mock_pipeline:
        mock_pipeline.return_value = 0

        try:
            await asyncio.wait_for(start_data_worker(batch_size=10), timeout=0.2)
        except asyncio.TimeoutError:
            pass  # Gracefully interrupted the worker's infinite polling loop

        assert mock_pipeline.called
