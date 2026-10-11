"""Test LiveTailer offset tracking, incremental appending, and deduplication."""

import json
from datetime import datetime, timezone
from pathlib import Path

from sentinel.replay.controller import ReplayController
from sentinel.replay.live_tail import LiveTailer, parse_incremental_csv


def test_parse_incremental_csv_offset_handling(tmp_path: Path):
    csv_file = tmp_path / "live_test.csv"
    headers = "record_id,headline,body,published_at\n"
    csv_file.write_text(headers)

    records, offset, ts = parse_incremental_csv(csv_file, 0)
    assert records == []
    assert offset > 0

    # Append 2 lines
    line1 = "rec-1,Fed holds rates steady,The central bank kept interest rates unchanged,2023-11-01T18:00:00Z\n"
    line2 = "rec-2,Tech earnings beat estimates,Major tech firm reports quarterly profit,2023-11-01T20:00:00Z\n"
    with open(csv_file, "a") as f:
        f.write(line1 + line2)

    new_records, new_offset, latest_ts = parse_incremental_csv(csv_file, offset)
    assert len(new_records) == 2
    assert new_records[0].record_id == "rec-1"
    assert new_records[1].record_id == "rec-2"
    assert new_offset > offset
    assert latest_ts is not None

    # Calling again without new data returns nothing (no double append)
    records_again, offset_again, ts_again = parse_incremental_csv(csv_file, new_offset)
    assert records_again == []
    assert offset_again == new_offset


def test_live_tailer_appends_to_controller_once(tmp_path: Path):
    controller = ReplayController()
    controller.load_scenario("live-test", [], sources=["gdelt_live"], badges=["LIVE CAPTURE"])

    live_dir = tmp_path / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    csv_file = live_dir / "gdelt_live.csv"
    csv_file.write_text("record_id,headline,body,published_at\n")

    tailer = LiveTailer(controller, live_dir=live_dir)
    assert tailer.poll_once() == 0

    # Write 2 lines to temp file
    with open(csv_file, "a") as f:
        f.write(
            "live-1,Oil prices decline,Crude drops 3 percent,2023-11-02T10:00:00Z\n"
            "live-2,Bank liquidity remains robust,Deposits stabilize across lenders,2023-11-02T11:00:00Z\n"
        )

    count = tailer.poll_once()
    assert count == 2
    assert controller.get_status().total_records == 2

    # Second poll should append 0 (no duplicate append)
    count2 = tailer.poll_once()
    assert count2 == 0
    assert controller.get_status().total_records == 2


def test_live_status_reporting(tmp_path: Path):
    controller = ReplayController()
    controller.load_scenario("live-run", [], sources=["gdelt_live"], badges=["LIVE CAPTURE"])

    live_dir = tmp_path / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    state_file = live_dir / ".state.json"

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state_file.write_text(json.dumps({"last_fetch_at": now_iso}))

    tailer = LiveTailer(controller, live_dir=live_dir)
    status = tailer.get_live_status()

    assert status["mode"] == "LIVE"
    assert status["last_fetch_at"] == now_iso
    assert status["recorder_alive"] is True
    assert status["lag_seconds"] < 10.0


def test_partial_trailing_row_is_left_for_the_next_poll(tmp_path: Path):
    csv_file = tmp_path / "live.csv"
    csv_file.write_text("record_id,headline,body,published_at\n")
    _, offset, _ = parse_incremental_csv(csv_file, 0)
    with open(csv_file, "a") as f:
        f.write('rec-1,Full row,"Body, with comma",2023-11-01T18:00:00Z\nrec-2,Half wri')
    records, offset, _ = parse_incremental_csv(csv_file, offset)
    assert [r.record_id for r in records] == ["rec-1"]
    with open(csv_file, "a") as f:
        f.write("tten row,Body,2023-11-01T19:00:00Z\n")
    records, _, _ = parse_incremental_csv(csv_file, offset)
    assert [(r.record_id, r.headline) for r in records] == [("rec-2", "Half written row")]


def test_open_quoted_field_is_not_consumed(tmp_path: Path):
    csv_file = tmp_path / "live.csv"
    csv_file.write_text("record_id,headline,body,published_at\n")
    _, offset, _ = parse_incremental_csv(csv_file, 0)
    with open(csv_file, "a") as f:
        f.write('rec-1,Headline,"multi\nline body still being writ')
    records, new_offset, _ = parse_incremental_csv(csv_file, offset)
    assert records == [] and new_offset == offset


def test_live_rows_are_not_injected_into_historical_replays(tmp_path: Path):
    controller = ReplayController()
    controller.load_scenario("svb", [], sources=["gdelt_svb_2023"], badges=["HISTORICAL REPLAY"])
    live_dir = tmp_path / "live"
    live_dir.mkdir()
    (live_dir / "gdelt_live.csv").write_text(
        "record_id,headline,body,published_at\nlive-1,Oil falls,Crude drops,2023-11-02T10:00:00Z\n"
    )
    tailer = LiveTailer(controller, live_dir=live_dir)
    assert tailer.poll_once() == 0
    assert controller.get_status().total_records == 0


def test_truncated_row_does_not_stall_the_file(tmp_path: Path):
    """A row cut off mid-quote (recorder killed) is skipped once later rows arrive."""
    csv_file = tmp_path / "live.csv"
    csv_file.write_text("record_id,headline,body,published_at\n")
    _, offset, _ = parse_incremental_csv(csv_file, 0)
    lines = ['rec-9,"Half written\n'] + [
        f"rec-{i},Headline {i},Body,2023-11-01T18:00:00Z\n" for i in range(10, 40)
    ]
    with open(csv_file, "a") as f:
        f.writelines(lines)
    seen = []
    for _ in range(3):
        records, offset, _ = parse_incremental_csv(csv_file, offset)
        seen += [r.record_id for r in records]
    assert "rec-39" in seen and "rec-9" not in seen
    assert offset == csv_file.stat().st_size


def test_recorder_repairs_partial_tail(tmp_path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "record_live", Path(__file__).resolve().parent.parent / "scripts" / "live" / "record_live.py"
    )
    rl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rl)
    f = tmp_path / "x.csv"
    f.write_bytes(b'a,b\n1,2\n3,"par')
    rl.repair_truncated_tail(f)
    assert f.read_bytes() == b"a,b\n1,2\n"


def test_status_uses_last_successful_fetch_and_recorder_interval(tmp_path: Path):
    from datetime import timedelta

    controller = ReplayController()
    controller.load_scenario("live", [], sources=["gdelt_live"], badges=["LIVE CAPTURE"])
    live_dir = tmp_path / "live"
    live_dir.mkdir()
    now = datetime.now(timezone.utc)
    state = live_dir / ".state.json"
    # failing recorder: attempts recorded, no successful fetch ever
    state.write_text(json.dumps({"last_attempt_at": now.isoformat(), "interval_seconds": 900}))
    assert LiveTailer(controller, live_dir=live_dir).get_live_status()["recorder_alive"] is False
    # healthy 15-min recorder, 12 minutes since its last fetch: still alive
    state.write_text(json.dumps({"last_attempt_at": now.isoformat(), "interval_seconds": 900,
                                 "last_fetch_at": (now - timedelta(minutes=12)).isoformat()}))
    assert LiveTailer(controller, live_dir=live_dir).get_live_status()["recorder_alive"] is True
