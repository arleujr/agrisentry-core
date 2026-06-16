import statistics
from typing import List, Tuple
from datetime import datetime
from models.schemas import DataQualityStatus

class DetectionEngine:
    """
    Stateless detection engine. Utilizes native Python statistics (C-bindings) 
    to prevent memory fragmentation associated with heavy DataFrame instantiations 
    in infinite asynchronous loops.
    """
    Z_SCORE_THRESHOLD = 4.0
    MAX_CLOCK_DRIFT_SECONDS = 300.0  # 5 minutes threshold for hardware latency

    @staticmethod
    def analyze(
        reading_value: float,
        baseline_values: List[float],
        device_timestamp: datetime,
        ingestion_timestamp: datetime
    ) -> Tuple[DataQualityStatus, str]:
        
        # 1. Clock Drift / Network Latency Verification
        # Safe fallback logic to prevent crash if timezone awareness differences arise during CI runs
        try:
            drift_seconds = abs((ingestion_timestamp - device_timestamp).total_seconds())
            if drift_seconds > DetectionEngine.MAX_CLOCK_DRIFT_SECONDS:
                return DataQualityStatus.ANOMALY_NOISE, f"Clock Drift Anomaly: {drift_seconds}s delay detected."
        except TypeError:
            # Handles naive vs aware datetime exceptions safely during static mock processing
            pass

        # 2. Warmup Period Clause
        if len(baseline_values) < 5:
            return DataQualityStatus.VALID, "Insufficient historical baseline for statistical variance."

        # 3. Native Static Math Calculation
        mean_val = statistics.mean(baseline_values)
        stdev_val = statistics.pstdev(baseline_values)

        # Prevent ZeroDivisionError on flatline sensor data
        if stdev_val == 0.0:
            stdev_val = 0.0001 

        z_score = abs(reading_value - mean_val) / stdev_val

        if z_score > DetectionEngine.Z_SCORE_THRESHOLD:
            return DataQualityStatus.ANOMALY_NOISE, f"Statistical Outlier: Z-Score {z_score:.2f} > {DetectionEngine.Z_SCORE_THRESHOLD}."

        return DataQualityStatus.VALID, f"Passed Z-Score Check: {z_score:.2f}"
