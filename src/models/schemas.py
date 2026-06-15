import uuid
import enum
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum, text
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base

class DataQualityStatus(str, enum.Enum):
    """
    Enum strictly mirroring the PostgreSQL DataQualityStatus type.
    """
    PENDING = 'PENDING'
    VALID = 'VALID'
    ANOMALY_NOISE = 'ANOMALY_NOISE'
    ANOMALY_CRITICAL = 'ANOMALY_CRITICAL'

class Sensor(Base):
    """
    Relational metadata for physical hardware sensors.
    """
    __tablename__ = "sensors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hardware_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String)

class SensorReading(Base):
    """
    Time-series hypertable mapping for telemetry ingestion.
    Note: Composite primary key (id, created_at) is required by TimescaleDB constraints.
    """
    __tablename__ = "sensor_readings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    value = Column(Float, nullable=False)
    sensor_id = Column(UUID(as_uuid=True), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False)
    status = Column(
        Enum(DataQualityStatus, name="DataQualityStatus"), 
        nullable=False, 
        default=DataQualityStatus.PENDING
    )
    ai_analysis_note = Column(String)
    created_at = Column(
        DateTime(timezone=True), 
        primary_key=True, 
        server_default=text('CURRENT_TIMESTAMP')
    )
class ActuatorLog(Base):
    """
    Relational log mapping for physical actuators (Water pumps, exhaust fans, etc.).
    Used to provide physical context to AI anomaly detection.
    """
    __tablename__ = "actuator_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actuator_name = Column(String(100), nullable=False)
    # Using simple UUID for the test, but could be a ForeignKey in production
    sensor_environment_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(50), nullable=False) # e.g., 'ACTIVE', 'INACTIVE'
    timestamp = Column(DateTime(timezone=True), nullable=False)   