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
import urllib.parse
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
SP500_START = "2022-06-01"  # 120-day beta warm-up before the 2023 Polygon news window


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
    # S&P 500 closes over the Polygon news window, for impact labels on every linked company
    sp500 = pd.read_csv(RAW / "sec" / "sp500.csv").ticker.tolist()
    wide = yf.download(
        sorted(set(sp500) | set(MARKET_PROXIES)),
        start=SP500_START,
        end=MARKET_END,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    wide["Close"].to_parquet(d / "close_sp500.parquet")
    print(f"ok market {px['Close'].shape}, sp500 {wide['Close'].shape}")


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


# 8-K items whose filing *is* the event: real, labeled text for classes the public tweet
# datasets lack. Query -> event class (EDGAR full-text search, all filers).
SEC_8K_QUERIES = {
    "1.05": ('"Item 1.05" "cybersecurity incident"', "CYBER"),
    "1.03": ('"Item 1.03" "Bankruptcy or Receivership"', "CREDIT"),
    "2.04": ('"Item 2.04" "Triggering Events"', "CREDIT"),
    # Routine filings as real negatives: 8-K boilerplate alone must not look like a credit event
    "2.02": ('"Item 2.02" "Results of Operations and Financial Condition"', "EARNINGS"),
    "5.02": ('"Item 5.02" "Departure of Directors"', "OTHER"),
    "7.01": ('"Item 7.01" "Regulation FD Disclosure"', "OTHER"),
    "8.01": ('"Item 8.01" "Other Events"', "OTHER"),
    "2.03": ('"Item 2.03" "Creation of a Direct Financial Obligation"', "OTHER"),
}
DISTRESS_ITEMS = {"1.03", "1.05", "2.04", "2.06"}
SEC_8K_CAP = 150  # filings per item


def sec_8k() -> None:
    d = RAW / "sec" / "8k"
    d.mkdir(parents=True, exist_ok=True)
    index_path = d / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    for item, (query, label) in SEC_8K_QUERIES.items():
        hits, offset = [], 0
        while len(hits) < SEC_8K_CAP:
            url = (
                "https://efts.sec.gov/LATEST/search-index?forms=8-K&from="
                f"{offset}&q={urllib.parse.quote(query)}"
            )
            page = json.loads(get(url))["hits"]["hits"]
            if not page:
                break
            hits.extend(page)
            offset += len(page)
            time.sleep(0.15)
        for h in hits[:SEC_8K_CAP]:
            src = h["_source"]
            adsh, doc = h["_id"].split(":", 1)
            items = src.get("items", [])
            if adsh in index or item not in items:
                continue
            if label in ("OTHER", "EARNINGS") and DISTRESS_ITEMS & set(items):
                continue  # a routine-item negative must not also report a distress item
            cik = int(src["ciks"][0])
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-', '')}/{doc}"
            try:
                (d / f"{adsh}.htm").write_bytes(get(doc_url))
            except Exception as exc:
                print(f"  skip {adsh}: {exc}")
                continue
            index[adsh] = {
                "item": item,
                "label": label,
                "company": src["display_names"][0],
                "file_date": src["file_date"],
                "form": src.get("form"),
                "url": doc_url,
            }
            time.sleep(0.15)  # SEC fair access: < 10 requests/second
        index_path.write_text(json.dumps(index, indent=1))
    counts = {i: sum(v["item"] == i for v in index.values()) for i in SEC_8K_QUERIES}
    print(f"ok sec_8k {counts}")


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


FRED_SERIES = [
    "BAMLH0A0HYM2",
    "BAMLC0A0CM",
    "BAMLC0A1CAAA",
    "BAMLC0A2CAA",
    "BAMLC0A3CA",
    "BAMLC0A4CBBB",
    "BAMLH0A1HYBB",
    "BAMLH0A2HYB",
    "BAMLH0A3HYC",
    "DGS5",
]


def fred() -> None:
    d = RAW / "fred"
    d.mkdir(parents=True, exist_ok=True)
    for sid in FRED_SERIES:
        out = d / f"{sid}.csv"
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
        try:
            out.write_bytes(get(url))
        except Exception as exc:
            print(f"  skip fred {sid}: {exc}")
            continue
    print(f"ok fred ({len(list(d.glob('*.csv')))} series)")


def xbrl() -> None:
    import pandas as pd

    d = RAW / "sec" / "xbrl"
    d.mkdir(parents=True, exist_ok=True)
    tickers_path = RAW / "sec" / "company_tickers.json"
    if not tickers_path.exists():
        sec()
    tickers = json.loads(tickers_path.read_text())
    cik_by_ticker = {v["ticker"]: v["cik_str"] for v in tickers.values()}
    sp100_path = RAW / "sec" / "sp100.csv"
    if not sp100_path.exists():
        _sp100()
    sp = pd.read_csv(sp100_path)
    for t in sp.ticker:
        out = d / f"{t}.json"
        if out.exists():
            continue
        cik = cik_by_ticker.get(t) or cik_by_ticker.get(t.replace("-", "."))
        if not cik:
            sub = RAW / "sec" / "submissions" / f"{t}.json"
            if sub.exists():
                cik = int(json.loads(sub.read_text()).get("cik"))
        if not cik:
            continue
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        try:
            out.write_bytes(get(url))
        except Exception as exc:
            print(f"  skip xbrl {t}: {exc}")
            continue
        time.sleep(0.15)
    print(f"ok xbrl ({len(list(d.glob('*.json')))} filers)")


def gdelt_hist(start: str = "2023-03-09", end: str = "2023-03-14") -> None:
    """Fetch GDELT 2.0 GKG slices across the 2023 SVB bank run window and build svb_weekend.csv."""
    import importlib.util

    import pandas as pd

    d_raw = RAW / "gdelt_hist"
    d_raw.mkdir(parents=True, exist_ok=True)
    out_dir = REPO_ROOT / "data" / "real" / "gdelt"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "svb_weekend.csv"

    spec = importlib.util.spec_from_file_location(
        "convert_real", REPO_ROOT / "scripts" / "data" / "convert_real.py"
    )
    convert_real = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(convert_real)

    # 22 slices sampled across 2023-03-09 through 2023-03-14
    stamps = [
        "20230309140000", "20230309180000", "20230309220000",
        "20230310140000", "20230310160000", "20230310180000", "20230310200000", "20230310220000",
        "20230311140000", "20230311180000", "20230311220000",
        "20230312140000", "20230312180000", "20230312220000",
        "20230313120000", "20230313140000", "20230313160000", "20230313180000", "20230313220000",
        "20230314140000", "20230314180000", "20230314220000",
    ]

    all_rows = []
    for s in stamps:
        cached = d_raw / f"{s}.gkg.csv"
        if cached.exists():
            lines = cached.read_text(encoding="utf-8", errors="replace").splitlines()
        else:
            url = f"https://data.gdeltproject.org/gdeltv2/{s}.gkg.csv.zip"
            try:
                data = get(url, tries=2)
                archive = zipfile.ZipFile(io.BytesIO(data))
                content = archive.read(archive.namelist()[0]).decode("utf-8", errors="replace")
                cached.write_text(content, encoding="utf-8")
                lines = content.splitlines()
            except Exception as exc:
                print(f"  skip gdelt_hist {s}: {exc}")
                continue
        rows = convert_real.parse_gkg_rows(lines)
        for r in rows:
            r["source_id"] = "gdelt_svb_2023"
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows).drop_duplicates("headline").sort_values(["published_at", "record_id"])

    # Filter: retain all SVB/FRC/SBNY headlines + banking/markets/deposit/fed headlines
    svb_mask = df.headline.str.contains(
        r"Silicon Valley Bank|SVB|First Republic|Signature Bank|Silvergate|FDIC|bank run|deposit flight|bailout|systemic risk",
        case=False,
        regex=True,
    )
    bank_mask = df.headline.str.contains(
        r"bank|lender|credit|default|liquidity|treasury|fed|rates|yield|contagion",
        case=False,
        regex=True,
    )
    market_mask = df.headline.str.contains(
        r"stocks?|shares?|bonds?|markets?|rally|slump|drop|fall|plunge|rout|soar|crisis|funds?|debts?|finance|invest|economy|inflation",
        case=False,
        regex=True,
    )
    keep_mask = svb_mask | bank_mask | market_mask
    filtered = df[keep_mask].copy()
    if len(filtered) > 3000:
        svb_part = filtered[svb_mask]
        other_part = filtered[~svb_mask].sample(n=3000 - len(svb_part), random_state=42)
        filtered = pd.concat([svb_part, other_part]).sort_values(["published_at", "record_id"])

    cols = convert_real.NEWS_COLS + ["source_url"]
    filtered[cols].to_csv(out_path, index=False)
    print(f"ok gdelt_hist: wrote {out_path} with {len(filtered)} rows ({svb_mask.sum()} SVB/banking-crisis specific)")

    spec_m = importlib.util.spec_from_file_location(
        "build_manifest", REPO_ROOT / "scripts" / "data" / "build_manifest.py"
    )
    build_manifest = importlib.util.module_from_spec(spec_m)
    spec_m.loader.exec_module(build_manifest)

    build_manifest.register_dataset(
        str(out_path.relative_to(REPO_ROOT)),
        "Real GDELT 2.0 headlines from the March 9-14 2023 SVB weekend bank run and regional banking contagion",
        "GDELT Project (Public domain / open research)",
        is_synthetic=False,
        source="https://data.gdeltproject.org/gdeltv2/",
        columns=cols,
    )


STEPS = {
    "kaggle": kaggle,
    "hf": hf,
    "sec": sec,
    "sec_8k": sec_8k,
    "market": market,
    "gdelt": gdelt,
    "gdelt_hist": gdelt_hist,
    "fred": fred,
    "xbrl": xbrl,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", default=",".join(STEPS), help="comma-separated steps")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    for step in args.only.split(","):
        STEPS[step.strip()]()
    checksums()
