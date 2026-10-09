#!/usr/bin/env python3
"""Automated Kaggle dataset fetcher and acquisition manager for S&P Sentinel.

Manages acquisition of public benchmark and transaction datasets specified in
the hackathon Problem Statement and Review Plan:
1. ankurzing/sentiment-analysis-for-financial-news (FinancialPhraseBank)
2. rdolphin/financial-news-with-ticker-level-sentiment (Ticker-Level News)
3. thedevastator/tweet-sentiment-s-impact-on-stock-returns (Stock Tweets & Returns)
4. computingvictor/transactions-fraud-datasets (Financial Transactions / Retail Credit)

Handles credentials verification, CLI downloading, license extraction, and
graceful offline bootstrapping for reproducible zero-key evaluation.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_KAGGLE_DIR = REPO_ROOT / "data" / "raw" / "kaggle"

DATASETS = {
    "phrasebank": {
        "slug": "ankurzing/sentiment-analysis-for-financial-news",
        "dest": RAW_KAGGLE_DIR / "phrasebank",
        "description": "FinancialPhraseBank (Malo et al. 2014) sentiment benchmark.",
        "license": "CC BY-NC-SA 4.0",
        "expected_files": ["all-data.csv"],
    },
    "ticker_news": {
        "slug": "rdolphin/financial-news-with-ticker-level-sentiment",
        "dest": RAW_KAGGLE_DIR / "ticker_news",
        "description": "Financial news articles with ticker-level sentiment annotations.",
        "license": "CC0: Public Domain",
        "expected_files": ["financial_news.csv"],
    },
    "tweets": {
        "slug": "thedevastator/tweet-sentiment-s-impact-on-stock-returns",
        "dest": RAW_KAGGLE_DIR / "tweets",
        "description": "Stock tweets with forward returns and polarity scores.",
        "license": "CC0: Public Domain",
        "expected_files": ["stock_tweets.csv"],
    },
    "transactions": {
        "slug": "computingvictor/transactions-fraud-datasets",
        "dest": RAW_KAGGLE_DIR / "transactions",
        "description": "Retail credit card transactions, user credit scores, and cards.",
        "license": "CC0: Public Domain",
        "expected_files": ["transactions.csv", "users.csv", "cards.csv"],
    },
}


def check_kaggle_cli() -> bool:
    """Check if kaggle CLI is installed and discoverable."""
    return shutil.which("kaggle") is not None


def check_kaggle_credentials() -> bool:
    """Check if ~/.kaggle/kaggle.json or KAGGLE_USERNAME/KAGGLE_KEY environment variables exist."""
    cred_file = Path.home() / ".kaggle" / "kaggle.json"
    if cred_file.exists():
        return True
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return True
    return False


def print_credential_help() -> None:
    """Print clear instruction for configuring Kaggle API credentials."""
    print("\n" + "=" * 70)
    print(" KAGGLE CREDENTIALS NOT FOUND")
    print("=" * 70)
    print("To download raw datasets directly from Kaggle:")
    print("  1. Log into your Kaggle account: https://www.kaggle.com")
    print("  2. Go to Account Settings -> API -> Click 'Create New Token'")
    print("  3. Place downloaded 'kaggle.json' at: ~/.kaggle/kaggle.json")
    print("  4. Set permissions: chmod 600 ~/.kaggle/kaggle.json")
    print("Or set environment variables:")
    print("  export KAGGLE_USERNAME=your_username")
    print("  export KAGGLE_KEY=your_api_key")
    print("=" * 70 + "\n")


def download_dataset(name: str, config: dict, dry_run: bool = False) -> bool:
    """Download a specific dataset using the Kaggle CLI."""
    dest = config["dest"]
    slug = config["slug"]
    print(f"\n[KAGGLE] Downloading {name} ({slug}) -> {dest.relative_to(REPO_ROOT)}...")

    if dry_run:
        print(f"  [DRY-RUN] Would run: kaggle datasets download -d {slug} -p {dest} --unzip")
        print(f"  [DRY-RUN] Would run: kaggle datasets metadata -d {slug} -p {dest}")
        return True

    dest.mkdir(parents=True, exist_ok=True)
    cmd_download = [
        "kaggle",
        "datasets",
        "download",
        "-d",
        slug,
        "-p",
        str(dest),
        "--unzip",
    ]
    try:
        subprocess.run(cmd_download, check=True, capture_output=True, text=True)
        print(f"  OK: Downloaded and extracted into {dest}")
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: Download failed: {e.stderr.strip()}", file=sys.stderr)
        return False

    # Download metadata for license confirmation
    cmd_meta = [
        "kaggle",
        "datasets",
        "metadata",
        "-d",
        slug,
        "-p",
        str(dest),
    ]
    try:
        subprocess.run(cmd_meta, check=False, capture_output=True, text=True)
    except Exception:
        pass

    return True


def bootstrap_offline_fixtures() -> None:
    """Bootstrap deterministic, realistic offline raw fixtures if kaggle credentials are absent.

    Ensures downstream converter scripts and evaluation pipelines function
    seamlessly in offline evaluation environments without external network dependencies.
    """
    print("\n[BOOTSTRAP] Ensuring deterministic offline sample files exist in data/raw/kaggle/...")

    # 1. FinancialPhraseBank fixture
    pb_dir = DATASETS["phrasebank"]["dest"]
    pb_dir.mkdir(parents=True, exist_ok=True)
    pb_file = pb_dir / "all-data.csv"
    if not pb_file.exists():
        sample_pb_rows = [
            'neutral,"According to the company, the net loss will be between EUR 1.5 million and EUR 2.0 million."',
            'positive,"Operating profit rose by 14% to EUR 12.3 million from EUR 10.8 million."',
            'negative,"Operating loss for the period was EUR 1.8 million, compared with an operating profit of EUR 0.4 million."',
            'positive,"Sales increased by 7.4% to EUR 27.2 million from EUR 25.3 million in the corresponding period of 2007."',
            'neutral,"The contract has a value of EUR 3.5 million and will run for three years."',
            'negative,"Net sales decreased by 8% to EUR 29.8 million from EUR 32.4 million."',
            'positive,"Net profit totaled EUR 4.2 million, up from EUR 1.9 million."',
            'negative,"The closure of the plant will result in the loss of approximately 140 jobs."',
            'neutral,"The company has signed an agreement with an international distributor."',
            'positive,"EBITDA grew to EUR 8.9 million from EUR 6.4 million in the previous year."',
        ]
        with open(pb_file, "w", encoding="latin-1") as f:
            f.write("\n".join(sample_pb_rows) + "\n")
        print(f"  OK: Bootstrapped sample {pb_file.relative_to(REPO_ROOT)}")

    # 2. Ticker News fixture
    tn_dir = DATASETS["ticker_news"]["dest"]
    tn_dir.mkdir(parents=True, exist_ok=True)
    tn_file = tn_dir / "financial_news.csv"
    if not tn_file.exists():
        headers = "headline,summary,published_at,ticker,sentiment_label,sentiment_score\n"
        tn_rows = [
            'Apex Industrials Faces Extended Foundry Outage Following Thermal Explosion,"Production at Apex main steel foundry halted indefinitely as safety inspectors conduct formal review.","2026-03-15T08:30:00Z",APEX,negative,-0.82',
            'Titan Steel Secures $250M Multi-Year Auto Supply Contract,"Titan Steel Corporation announced exclusive supply contract with major European automotive consortium.","2026-03-15T09:15:00Z",TSTEL,positive,0.76',
            'Quantum Semiconductor Discloses 8-Week Yield Contraction,"Advanced node silicon fabrication yields dipped 4.2% due to chemical supplier purity defects.","2026-03-15T10:00:00Z",QSEM,negative,-0.68',
            'Global Logistics Expedites Freight Capacity in Southeast Corridor,"Global Logistics added 12 regional intermodal routes following port congestion resolution.","2026-03-15T11:20:00Z",GLOG,positive,0.58',
            'Vanguard Auto Lowers FY26 Delivery Targets by 5%,"Vehicle assembly guidance trimmed citing semiconductor inventory bottlenecks and battery shipping delays.","2026-03-15T13:45:00Z",VAUTO,negative,-0.61',
            'Solaris Energy Commences Commercial Operation of 400MW Solar Facility,"Solaris Energy grid interconnect approved ahead of schedule with long-term utility PPA.","2026-03-15T14:10:00Z",SLEN,positive,0.85',
        ]
        with open(tn_file, "w", encoding="utf-8") as f:
            f.write(headers + "\n".join(tn_rows) + "\n")
        print(f"  OK: Bootstrapped sample {tn_file.relative_to(REPO_ROOT)}")

    # 3. Stock tweets fixture
    tw_dir = DATASETS["tweets"]["dest"]
    tw_dir.mkdir(parents=True, exist_ok=True)
    tw_file = tw_dir / "stock_tweets.csv"
    if not tw_file.exists():
        tw_headers = "tweet,stock,date,forward_return_1d,forward_return_7d,volatility,textblob_polarity\n"
        tw_rows = [
            '"$APEX massive supply chain breakdown reported at Ohio foundry. Puts printing heavy tomorrow",APEX,2026-03-15,-0.042,-0.088,0.28,-0.45',
            '"$TSTEL balance sheet looking like a fortress after today new commercial contract announcement",TSTEL,2026-03-15,0.035,0.062,0.18,0.52',
            '"$QSEM chip wafer allocation issues look worse than guided. Fab capacity constrained",QSEM,2026-03-15,-0.028,-0.054,0.24,-0.38',
            '"$GLOG shipping volumes rebounding strongly through west coast terminals",GLOG,2026-03-15,0.019,0.041,0.15,0.40',
            '"$VAUTO suppliers delaying parts shipments again. Tough quarter ahead for deliveries",VAUTO,2026-03-15,-0.031,-0.069,0.22,-0.35',
            '"$SLEN commercial solar power plant goes online 2 weeks early. Solid execution",SLEN,2026-03-15,0.041,0.082,0.19,0.60',
        ]
        with open(tw_file, "w", encoding="utf-8") as f:
            f.write(tw_headers + "\n".join(tw_rows) + "\n")
        print(f"  OK: Bootstrapped sample {tw_file.relative_to(REPO_ROOT)}")

    # 4. Financial transactions & user credit fixture
    tx_dir = DATASETS["transactions"]["dest"]
    tx_dir.mkdir(parents=True, exist_ok=True)
    users_file = tx_dir / "users.csv"
    cards_file = tx_dir / "cards.csv"

    if not users_file.exists():
        u_headers = "user_id,credit_score,total_debt,yearly_income,mcc_dominant\n"
        u_rows = [
            "usr-1001,780,12000,95000,5411",  # Supermarkets (Consumer Staples)
            "usr-1002,710,24000,82000,4814",  # Telecommunications
            "usr-1003,660,38000,58000,5541",  # Service Stations (Energy)
            "usr-1004,610,48000,46000,4511",  # Airlines (Transportation/Travel)
            "usr-1005,740,15000,105000,5732",  # Electronics Stores (Technology)
            "usr-1006,680,29000,72000,5044",  # Office Equipment (Commercial Services)
            "usr-1007,790,8000,120000,8011",  # Healthcare
            "usr-1008,630,42000,52000,1520",  # General Contractors (Real Estate / Construction)
        ]
        with open(users_file, "w", encoding="utf-8") as f:
            f.write(u_headers + "\n".join(u_rows) + "\n")
        print(f"  OK: Bootstrapped sample {users_file.relative_to(REPO_ROOT)}")

    if not cards_file.exists():
        c_headers = "card_id,user_id,credit_limit,card_type\n"
        c_rows = [
            "crd-01,usr-1001,25000,Visa Signature",
            "crd-02,usr-1002,15000,Mastercard Platinum",
            "crd-03,usr-1003,10000,Amex Everyday",
            "crd-04,usr-1004,8000,Discover it",
            "crd-05,usr-1005,30000,Visa Infinite",
            "crd-06,usr-1006,12000,Mastercard World",
            "crd-07,usr-1007,35000,Visa Signature",
            "crd-08,usr-1008,9000,Mastercard Standard",
        ]
        with open(cards_file, "w", encoding="utf-8") as f:
            f.write(c_headers + "\n".join(c_rows) + "\n")
        print(f"  OK: Bootstrapped sample {cards_file.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Kaggle datasets for S&P Sentinel")
    parser.add_argument(
        "--dataset",
        choices=list(DATASETS.keys()) + ["all"],
        default="all",
        help="Specific dataset to fetch or 'all'",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing downloads",
    )
    parser.add_argument(
        "--bootstrap-only",
        action="store_true",
        help="Only generate offline sample fixtures without calling Kaggle API",
    )
    args = parser.parse_args()

    print("=" * 70)
    print(" S&P Sentinel Kaggle Acquisition Manager")
    print("=" * 70)

    if args.bootstrap_only:
        bootstrap_offline_fixtures()
        print("\nAll offline fixtures prepared successfully.")
        return

    cli_available = check_kaggle_cli()
    creds_available = check_kaggle_credentials()

    if not cli_available or not creds_available:
        if not cli_available:
            print("[INFO] 'kaggle' CLI not installed in current environment.")
        if not creds_available:
            print_credential_help()

        print("[INFO] Falling back to reproducible offline fixtures in data/raw/kaggle/.")
        bootstrap_offline_fixtures()
        print("\nOffline sample fixtures are ready for conversion pipelines.")
        return

    # If Kaggle CLI and credentials are ready, proceed with downloads
    targets = (
        list(DATASETS.keys()) if args.dataset == "all" else [args.dataset]
    )
    all_success = True
    for name in targets:
        success = download_dataset(name, DATASETS[name], dry_run=args.dry_run)
        if not success:
            all_success = False

    if all_success:
        print("\nAll Kaggle dataset downloads completed successfully.")
    else:
        print("\nSome downloads encountered errors. Bootstrapping fallback samples...")
        bootstrap_offline_fixtures()


if __name__ == "__main__":
    main()
