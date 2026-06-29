from app.db.models import RawItem, Source
from app.services.ingestion import normalize_item
from app.sources.sec_filings import SecFilingsConnector, parse_sec_date, sec_filing_url


def test_sec_filings_connector_converts_recent_filings_to_raw_items() -> None:
    connector = SecFilingsConnector(tickers=["MU"], limit=2, user_agent="SignalLens test")

    items = connector._payload_to_raw_items(
        ticker="MU",
        cik="0000723125",
        payload={
            "name": "MICRON TECHNOLOGY INC",
            "filings": {
                "recent": {
                    "form": ["8-K", "4", "10-Q"],
                    "accessionNumber": [
                        "0000723125-26-000010",
                        "0000000000-26-000001",
                        "0000723125-26-000011",
                    ],
                    "filingDate": ["2026-06-25", "2026-06-24", "2026-06-23"],
                    "reportDate": ["2026-06-24", "2026-06-24", "2026-06-01"],
                    "primaryDocument": ["mu-8k.htm", "ownership.xml", "mu-10q.htm"],
                    "primaryDocDescription": ["Current report", "Ownership", "Quarterly report"],
                }
            },
        },
    )

    assert [item.raw_title for item in items] == [
        "MU 8-K: Current report filed 2026-06-25",
        "MU 10-Q: Quarterly report filed 2026-06-23",
    ]
    assert items[0].external_id == "0000723125:0000723125-26-000010"
    assert items[0].raw_author == "SEC EDGAR"
    assert items[0].raw_metadata["ticker"] == "MU"
    assert items[0].raw_metadata["form"] == "8-K"
    assert "MICRON TECHNOLOGY INC (MU) filed SEC form 8-K." in (items[0].raw_text or "")
    assert items[0].published_at is not None


def test_sec_filing_url_uses_edgar_archive_path() -> None:
    assert sec_filing_url(
        cik="0000723125",
        accession="0000723125-26-000010",
        document="mu-8k.htm",
    ) == "https://www.sec.gov/Archives/edgar/data/723125/000072312526000010/mu-8k.htm"


def test_sec_date_parser_handles_invalid_values() -> None:
    assert parse_sec_date("2026-06-25") is not None
    assert parse_sec_date("not-a-date") is None


def test_sec_filing_normalizes_as_stock_company_event_without_ai_keyword() -> None:
    source = Source(
        id=1,
        name="SEC Filings",
        type="finance_filings",
        access_method="official_api",
    )
    raw = RawItem(
        id=1,
        raw_title="MU 8-K: Current report filed 2026-06-25",
        url="https://www.sec.gov/Archives/edgar/data/723125/example.htm",
        raw_text=(
            "MICRON TECHNOLOGY INC (MU) filed SEC form 8-K. "
            "Filing description: Current report."
        ),
        raw_metadata={
            "ticker": "MU",
            "cik": "0000723125",
            "form": "8-K",
        },
    )

    item = normalize_item(raw=raw, source=source)

    assert item is not None
    assert item.category == "stock_company_event"
    assert item.subcategory == "sec_filing"
    assert item.tickers == ["MU"]
    assert item.companies == ["Micron Technology"]
    assert item.stock_impact_score == 0.5
