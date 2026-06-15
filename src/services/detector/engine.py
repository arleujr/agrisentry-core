import logging
import pandas as pd
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from models.schemas import DataQualityStatus

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """
    Core engine responsible for statistical validation of telemetry data.
    Uses Z-Score analysis to identify hardware noise and environmental outliers.
    """
    
    @staticmethod
    def calculate_zscore_analysis(current_value: float, historical_values: List[float], threshold: float = 3.0) -> Tuple[bool, str]:
        """
        Determines if a reading is anomalous based on a Gaussian distribution model.
        
        :param current_value: The reading to validate.
        :param historical_values: Historical context for the specific sensor.
        :param threshold: Standard deviation multiplier.
        """
        if len(historical_values) < 5:
            return False, "Insufficient historical baseline for anomaly detection."

        series = pd.Series(historical_values)
        mean = series.mean()
        std_dev = series.std()

        # Handle static baseline cases
        if std_dev == 0:
            return (False, "Valid: Perfect baseline match.") if current_value == mean else (True, "Outlier: Deviation from static baseline.")

        z_score = abs((current_value - mean) / std_dev)
        
        if z_score > threshold:
            return True, f"Outlier detected. Z-Score: {z_score:.2f} exceeded threshold {threshold}."
        
        return False, f"Valid: Z-Score {z_score:.2f} within normal limits."