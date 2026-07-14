import asyncio

from app.db.models import RawItem, Source
from app.services.ingestion import normalize_item
from app.sources.sec_filings import (
    COMPANY_TICKERS_URL,
    SecFilingsConnector,
    fetch_company_ticker_ciks,
    format_cik,
    parse_company_ticker_ciks,
    parse_sec_date,
    sec_filing_url,
)


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


def test_sec_filings_connector_normalizes_injected_ticker_cik_map() -> None:
    connector = SecFilingsConnector(
        tickers=[" tsla ", "MU"],
        limit=2,
        user_agent="SignalLens test",
        ticker_cik_map={"tsla": "1318605", "bad": "not-a-cik"},
    )

    assert connector.tickers == ["TSLA", "MU"]
    assert connector.ticker_cik_map == {"TSLA": "0001318605"}


def test_parse_company_ticker_ciks_reads_official_sec_mapping() -> None:
    assert parse_company_ticker_ciks(
        {
            "0": {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla, Inc."},
            "1": {"cik_str": "2488", "ticker": "AMD", "title": "Advanced Micro Devices"},
            "2": {"cik_str": None, "ticker": "BAD", "title": "Bad Row"},
            "3": {"cik_str": 0, "ticker": "ZERO", "title": "Zero Row"},
            "4": "not-a-row",
        }
    ) == {
        "TSLA": "0001318605",
        "AMD": "0000002488",
    }


def test_fetch_company_ticker_ciks_uses_official_sec_mapping_url() -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, dict[str, object]]:
            return {"0": {"cik_str": 1318605, "ticker": "TSLA"}}

    class FakeClient:
        requested_url: str | None = None

        async def get(self, url: str) -> FakeResponse:
            self.requested_url = url
            return FakeResponse()

    client = FakeClient()

    assert asyncio.run(fetch_company_ticker_ciks(client)) == {"TSLA": "0001318605"}
    assert client.requested_url == COMPANY_TICKERS_URL


def test_format_cik_rejects_invalid_values() -> None:
    assert format_cik(1318605) == "0001318605"
    assert format_cik("0000723125") == "0000723125"
    assert format_cik("not-a-cik") is None
    assert format_cik(0) is None


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
    assert item.source_quality_score == 0.9
    assert item.stock_impact_score == 0.6
    assert item.summary_detailed is not None
    assert "Filing summary: Watched company (MU) filed 8-K." in item.summary_detailed
    assert "Stock-watch relevance: official SEC disclosure" in item.summary_detailed
