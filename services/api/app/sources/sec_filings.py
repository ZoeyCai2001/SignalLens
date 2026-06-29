from collections.abc import Mapping
from datetime import UTC, datetime, time
from typing import Any

import httpx

from app.sources.base import FetchCursor, FetchResult, RawItemInput, SourceConnector

COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

SEC_CIK_BY_TICKER = {
    "MU": "0000723125",
    "SNDK": "0001000180",
    "MRVL": "0001835632",
    "NVDA": "0001045810",
    "AMD": "0000002488",
    "AVGO": "0001730168",
    "TSM": "0001046179",
    "ASML": "0000937966",
    "AMAT": "0000006951",
    "LRCX": "0000707549",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "META": "0001326801",
    "ORCL": "0001341439",
    "ARM": "0001973239",
    "SMCI": "0001375365",
    "DELL": "0001571996",
    "HPE": "0001645590",
}

DEFAULT_SEC_FORMS = {"8-K", "10-K", "10-Q"}


class SecFilingsConnector(SourceConnector):
    source_name = "SEC Filings"
    source_type = "finance_filings"

    def __init__(
        self,
        tickers: list[str],
        limit: int = 25,
        user_agent: str = "SignalLens/0.1 personal research; configure SEC_USER_AGENT",
        forms: set[str] | None = None,
        ticker_cik_map: Mapping[str, str] | None = None,
    ) -> None:
        self.tickers = [ticker.strip().upper() for ticker in tickers if ticker.strip().upper()]
        self.limit = limit
        self.user_agent = user_agent
        self.forms = forms or DEFAULT_SEC_FORMS
        self.base_url = "https://data.sec.gov/submissions"
        self.ticker_cik_map = normalize_ticker_cik_map(ticker_cik_map or SEC_CIK_BY_TICKER)

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        items: list[RawItemInput] = []
        ticker_ciks = dict(self.ticker_cik_map)
        missing_tickers = [ticker for ticker in self.tickers if ticker not in ticker_ciks]
        cik_lookup_failed = False
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            if missing_tickers:
                try:
                    ticker_ciks.update(await fetch_company_ticker_ciks(client))
                except httpx.HTTPError:
                    cik_lookup_failed = True

            for ticker in self.tickers:
                cik = ticker_ciks.get(ticker)
                if not cik:
                    continue
                response = await client.get(f"{self.base_url}/CIK{cik}.json")
                response.raise_for_status()
                items.extend(self._payload_to_raw_items(ticker=ticker, cik=cik, payload=response.json()))
                if len(items) >= self.limit:
                    break

        return FetchResult(
            items=items[: self.limit],
            next_cursor=FetchCursor(
                metadata={
                    "last_limit": self.limit,
                    "unresolved_tickers": [
                        ticker for ticker in self.tickers if ticker not in ticker_ciks
                    ],
                    "cik_lookup_failed": cik_lookup_failed,
                }
            ),
        )

    def _payload_to_raw_items(
        self,
        ticker: str,
        cik: str,
        payload: dict[str, Any],
    ) -> list[RawItemInput]:
        company_name = str(payload.get("name") or ticker)
        recent = payload.get("filings", {}).get("recent", {})
        forms = recent.get("form") or []
        accession_numbers = recent.get("accessionNumber") or []
        filing_dates = recent.get("filingDate") or []
        report_dates = recent.get("reportDate") or []
        primary_documents = recent.get("primaryDocument") or []
        descriptions = recent.get("primaryDocDescription") or []

        rows = []
        for index, form in enumerate(forms):
            form_text = str(form or "").strip().upper()
            if form_text not in self.forms:
                continue
            accession = value_at(accession_numbers, index)
            filing_date = value_at(filing_dates, index)
            primary_document = value_at(primary_documents, index)
            if not accession or not filing_date or not primary_document:
                continue
            description = value_at(descriptions, index) or form_text
            report_date = value_at(report_dates, index)
            rows.append(
                RawItemInput(
                    source_name=self.source_name,
                    external_id=f"{cik}:{accession}",
                    url=sec_filing_url(cik=cik, accession=accession, document=primary_document),
                    raw_title=f"{ticker} {form_text}: {description} filed {filing_date}",
                    raw_text=build_sec_filing_text(
                        company_name=company_name,
                        ticker=ticker,
                        form=form_text,
                        filing_date=filing_date,
                        report_date=report_date,
                        description=description,
                    ),
                    raw_author="SEC EDGAR",
                    raw_metadata={
                        "ticker": ticker,
                        "cik": cik,
                        "company_name": company_name,
                        "form": form_text,
                        "accession_number": accession,
                        "filing_date": filing_date,
                        "report_date": report_date,
                        "primary_document": primary_document,
                        "primary_doc_description": description,
                    },
                    published_at=parse_sec_date(filing_date),
                )
            )
            if len(rows) >= self.limit:
                break
        return rows


async def fetch_company_ticker_ciks(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.get(COMPANY_TICKERS_URL)
    response.raise_for_status()
    return parse_company_ticker_ciks(response.json())


def parse_company_ticker_ciks(payload: dict[str, Any]) -> dict[str, str]:
    ticker_ciks: dict[str, str] = {}
    for entry in payload.values():
        if not isinstance(entry, dict):
            continue
        ticker = str(entry.get("ticker") or "").strip().upper()
        cik = format_cik(entry.get("cik_str"))
        if ticker and cik:
            ticker_ciks[ticker] = cik
    return ticker_ciks


def normalize_ticker_cik_map(mapping: Mapping[str, str]) -> dict[str, str]:
    ticker_ciks: dict[str, str] = {}
    for ticker, cik_value in mapping.items():
        normalized_ticker = str(ticker or "").strip().upper()
        cik = format_cik(cik_value)
        if normalized_ticker and cik:
            ticker_ciks[normalized_ticker] = cik
    return ticker_ciks


def format_cik(value: Any) -> str | None:
    if value is None:
        return None
    try:
        cik_number = int(str(value).strip())
    except ValueError:
        return None
    if cik_number <= 0:
        return None
    return f"{cik_number:010d}"


def value_at(values: list[Any], index: int) -> str | None:
    if index >= len(values):
        return None
    value = values[index]
    text = str(value or "").strip()
    return text or None


def sec_filing_url(cik: str, accession: str, document: str) -> str:
    cik_number = str(int(cik))
    accession_path = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_number}/{accession_path}/{document}"


def build_sec_filing_text(
    company_name: str,
    ticker: str,
    form: str,
    filing_date: str,
    report_date: str | None,
    description: str,
) -> str:
    parts = [
        f"{company_name} ({ticker}) filed SEC form {form}.",
        f"Filing description: {description}.",
        f"Filing date: {filing_date}.",
    ]
    if report_date:
        parts.append(f"Report date: {report_date}.")
    parts.append("Review the SEC filing for company-specific financial and risk disclosures.")
    return " ".join(parts)


def parse_sec_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.combine(datetime.strptime(value, "%Y-%m-%d").date(), time.min, tzinfo=UTC)
    except ValueError:
        return None
