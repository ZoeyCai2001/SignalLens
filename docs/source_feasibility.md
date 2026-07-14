# SignalLens Source Feasibility

Last checked: 2026-06-27

This document is the Phase 0 source feasibility deliverable from the PRD. It is intentionally conservative: SignalLens should prefer stable APIs, public RSS/Atom feeds, and user-provided manual links before any fragile scraping or expensive social-data integration.

## MVP Source Decisions

| Source | MVP decision | API key | Cost posture | Compliance and risk notes | Current implementation |
| --- | --- | --- | --- | --- | --- |
| arXiv | Include | No | Free with conservative polling | Official API/RSS use is acceptable if SignalLens respects rate limits, links users back to arXiv, and avoids redistributing full papers without permission. arXiv asks legacy API/RSS users to make no more than one request every three seconds. | Implemented connector and ingestion route |
| Hacker News | Include | No | Free | Official Firebase API exposes public HN data and currently states no rate limit, but SignalLens should still poll conservatively and store URLs/metadata rather than treating comments as a bulk corpus. | Implemented connector, ingestion route, bounded top-comment preview, and deterministic discussion summaries |
| GitHub Search and followed repositories | Include | Optional | Free enough for MVP | GitHub REST allows unauthenticated public-data requests but limits them to 60 requests/hour; authenticated requests raise the budget. Use public repository metadata only and configure `GITHUB_TOKEN` if rate limits become painful. | Implemented search connector, optional token support, ingestion route, followed-repository source runs, and approximate stars-per-day traction signal |
| Hugging Face Hub | Include | Optional | Free enough for MVP | Hub APIs expose model, dataset, and Space metadata; API calls are subject to HF-wide rate limits. Keep to metadata, rankings, and links. | Implemented connector and ingestion route for models, datasets, and Spaces, with downloads/likes used as local traction signals |
| Selected RSS feeds | Include | No | Free | Best source class for company blogs and AI news. Store titles, URLs, publication metadata, and excerpts where provided by the feed; do not crawl full articles unless allowed. | Implemented connector and ingestion route |
| Product Hunt | Include if token is available | Yes | Free for personal/non-commercial prototype | Product Hunt API is GraphQL, token-gated, public-scope by default, and asks for attribution. Its docs say commercial use requires contacting Product Hunt. | Implemented connector, skipped cleanly without token |
| Alpha Vantage | Include as initial finance provider | Yes | Free tier is very limited; paid tier starts if volume grows | Free key is enough for light daily news/price polling. Alpha Vantage says most endpoints are free under the standard limit of 25 requests/day; premium plans remove daily limits. | Implemented news and daily price connectors, skipped cleanly without key |
| SEC EDGAR submissions | Include for watched public companies | No | Free official data | Good fit for 8-K, 10-Q, and 10-K filing metadata. Use a descriptive `SEC_USER_AGENT`, poll conservatively, and link to filings rather than storing full documents. | Implemented watched-ticker filings connector with official ticker-to-CIK fallback |
| NewsAPI | Defer | Yes | Free only for development/testing; paid plan required beyond dev use | Useful fallback for broad news, but the free Developer plan is limited to development/testing and 100 requests/day. Not needed while RSS and Alpha Vantage cover MVP. | Not implemented |
| GDELT | Research candidate | No for public data; BigQuery costs may apply | Potentially free data, but analysis may require BigQuery usage | Strong candidate for broad global news/event discovery, but it is noisy and large. Use only after MVP source quality controls are stronger. | Not implemented |
| X/Twitter | Defer automated ingestion | Yes for API use | Pay-per-use | High signal but cost-sensitive. X describes pay-per-use API pricing and rate limits by endpoint. Add automated ingestion only after a concrete account/query list and spend cap exist; do not scrape login-protected or restricted surfaces. | Manual URL submission plus an X Account Watch source template for attribution |
| Reddit | Defer | Yes for API use | Access/rules require review before product use | Valuable for community signals, but API access rules and commercial limitations need a dedicated review. Prefer RSS/manual links first. | Not implemented |
| Xiaohongshu | Manual/public-feed prototype only; no scraping | Unknown | Unknown | Important for Chinese consumer AI signals, but SignalLens must not bypass login, captcha, anti-bot, or device controls. Use manual URL submission first; consider only official/open-platform or reputable compliant data providers later. | Manual URL submission, an XHS Manual Watch source template, and optional public Chinese/XHS RSS support |

## API Key Checklist

Required for current optional MVP features:

- `MOONSHOT_API_KEY`: LLM summarization/classification via Kimi Coding API. `KIMI_API_KEY` is accepted as a legacy compatibility alias, but new setups should use `MOONSHOT_API_KEY`.
- `ALPHA_VANTAGE_API_KEY`: stock news and daily price ingestion.
- `PRODUCT_HUNT_API_TOKEN`: Product Hunt public launch metadata.
- `SEC_USER_AGENT`: descriptive contact string for SEC EDGAR submissions access.

Optional or future:

- `GITHUB_TOKEN`: raises GitHub API limits if unauthenticated usage is too tight.
- `HUGGING_FACE_TOKEN`: only needed if public Hub endpoints become rate-limited or gated data is intentionally supported.
- `NEWSAPI_KEY`: only if NewsAPI is added for development/testing or a paid plan is chosen.
- X/Twitter credentials: only after a spend cap and query/account plan are approved.
- Reddit credentials: only after API access-rule review.

Do not commit secrets. Keep local keys in `.env`; keep `.env.example` limited to variable names and safe placeholders.

## Cost Estimate

For the local personal MVP, the recommended monthly source-data cost is `$0` except for:

- LLM usage through Kimi Coding API, controlled by filtering before summarization.
- Alpha Vantage if the 25-request/day free tier is too small.
- Product Hunt only if a token is available under acceptable use.

Avoid paid social APIs until the dashboard proves daily value from free/low-cost sources.

## Risk Notes

- Store source attribution and original URLs for every item.
- Prefer metadata and short excerpts over full article storage.
- Treat source failure as normal; record skipped and failed source runs instead of failing the entire ingestion cycle.
- Keep finance outputs informational only. Do not produce buy, sell, or hold advice.
- Re-check pricing and terms before enabling any paid or social connector.

## References

- [arXiv API Terms of Use](https://info.arxiv.org/help/api/tou.html)
- [Hacker News official API](https://github.com/HackerNews/API)
- [GitHub REST API rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [Hugging Face Hub API endpoints](https://huggingface.co/docs/hub/en/api)
- [Product Hunt API documentation](https://api.producthunt.com/v2/docs)
- [Alpha Vantage documentation](https://www.alphavantage.co/documentation/)
- [Alpha Vantage premium plans](https://www.alphavantage.co/premium/)
- [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [NewsAPI pricing](https://newsapi.org/pricing)
- [GDELT data access](https://www.gdeltproject.org/data.html)
- [X Developer Platform overview](https://docs.x.com/overview)
- [X API rate limits](https://docs.x.com/x-api/fundamentals/rate-limits)
- [Reddit API documentation](https://www.reddit.com/dev/api/)
