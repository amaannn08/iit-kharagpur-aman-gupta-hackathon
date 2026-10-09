"""Contract tests for the committed real public datasets (data/real, data/train)."""

import csv
import importlib.util
import json

import pytest

from sentinel.config import settings
from sentinel.contracts.records import SourceType, TimestampQuality
from sentinel.ingestion.adapters import NewsAdapter, SocialAdapter

DATA = settings.data_dir

_spec = importlib.util.spec_from_file_location(
    "convert_real", settings.base_dir / "scripts" / "data" / "convert_real.py"
)
convert_real = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(convert_real)


@pytest.mark.parametrize(
    "rel_path,adapter,source_type,quality",
    [
        (
            "real/polygon_news/polygon_news.csv",
            NewsAdapter,
            SourceType.NEWS,
            TimestampQuality.ORIGINAL,
        ),
        ("real/gdelt/snapshot.csv", NewsAdapter, SourceType.NEWS, TimestampQuality.ORIGINAL),
        (
            "real/stock_tweets/sample.csv",
            SocialAdapter,
            SourceType.SOCIAL,
            TimestampQuality.DATE_ONLY,
        ),
    ],
)
def test_real_feeds_load_through_adapters_with_honest_provenance(
    rel_path, adapter, source_type, quality
):
    records = adapter.load_from_csv(DATA / rel_path)
    assert len(records) >= 1000
    assert len({r.record_id for r in records}) == len(records)
    for r in records:
        assert r.is_synthetic is False
        assert r.source_type == source_type
        assert r.timestamp_quality == quality
        assert r.published_at is not None
        assert r.primary_entity_id in (None, "")  # no gold hints leak into the engine


def test_every_real_folder_has_license_and_manifest_entry():
    manifest = json.loads((DATA / "manifest.json").read_text())
    by_path = {d["file_path"]: d for d in manifest["datasets"]}
    for folder in ["real/polygon_news", "real/stock_tweets", "real/gdelt",
                   "train/hf_fin_topic", "train/hf_fin_sentiment", "train/phrasebank"]:  # fmt: skip
        assert (DATA / folder / "LICENSE").exists(), folder
        files = [p for p in (DATA / folder).glob("*.csv")]
        assert files, folder
        for p in files:
            entry = by_path[str(p.relative_to(settings.base_dir))]
            assert entry["is_synthetic"] is False
            assert entry["source"].startswith("http")
    assert by_path["data/train/phrasebank/sample.csv"]["license"] == "CC BY-NC-SA 3.0"
    assert by_path["data/real/polygon_news/polygon_news.csv"]["license"] == "MIT"


def test_gdelt_parser_keeps_only_finance_rows_with_titles():
    def row(record, themes, title):
        cols = [""] * 27
        cols[0], cols[1], cols[4], cols[7] = (
            record,
            "20261009081500",
            "https://example.org/a",
            themes,
        )
        cols[26] = f"<PAGE_TITLE>{title}</PAGE_TITLE>" if title else ""
        return "\t".join(cols)

    lines = [
        row("1", "ECON_INFLATION,12;TAX_FNCACT,3", "Central bank raises rates to fight inflation"),
        row("2", "SPORTS,1", "Local team wins the championship final match"),
        row("3", "ECON_DEBT,4", ""),
        row("4", "SANCTIONS,9", "Short"),
    ]
    out = convert_real.parse_gkg_rows(lines)
    assert [r["record_id"] for r in out] == [convert_real.rid("gd", "1")]
    assert out[0]["published_at"] == "2026-10-09T08:15:00Z"
    assert out[0]["body"] == ""


def test_hf_label_files_have_expected_label_space():
    with open(DATA / "train/hf_fin_topic/topic_valid.csv", newline="") as f:
        labels = {int(r["label"]) for r in csv.DictReader(f)}
    assert labels == set(range(20))
    with open(DATA / "train/hf_fin_sentiment/sent_valid.csv", newline="") as f:
        assert {int(r["label"]) for r in csv.DictReader(f)} == {0, 1, 2}
