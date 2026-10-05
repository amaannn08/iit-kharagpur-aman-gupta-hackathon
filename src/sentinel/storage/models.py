"""SQLAlchemy ORM models for S&P Sentinel persistence."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from sentinel.storage.db import Base


class RunModel(Base):
    __tablename__ = "runs"

    run_id = Column(String(64), primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(32), default="idle", nullable=False)
    scenario_id = Column(String(64), nullable=True)
    total_records = Column(Integer, default=0)
    processed_signals = Column(Integer, default=0)


class RecordModel(Base):
    __tablename__ = "records"

    record_id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), ForeignKey("runs.run_id"), nullable=True, index=True)
    source_id = Column(String(64), nullable=False)
    source_type = Column(String(32), nullable=False)
    text = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=True)
    simulated_at = Column(DateTime, nullable=True)
    is_synthetic = Column(Boolean, default=True)


class SignalModel(Base):
    __tablename__ = "signals"

    signal_id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), ForeignKey("runs.run_id"), nullable=False, index=True)
    record_id = Column(String(64), ForeignKey("records.record_id"), nullable=False)
    entity_ticker = Column(String(32), nullable=True, index=True)
    sentiment_score = Column(Float, nullable=False)
    sentiment_label = Column(String(32), nullable=False)
    event_label = Column(String(64), nullable=False)
    event_confidence = Column(Float, nullable=False)
    impact_score = Column(Integer, nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    eligible_for_action = Column(Boolean, default=True)


class StressRunModel(Base):
    __tablename__ = "stress_runs"

    stress_id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), ForeignKey("runs.run_id"), nullable=False, index=True)
    scenario_id = Column(String(64), nullable=True)
    trigger_signal_id = Column(String(64), ForeignKey("signals.signal_id"), nullable=True)
    baseline_value_usd = Column(Float, nullable=False)
    stressed_value_usd = Column(Float, nullable=False)
    total_loss_usd = Column(Float, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
