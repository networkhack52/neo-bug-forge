import datetime as dt
import time

from app import dates, documents, export


def test_parses_labelled_review_dates():
    assert dates.to_iso(dates.parse_stated_date("Last Reviewed: March 14, 2025")) == "2025-03-14"
    assert dates.to_iso(dates.parse_stated_date("Effective Date: 2024-01-03")) == "2024-01-03"
    assert dates.to_iso(dates.parse_stated_date("Last updated 14 March 2023")) == "2023-03-14"
    assert dates.to_iso(dates.parse_stated_date("Report date: 12/31/2024")) == "2024-12-31"


def test_ignores_unlabelled_dates_and_junk():
    # A date with no freshness label must not be mistaken for the review date.
    assert dates.parse_stated_date("We were founded in 2019-05-05 as a company.") is None
    assert dates.parse_stated_date("no date at all here") is None


def test_picks_most_recent_labelled_date():
    text = "Effective Date: 2022-01-01. This was Last Reviewed: 2025-06-30."
    assert dates.to_iso(dates.parse_stated_date(text)) == "2025-06-30"


def test_months_old_and_staleness_math():
    old = dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc).timestamp()
    assert dates.months_old(old) > 24
    assert dates.months_old(None) is None


def test_source_dates_prefers_stated_over_file():
    text = "Information Security Policy. Last Reviewed: 2025-03-14."
    out = documents.source_dates("text", text.encode(), text)
    assert out["date_basis"] == "stated"
    assert dates.to_iso(out["source_date"]) == "2025-03-14"
    assert out["file_date"] is not None  # upload time as the file date


def test_source_dates_falls_back_to_file_date():
    text = "A policy with no stated review date anywhere."
    out = documents.source_dates("text", text.encode(), text)
    assert out["date_basis"] == "file"
    assert out["stated_date"] is None
    assert out["source_date"] == out["file_date"]


def test_export_source_cell_appends_date_and_stale_note():
    fresh = {"citations": [{"title": "Acme_Policy.pdf", "text": "AES-256 at rest",
                            "kind": "document", "date": "2025-03-14", "date_basis": "stated",
                            "stale": False}]}
    cell = export.source_cell(fresh)
    assert "(reviewed 2025-03-14)" in cell

    stale = {"citations": [{"title": "Old_Policy.pdf", "text": "quarterly reviews",
                            "kind": "document", "date": "2019-01-01", "date_basis": "file",
                            "stale": True}]}
    cell = export.source_cell(stale)
    assert "(dated 2019-01-01, review recommended)" in cell
