#!/usr/bin/env python3
"""Live capture recorder: append real GDELT and SEC EDGAR 8-K records to local CSV files.

The application never calls external services (AGENTS.md). Real-time ingestion works by
running this recorder alongside it: every cycle it appends records it has not seen before to
  data/live/gdelt_live.csv   GDELT 2.0 GKG finance headlines (15-minute files, no API key)
  data/live/sec_8k_live.csv  new Form 8-K filings by S&P 500 issuers (data.sec.gov)
and the app queues them with POST /api/replay/append {"source": "gdelt_live" | "sec_8k_live"}.

Usage:
  uv run python scripts/live/record_live.py --once                  # one cycle
  uv run python scripts/live/record_live.py --interval-min 15       # keep recording
  uv run python scripts/live/record_live.py --once --backfill-days 3  # include recent 8-Ks
"""

import argparse
import csv
import importlib.util
import io
import json
import re
import sys
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LIVE = REPO_ROOT / "data" / "live"
UNIVERSE = REPO_ROOT / "data" / "universe" / "entities.csv"
STATE = LIVE / ".state.json"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fetch_real = _load("fetch_real", "scripts/data/fetch_real.py")
convert_real = _load("convert_real", "scripts/data/convert_real.py")
NEWS_COLS = convert_real.NEWS_COLS

ITEM_NAMES = {
    "1.01": "Material Definitive Agreement", "1.02": "Termination of Agreement",
    "1.03": "Bankruptcy or Receivership", "1.05": "Material Cybersecurity Incident",
    "2.01": "Completion of Acquisition or Disposition", "2.02": "Results of Operations",
    "2.03": "Creation of a Direct Financial Obligation", "2.04": "Triggering Events (debt acceleration)",
    "2.05": "Exit or Restructuring Costs", "2.06": "Material Impairments",
    "3.01": "Delisting Notice", "3.02": "Unregistered Sale of Equity",
    "3.03": "Modification of Security Holder Rights", "4.01": "Change of Auditor",
    "4.02": "Non-Reliance on Financial Statements", "5.01": "Change in Control",
    "5.03": "Amendment to Articles or Bylaws", "5.07": "Shareholder Vote Results",
    "5.02": "Officer or Director Change", "7.01": "Regulation FD Disclosure", "8.01": "Other Events",
}  # fmt: skip


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"gdelt_files": [], "sec_seen": []}


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=1))


def append_rows(path: Path, rows: list) -> int:
    if not rows:
        return 0
    existing = set(pd.read_csv(path).record_id) if path.exists() else set()
    fresh = [r for r in rows if r["record_id"] not in existing]
    if fresh:
        pd.DataFrame(fresh, columns=NEWS_COLS).to_csv(
            path, mode="a", header=not path.exists(), index=False
        )
    return len(fresh)


def gdelt_cycle(state: dict) -> int:
    """Ingest the newest published GKG slice. lastupdate.txt can list a slice before it is
    downloadable (observed 404s), so walk back up to an hour of 15-minute slices."""
    lines = (
        fetch_real.get("http://data.gdeltproject.org/gdeltv2/lastupdate.txt").decode().splitlines()
    )
    newest = next(line.split()[2] for line in lines if line.endswith(".gkg.csv.zip"))
    stamp = datetime.strptime(newest.rsplit("/", 1)[1][:14], "%Y%m%d%H%M%S")
    for back in range(5):
        slice_ts = (stamp - timedelta(minutes=15 * back)).strftime("%Y%m%d%H%M%S")
        url = f"http://data.gdeltproject.org/gdeltv2/{slice_ts}.gkg.csv.zip"
        if url in state["gdelt_files"]:
            return 0  # newest available slice already ingested
        try:
            archive = zipfile.ZipFile(io.BytesIO(fetch_real.get(url, tries=1)))
        except Exception:
            continue
        csv.field_size_limit(sys.maxsize)
        text = archive.read(archive.namelist()[0]).decode("utf-8", errors="replace")
        rows = convert_real.parse_gkg_rows(text.splitlines())
        state["gdelt_files"] = (state["gdelt_files"] + [url])[-200:]
        return append_rows(LIVE / "gdelt_live.csv", rows)
    print("  gdelt: no slice available in the last hour")
    return 0


def item_statement(text: str, item: str) -> str:
    for m in re.finditer(rf"Item\s*{re.escape(item)}\b[^.]{{0,160}}?\.?", text, re.I):
        body = re.split(
            r"\bItem\s*\d\.\d\d\b|\bSIGNATURES?\b", text[m.end() :], maxsplit=1, flags=re.I
        )[0]
        letters = [c for c in body if c.isalpha()]
        if len(body) >= 150 and sum(c.isupper() for c in letters) / max(1, len(letters)) <= 0.5:
            return convert_real.clean_text(body[:420])
    return ""


def sec_cycle(state: dict, backfill_days: int, max_filers: int) -> int:
    universe = pd.read_csv(UNIVERSE)
    universe = universe[(universe.is_synthetic == False) & universe.cik.notna()]  # noqa: E712
    seen = set(state["sec_seen"])
    first_run = not seen
    cutoff = (datetime.now(timezone.utc) - timedelta(days=backfill_days)).date().isoformat()
    rows = []
    for r in universe.head(max_filers).itertuples():
        cik = int(r.cik)
        try:
            recent = json.loads(
                fetch_real.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
            )
        except Exception as exc:
            print(f"  sec skip {r.ticker}: {exc}")
            continue
        time.sleep(0.12)  # SEC fair access: < 10 requests/second
        f = recent["filings"]["recent"]
        for i, form in enumerate(f["form"]):
            if form != "8-K":
                continue
            adsh = f["accessionNumber"][i]
            if adsh in seen:
                continue
            seen.add(adsh)
            if first_run and f["filingDate"][i] < cutoff:
                continue  # seed state on first run; only backfill the requested window
            items = [x for x in f["items"][i].split(",") if x and x != "9.01"]
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-', '')}/{f['primaryDocument'][i]}"
            try:
                text = convert_real.html_to_text(fetch_real.get(doc_url).decode("utf-8", "ignore"))
            except Exception:
                continue
            time.sleep(0.12)
            body = " ".join(s for s in (item_statement(text, it) for it in items) if s)
            names = "; ".join(ITEM_NAMES.get(it, it) for it in items)
            rows.append(
                {
                    "record_id": convert_real.rid("sec", adsh),
                    "source_id": "sec_edgar_8k",
                    "source_type": "news",
                    "headline": f"{r.canonical_name} files Form 8-K: Item {', '.join(items)} ({names})",
                    "body": body,
                    "published_at": f["acceptanceDateTime"][i],
                    "timestamp_quality": "original",
                    "simulated_at": "",
                    "is_synthetic": "false",
                    "primary_entity_id": r.ticker,  # filer identity is certain issuer metadata
                }
            )
    state["sec_seen"] = sorted(seen)[-20000:]
    return append_rows(LIVE / "sec_8k_live.csv", rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval-min", type=float, default=15.0)
    ap.add_argument("--backfill-days", type=int, default=0)
    ap.add_argument("--max-filers", type=int, default=600)
    ap.add_argument("--skip", default="", help="comma list: gdelt,sec")
    args = ap.parse_args()
    LIVE.mkdir(parents=True, exist_ok=True)
    skip = set(filter(None, args.skip.split(",")))
    while True:
        state = load_state()
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        g = s = 0
        try:  # a failing source must not stop the other one or the recorder
            g = gdelt_cycle(state) if "gdelt" not in skip else 0
        except Exception as exc:
            print(f"  gdelt cycle failed: {exc}")
        try:
            s = sec_cycle(state, args.backfill_days, args.max_filers) if "sec" not in skip else 0
        except Exception as exc:
            print(f"  sec cycle failed: {exc}")
        save_state(state)
        print(f"[{stamp}] appended gdelt={g} sec_8k={s}", flush=True)
        if args.once:
            break
        time.sleep(args.interval_min * 60)


if __name__ == "__main__":
    main()
