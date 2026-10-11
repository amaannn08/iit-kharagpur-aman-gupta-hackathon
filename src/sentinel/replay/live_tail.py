"""Live capture background tailer: polls local data/live/*.csv files and appends to active replay run."""

import asyncio
import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sentinel.config import settings
from sentinel.contracts.records import InputRecord, SourceType, TimestampQuality
from sentinel.replay.controller import ReplayController

logger = logging.getLogger(__name__)


# A quoted field may span lines, but a record still open after this many lines is malformed
# (e.g. a row truncated when the recorder was killed); it is skipped instead of blocking the file.
MAX_RECORD_LINES = 20


def complete_rows(chunk: bytes) -> Tuple[bytes, int]:
    """Complete CSV records at the start of chunk, and how many bytes they (and any skipped
    malformed record) span. Single pass: each line is scanned once.

    The unterminated last line, or a record whose quoted field is still open, is left for the
    next poll; the recorder may be mid-write.
    """
    lines = chunk.splitlines(keepends=True)
    good: List[bytes] = []
    consumed = 0  # bytes safely past (emitted or skipped)
    i = 0
    while i < len(lines):
        rec, open_quote, j = [], False, i
        while j < len(lines) and lines[j].endswith(b"\n"):
            rec.append(lines[j])
            open_quote ^= lines[j].count(b'"') % 2 == 1
            j += 1
            if not open_quote or len(rec) > MAX_RECORD_LINES:
                break
        if not rec or (open_quote and len(rec) <= MAX_RECORD_LINES):
            break  # unterminated or still-open record: wait for more data
        if open_quote:  # malformed: skip its first line and resynchronise on the next
            logger.warning("Skipping malformed live CSV line: %r", rec[0][:120])
            consumed += len(rec[0])
            i += 1
            continue
        good.extend(rec)
        consumed += sum(len(x) for x in rec)
        i = j
    return b"".join(good), consumed


def parse_incremental_csv(
    file_path: Path, offset: int
) -> Tuple[List[InputRecord], int, Optional[datetime]]:
    """Read newly appended rows from file_path starting at byte offset."""
    if not file_path.exists():
        return [], 0, None

    size = file_path.stat().st_size
    if size < offset:
        offset = 0
    if size == offset:
        return [], offset, None

    try:
        with open(file_path, "rb") as f:
            header_line = f.readline()
            if not header_line:
                return [], 0, None
            headers = [h.strip() for h in next(csv.reader([header_line.decode("utf-8", "replace")]), [])]
            if not headers:
                return [], 0, None
            if offset == 0:
                offset = f.tell()
            f.seek(offset)
            chunk = f.read()
    except Exception as exc:
        logger.warning("Error reading %s at offset %d: %s", file_path, offset, exc)
        return [], offset, None

    good, consumed = complete_rows(chunk)
    new_offset = offset + consumed
    new_text = good.decode("utf-8", "replace")
    if not new_text.strip():
        return [], new_offset, None

    records: List[InputRecord] = []
    latest_ts: Optional[datetime] = None
    stream = io.StringIO(new_text)
    reader = csv.DictReader(stream, fieldnames=headers)
    for idx, row in enumerate(reader):
        headline, body = (row.get("headline") or "").strip(), (row.get("body") or "").strip()
        text_content = f"{headline}. {body}" if headline and body else (headline or body)
        if not text_content:
            continue

        pub_str = row.get("published_at")
        pub_dt = None
        if pub_str:
            try:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                if latest_ts is None or pub_dt > latest_ts:
                    latest_ts = pub_dt
            except Exception:
                pass

        record = InputRecord(
            record_id=row.get("record_id", f"{file_path.stem}-{offset}-{idx}"),
            source_id=row.get("source_id", file_path.stem),
            source_type=SourceType.NEWS,
            text=text_content,
            headline=headline or None,
            published_at=pub_dt,
            timestamp_quality=TimestampQuality.ORIGINAL,
            is_synthetic=False,
            primary_entity_id=row.get("primary_entity_id"),
        )
        records.append(record)

    return records, new_offset, latest_ts


class LiveTailer:
    """Polls local CSV files in data/live/ and appends newly written records to the ReplayController."""

    def __init__(
        self,
        controller: ReplayController,
        live_dir: Optional[Path] = None,
        poll_interval: float = 30.0,
    ) -> None:
        self.controller = controller
        self.live_dir = live_dir or (settings.data_dir / "live")
        self.poll_interval = poll_interval
        self.offsets: Dict[str, int] = {}
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self.last_tail_at: Optional[datetime] = None
        self.last_record_at: Optional[datetime] = None

    def poll_once(self) -> int:
        """Scan data/live/*.csv for new lines and append them if the active run is LIVE.

        Offsets advance in every mode, so switching to a live run later does not replay the
        backlog into it, and live rows are never injected into historical or synthetic runs.
        """
        if not self.live_dir.exists():
            return 0
        is_live = self._mode() == "LIVE"

        appended_total = 0
        csv_files = sorted(self.live_dir.glob("*.csv"))
        for file_path in csv_files:
            file_key = str(file_path.resolve())
            offset = self.offsets.get(file_key, 0)
            records, new_offset, latest_ts = parse_incremental_csv(file_path, offset)
            self.offsets[file_key] = new_offset

            if latest_ts and (self.last_record_at is None or latest_ts > self.last_record_at):
                self.last_record_at = latest_ts

            if records and is_live:
                appended = self.controller.append_records(records)
                appended_total += appended

        self.last_tail_at = datetime.now(timezone.utc)
        return appended_total

    def _mode(self) -> str:
        badges = getattr(self.controller, "_badges", [])
        sources = getattr(self.controller, "_sources", [])
        if any(b == "LIVE CAPTURE" for b in badges) or any(
            s in ("gdelt_live", "sec_8k_live") for s in sources
        ):
            mode = "LIVE"
        elif any(b == "SYNTHETIC SCENARIO" for b in badges):
            mode = "SYNTHETIC"
        elif badges or sources:
            mode = "REPLAY"
        else:
            mode = "IDLE"
        return mode

    def get_live_status(self) -> Dict[str, Any]:
        """Compute live capture status, lag, and recorder process health."""
        mode = self._mode()
        state_file = self.live_dir / ".state.json"
        state_data: Dict[str, Any] = {}
        if state_file.exists():
            try:
                state_data = json.loads(state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        last_fetch_dt: Optional[datetime] = None
        last_fetch_str: Optional[str] = state_data.get("last_fetch_at")
        if last_fetch_str:
            try:
                last_fetch_dt = datetime.fromisoformat(last_fetch_str.replace("Z", "+00:00"))
            except ValueError:
                last_fetch_str = None
        elif state_file.exists() and "last_attempt_at" not in state_data:
            # state written by an older recorder that did not record fetch times
            last_fetch_dt = datetime.fromtimestamp(state_file.stat().st_mtime, tz=timezone.utc)
            last_fetch_str = last_fetch_dt.isoformat(timespec="seconds")

        now = datetime.now(timezone.utc)
        lag_seconds: Optional[float] = None
        if last_fetch_dt:
            lag_seconds = max(0.0, (now - last_fetch_dt).total_seconds())

        # alive = a successful fetch within two of the recorder's own cycles (it records its
        # interval in .state.json; 15 min default)
        recorder_interval = float(state_data.get("interval_seconds", 900.0))
        recorder_alive = bool(lag_seconds is not None and lag_seconds <= 2 * recorder_interval)

        rec_str = (
            self.last_record_at.isoformat(timespec="seconds") if self.last_record_at else None
        )

        return {
            "mode": mode,
            "last_record_at": rec_str,
            "last_fetch_at": last_fetch_str,
            "lag_seconds": round(lag_seconds, 1) if lag_seconds is not None else None,
            "recorder_alive": recorder_alive,
        }

    async def _loop(self) -> None:
        while self._running:
            try:
                self.poll_once()
            except Exception as exc:
                logger.warning("LiveTailer error during loop: %s", exc)
            await asyncio.sleep(self.poll_interval)

    def start(self) -> asyncio.Task:
        if self._task is None or self._task.done():
            self._running = True
            self._task = asyncio.create_task(self._loop())
        return self._task

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
