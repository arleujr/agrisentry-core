import pytest
from datetime import datetime
from services.data_quality import AnomalyDetector
from services.detector.engine import DetectionEngine
from models.schemas import DataQualityStatus


def test_evaluate_zscore_insufficient_data():
    is_anomaly, note = AnomalyDetector.evaluate_zscore(50.0, [50.0, 51.0])
    assert not is_anomaly
    assert "Insufficient historical data" in note


def test_evaluate_zscore_static_baseline():
    history = [45.0] * 6
    is_anomaly, note = AnomalyDetector.evaluate_zscore(45.0, history)
    assert not is_anomaly
    assert "matches static historical baseline" in note

    is_anomaly, note = AnomalyDetector.evaluate_zscore(50.0, history)
    assert is_anomaly
    assert "deviates from absolute static baseline" in note


def test_detection_engine_classification():
    history = [12.0, 12.5, 11.8, 12.2, 12.1, 11.9]
    now = datetime.utcnow()

    status, _ = DetectionEngine.analyze(12.0, history, now, now)
    assert status == DataQualityStatus.VALID

    status, _ = DetectionEngine.analyze(95.0, history, now, now)
    assert status == DataQualityStatus.ANOMALY_NOISE
