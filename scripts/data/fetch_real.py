#!/usr/bin/env python3
"""Fetch every real public dataset used by S&P Sentinel into data/raw/real/ (gitignored).

Build-time only: the application never calls these services at runtime.
No Kaggle credentials are needed; public Kaggle datasets download anonymously via kagglehub.

Usage:
    uv run --group data python scripts/data/fetch_real.py
    uv run --group data python scripts/data/fetch_real.py --only kaggle,hf
"""

import argparse
import hashlib
import io
import json
import shutil
import time
import urllib.request
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW = REPO_ROOT / "data" / "raw" / "real"

# SEC fair-access policy requires a descriptive User-Agent with a contact address.
UA = "SPSentinel-Hackathon research (contact: amangupta08@kgpian.iitkgp.ac.in)"

KAGGLE = {
    "phrasebank": "ankurzing/sentiment-analysis-for-financial-news",
    "stock_tweets": "thedevastator/tweet-sentiment-s-impact-on-stock-returns",
    "polygon_news": "rdolphin/financial-news-with-ticker-level-sentiment",
    "transactions": "computingvictor/transactions-fraud-datasets",
}
HF = {
    "hf_fin_topic": "zeroshot/twitter-financial-news-topic",
    "hf_fin_sentiment": "zeroshot/twitter-financial-news-sentiment",
}
MARKET_PROXIES = ["SPY", "IEF", "LQD", "HYG", "^TNX", "^IRX", "^VIX"]
MARKET_START, MARKET_END = "2016-06-01", "2024-03-01"


def get(url: str, ua: str = UA, tries: int = 4) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2**attempt * 2)  # 2s, 4s, 8s backoff
    raise RuntimeError("unreachable")


def kaggle() -> None:
    import kagglehub

    for name, slug in KAGGLE.items():
        dest = RAW / name
        if dest.exists() and any(p.name != "_kaggle_meta.json" for p in dest.iterdir()):
            print(f"skip {name} (already present)")
            continue
        src = Path(kagglehub.dataset_download(slug))
        dest.mkdir(parents=True, exist_ok=True)
        for p in src.iterdir():
            if p.is_dir():
                shutil.copytree(p, dest / p.name, dirs_exist_ok=True)
            else:
                shutil.copy2(p, dest / p.name)
        meta = json.loads(get(f"https://www.kaggle.com/api/v1/datasets/view/{slug}"))
        (dest / "_kaggle_meta.json").write_text(
            json.dumps(
                {
                    "slug": slug,
                    "license": meta.get("licenseName"),
                    "lastUpdated": meta.get("lastUpdated"),
                },
                indent=1,
            )
        )
        print(f"ok {name} ({meta.get('licenseName')})")


def hf() -> None:
    from huggingface_hub import snapshot_download

    for name, repo in HF.items():
        snapshot_download(
            repo_id=repo,
            repo_type="dataset",
            local_dir=RAW / name,
            allow_patterns=["*.csv", "README.md"],
        )
        print(f"ok {name}")


def _sp100():
    import pandas as pd

    html = get("https://en.wikipedia.org/wiki/S%26P_100", ua="Mozilla/5.0").decode()
    table = next(t for t in pd.read_html(io.StringIO(html)) if "Symbol" in t.columns)
    table = table.rename(columns={"Symbol": "ticker", "Name": "name", "Sector": "sector"})
    table = table[["ticker", "name", "sector"]]
    table["ticker"] = table.ticker.str.replace(".", "-", regex=False)
    table.to_csv(RAW / "sec" / "sp100.csv", index=False)
    return table


def _sp500():
    import pandas as pd

    html = get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", ua="Mozilla/5.0")
    table = pd.read_html(io.StringIO(html.decode()))[0]
    table = table.rename(columns={"Symbol": "ticker", "Security": "name", "GICS Sector": "sector"})
    table = table[["ticker", "name", "sector"]]
    table["ticker"] = table.ticker.str.replace(".", "-", regex=False)
    table.to_csv(RAW / "sec" / "sp500.csv", index=False)
    return table


def sec() -> None:
    d = RAW / "sec"
    d.mkdir(parents=True, exist_ok=True)
    (d / "company_tickers.json").write_bytes(get("https://www.sec.gov/files/company_tickers.json"))
    tickers = json.loads((d / "company_tickers.json").read_text())
    cik_by_ticker = {v["ticker"]: v["cik_str"] for v in tickers.values()}
    _sp500()
    sp = _sp100()
    sub = d / "submissions"
    sub.mkdir(exist_ok=True)
    for t in sp.ticker:
        cik = cik_by_ticker.get(t) or cik_by_ticker.get(t.replace("-", "."))
        if not cik or (sub / f"{t}.json").exists():
            continue
        (sub / f"{t}.json").write_bytes(get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json"))
        time.sleep(0.15)  # stay well under SEC's 10 requests/second
    print(f"ok sec ({len(list(sub.glob('*.json')))} filers)")


def market() -> None:
    import pandas as pd
    import yfinance as yf

    d = RAW / "market"
    d.mkdir(parents=True, exist_ok=True)
    sp = pd.read_csv(RAW / "sec" / "sp100.csv").ticker.tolist()
    px = yf.download(
        sp + MARKET_PROXIES,
        start=MARKET_START,
        end=MARKET_END,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    px["Close"].to_parquet(d / "close.parquet")
    px["Volume"].to_parquet(d / "volume.parquet")
    print(f"ok market {px['Close'].shape}")


def gdelt(slices: int = 8) -> None:
    """Record the most recent GDELT 2.0 15-minute slices (default 2 hours) as a snapshot."""
    d = RAW / "gdelt"
    d.mkdir(parents=True, exist_ok=True)
    last = get("http://data.gdeltproject.org/gdeltv2/lastupdate.txt").decode().split()
    newest = datetime.strptime(last[2].rsplit("/", 1)[1][:14], "%Y%m%d%H%M%S")
    for i in range(slices):
        stamp = (newest - timedelta(minutes=15 * i)).strftime("%Y%m%d%H%M%S")
        for kind in ("export.CSV", "gkg.csv"):
            out = d / f"{stamp}.{kind}"
            if out.exists():
                continue
            url = f"http://data.gdeltproject.org/gdeltv2/{stamp}.{kind}.zip"
            try:
                archive = zipfile.ZipFile(io.BytesIO(get(url, tries=1)))
            except Exception as exc:  # GDELT occasionally skips a slice
                print(f"  gdelt slice missing {stamp} {kind}: {exc}")
                continue
            out.write_bytes(archive.read(archive.namelist()[0]))
    print(f"ok gdelt ({len(list(d.iterdir()))} files)")


def checksums() -> None:
    rows = []
    for p in sorted(RAW.rglob("*")):
        if not p.is_file() or p.name == "CHECKSUMS.json":
            continue
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        rows.append(
            {"path": str(p.relative_to(RAW)), "bytes": p.stat().st_size, "sha256": h.hexdigest()}
        )
    (RAW / "CHECKSUMS.json").write_text(json.dumps(rows, indent=1))
    print(f"ok checksums ({len(rows)} files)")


STEPS = {"kaggle": kaggle, "hf": hf, "sec": sec, "market": market, "gdelt": gdelt}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", default=",".join(STEPS), help="comma-separated steps")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    for step in args.only.split(","):
        STEPS[step.strip()]()
    checksums()
