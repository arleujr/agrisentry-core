import pandas as pd
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """
    Statistical Engine for Data Quality in Agricultural Time Series.
    Evaluates raw telemetry to filter out hardware noise and environmental outliers.
    """
    
    @staticmethod
    def evaluate_zscore(current_value: float, historical_values: List[float], threshold: float = 3.0) -> Tuple[bool, str]:
        """
        Evaluates if a reading is an anomaly using the Z-Score method.
        
        :param current_value: The pending reading to evaluate.
        :param historical_values: A list of recent valid readings from the same sensor.
        :param threshold: The Z-Score limit (3.0 covers 99.7% of normal Gaussian distribution).
        :return: Tuple (is_anomaly, analysis_note)
        """
        # We need a minimum baseline to calculate standard deviation reliably
        if not historical_values or len(historical_values) < 5:
            return False, "Insufficient historical data for statistical baseline."

        series = pd.Series(historical_values)
        mean = series.mean()
        std_dev = series.std()

        # Edge case: All historical values are perfectly identical (std_dev = 0)
        if std_dev == 0:
            if current_value == mean:
                return False, "Valid. Value matches static historical baseline perfectly."
            else:
                return True, f"Anomaly. Value {current_value} deviates from absolute static baseline {mean}."

        # Calculate how many standard deviations the current value is from the mean
        z_score = abs((current_value - mean) / std_dev)

        if z_score > threshold:
            note = f"Z-Score {z_score:.2f} exceeded threshold {threshold}. Mean: {mean:.2f}, StdDev: {std_dev:.2f}."
            logger.warning(f"Hardware Noise Detected! {note}")
            return True, note
        
        return False, f"Valid reading. Z-Score: {z_score:.2f}"