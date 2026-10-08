from datetime import datetime, timezone

import pytest

from sentinel.contracts.records import InputRecord, SourceType
from sentinel.replay.controller import ReplayController, RunState


@pytest.fixture
def sample_records():
    r1 = InputRecord(
        record_id="rec-001",
        source_id="news_demo",
        source_type=SourceType.NEWS,
        text="SVB Financial faces unprecedented deposit outflow following asset sales.",
        simulated_at=datetime(2023, 3, 10, 9, 0, tzinfo=timezone.utc),
        sequence_number=1,
    )
    # Exact duplicate text of rec-001
    r2 = InputRecord(
        record_id="rec-002",
        source_id="social_demo",
        source_type=SourceType.SOCIAL,
        text="svb financial faces unprecedented deposit outflow following asset sales",
        simulated_at=datetime(2023, 3, 10, 9, 15, tzinfo=timezone.utc),
        sequence_number=2,
    )
    r3 = InputRecord(
        record_id="rec-003",
        source_id="news_demo",
        source_type=SourceType.NEWS,
        text="Signature Bank closed by state authorities to contain contagion.",
        simulated_at=datetime(2023, 3, 10, 10, 0, tzinfo=timezone.utc),
        sequence_number=3,
    )
    return [r1, r2, r3]


@pytest.mark.asyncio
async def test_controller_load_and_step(sample_records):
    controller = ReplayController()
    controller.load_scenario("svb_run_march2023", sample_records)

    status = controller.get_status()
    assert status.scenario_id == "svb_run_march2023"
    assert status.state == RunState.IDLE
    assert status.total_records == 3
    assert status.pending_records == 3
    assert status.processed_count == 0

    # Step 1
    step1 = await controller.step()
    assert step1 is not None
    assert step1.record.record_id == "rec-001"
    assert not step1.dedup.is_duplicate

    status = controller.get_status()
    assert status.pending_records == 2
    assert status.processed_count == 1
    assert status.duplicate_count == 0

    # Step 2: Duplicate
    step2 = await controller.step()
    assert step2 is not None
    assert step2.record.record_id == "rec-002"
    assert step2.dedup.is_duplicate
    assert step2.dedup.canonical_record_id == "rec-001"

    status = controller.get_status()
    assert status.pending_records == 1
    assert status.processed_count == 2
    assert status.duplicate_count == 1

    # Step 3: Third record
    step3 = await controller.step()
    assert step3 is not None
    assert step3.record.record_id == "rec-003"
    assert not step3.dedup.is_duplicate

    # Queue empty
    step4 = await controller.step()
    assert step4 is None


@pytest.mark.asyncio
async def test_controller_pause_resume_reset(sample_records):
    controller = ReplayController()
    controller.load_scenario("test_scenario", sample_records)
    initial_run_id = controller.run_id

    controller.pause()
    # Pausing from IDLE stays IDLE
    assert controller.state == RunState.IDLE

    # Step one
    await controller.step()
    assert controller.get_status().processed_count == 1

    # Reset
    controller.reset()
    assert controller.run_id != initial_run_id
    assert controller.state == RunState.IDLE
    assert controller.get_status().total_records == 0
    assert controller.get_status().processed_count == 0


@pytest.mark.asyncio
async def test_controller_processor_error_isolation(sample_records):
    controller = ReplayController()
    controller.load_scenario("test_scenario", sample_records)

    async def faulty_processor(record, dedup):
        if record.record_id == "rec-001":
            raise RuntimeError("Downstream simulated error")

    step1 = await controller.step(processor=faulty_processor)
    assert step1 is not None
    assert not step1.success
    assert "Downstream simulated error" in step1.error_message
    assert controller.get_status().error_count == 1

    # Next record still processes successfully
    step2 = await controller.step()
    assert step2 is not None
    assert step2.success
