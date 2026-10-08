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
    speed = Column(Float, default=1.0, nullable=False)
    current_simulated_at = Column(DateTime, nullable=True)
    total_records = Column(Integer, default=0, nullable=False)
    processed_records = Column(Integer, default=0, nullable=False)
    duplicate_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)


class RecordModel(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(String(64), nullable=False, index=True)
    run_id = Column(String(64), ForeignKey("runs.run_id"), nullable=True, index=True)
    source_id = Column(String(64), nullable=False)
    source_type = Column(String(32), nullable=False)
    text = Column(Text, nullable=False)
    sequence_number = Column(Integer, nullable=True)
    published_at = Column(DateTime, nullable=True)
    simulated_at = Column(DateTime, nullable=True)
    is_synthetic = Column(Boolean, default=True, nullable=False)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    duplicate_group_id = Column(String(64), nullable=True, index=True)
    canonical_record_id = Column(String(64), nullable=True)


class SignalModel(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(String(64), nullable=False, index=True)
    run_id = Column(String(64), ForeignKey("runs.run_id"), nullable=False, index=True)
    record_id = Column(String(64), nullable=False, index=True)
    entity_name = Column(String(128), nullable=True)
    entity_ticker = Column(String(32), nullable=True, index=True)
    sentiment_score = Column(Float, nullable=False)
    sentiment_label = Column(String(32), nullable=False)
    event_label = Column(String(64), nullable=False)
    event_confidence = Column(Float, nullable=False)
    impact_score = Column(Integer, nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    duplicate_group_id = Column(String(64), nullable=True)
    eligible_for_action = Column(Boolean, default=True, nullable=False)
    action_block_reasons = Column(Text, nullable=True)
    raw_json = Column(Text, nullable=True)


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
    raw_json = Column(Text, nullable=True)
