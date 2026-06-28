# Conversation Log

This file records project-shaping conversation summaries in English.

## 2026-06-25

User request:

- A PRD has been added under the project folder.
- Connect the project to `ZoeyCai2001/SignalLens.git`.
- Keep the design and development process in English, including conversation records.
- Commit changes and push to the remote.
- Make the technical design first.

Assistant response plan:

- Read the PRD.
- Create an initial technical design before implementation.
- Add process documentation that keeps project work in English.
- Initialize git because the folder is not yet a repository.
- Add the GitHub remote.
- Commit and push the initial documentation foundation.

Follow-up decisions:

- Use budget-conscious free and open sources first where possible.
- Use the user's Kimi Coding API key for LLM tasks.
- The working Kimi endpoint is `https://api.kimi.com/coding/v1/messages`.
- The available model is `kimi-for-coding`.
- The API uses an Anthropic-style Messages request shape, not the normal OpenAI chat completions path.
- GitHub SSH authentication was fixed by using an account-level SSH key instead of a read-only deploy key.
- Begin implementation with a backend-first MVP scaffold.

Implementation progress:

- Added a FastAPI backend scaffold.
- Added local Docker infrastructure for PostgreSQL with pgvector and Redis.
- Added the first SQLAlchemy models and Alembic migration.
- Added seeded AI Stock Watchlist support for MU, MRVL, and SNDK.
- Added an initial Hacker News connector using the public Firebase API.
- Added DB-backed feed, source health, watchlist, and ingestion routes.
- Added an arXiv connector using the public Atom API.
- Added a Kimi-backed item summarization endpoint that stores summaries on feed items.
- Added the first Next.js frontend dashboard for feed, stock watchlist, source health, ingestion, and summarization actions.
- Added manual URL submission and feed actions for save, hide, and mark important.
- Added keyword and filter search over stored feed items, with dashboard search controls.
- Added deterministic daily digest generation and a dashboard digest panel.
- Added topic watchlist persistence, seed data, API endpoints, and dashboard display.
- Added GitHub public repository ingestion for open-source AI project signals.
- Added stock-linked signal summary and ticker detail endpoints, with dashboard signal counts.
- Added Hugging Face public model ingestion for model-release and open-source LLM signals.
- Added selected RSS feed ingestion for AI company and research blog signals.
- Added deterministic event clustering and dashboard event cluster display.
- Added manual Kimi-backed feed item classification with dashboard action.
- Added a local APScheduler-backed ingestion runner for one-off or continuous source refresh cycles.
- Added persisted dashboard alerts with default high-impact stock and important AI development rules.
- Added optional Product Hunt ingestion for AI product launches, using the official API when a token is configured.
- Added optional Alpha Vantage stock-news ingestion for watched AI ticker news and sentiment metadata.
- Added editable stock watchlist APIs and a dashboard control for adding new watched tickers.
- Added configurable Chinese public RSS ingestion and a dashboard panel for Chinese social trend signals.
- Added editable topic and product-category watchlist APIs with dashboard add controls.
- Added editable alert rule APIs and dashboard controls for custom alert rules.
- Added source enable/disable APIs and dashboard controls; ingestion now skips disabled sources.
- Added bounded LLM batch processing for top feed items, plus a dashboard control to summarize the highest-priority items without clicking each card.
- Added per-ticker stock briefing APIs and a dashboard drill-down panel with urgency, sentiment counts, key themes, and recent stock-linked signal timeline.
- Added dashboard controls for removing stock and topic watchlist entries, using the existing delete APIs.
- Added dashboard controls for changing watchlist priority, pinning stocks/topics, and toggling topic digest inclusion through the existing patch APIs.
- Added persisted user preferences for configurable feed ranking weights, plus preferences APIs and weighted feed ordering.
- Added dashboard ranking weight controls that read and update local preferences and refresh the ranked feed.
- Added deterministic stock attention scores to stock signal summaries, briefings, and the dashboard stock table.
- Added saved-only feed retrieval, unsave actions, and a dashboard Saved Items panel.
- Added a Markdown daily digest export endpoint and dashboard copy control.
- Added dashboard stock watchlist detail editing for optional holding status, shares, average cost, grouping, sector metadata, and notes.
- Added interactive first-class module navigation that filters the main feed by Dashboard, AI Trends, Research, Products, AI Stocks, Chinese Social, or Daily Digest.
- Added persisted daily digest snapshots, snapshot list/create APIs, scheduled snapshot generation, and a dashboard save control.
- Added optional Alpha Vantage daily price ingestion, stock price persistence, market snapshots in stock APIs, and dashboard price/change display.
- Added richer stock watchlist summaries with high-impact counts, latest AI-related event, sentiment counts, and dashboard table columns.
- Added date range, language, and minimum-importance search filters to the API and dashboard search panel.
- Added feed item detail API and dashboard Details panel with source text, score explanation, entities, products, and action state.
- Added editable source operations metadata for priority, polling interval, rate limit, and terms notes in the dashboard Source Health panel.
- Added an event cluster detail API and dashboard evidence drill-down so related source items can be inspected from one cluster card.
- Added system readiness reporting for LLM/API integration configuration and a dashboard panel showing readiness plus live local counts.
- Added lightweight natural-language search intent parsing for recent/latest queries, stock tickers, product/research/social categories, Chinese language signals, saved-item searches, and high-importance filters.
- Added deterministic enrichment for manual URL submissions so pasted AI product, research, stock, and social-trend links are categorized, scored, summarized, and routed into the right dashboard modules without requiring an LLM call.
- Added dashboard controls for enabling, disabling, and deleting alert rules; disabling a rule now suppresses its active alerts from the default alert view.
- Added source run history APIs and a dashboard run trail so recent ingestion successes, skips, failures, counts, and error messages are visible from Source Health.
- Added a registered source runner endpoint and Source Health row action so individual configured sources can be triggered directly while preserving source-run status tracking.
- Added a natural-language search POST endpoint that returns deterministic intent filters with matching feed items, keeping search explainable and LLM-free for the MVP.
- Connected the dashboard search box to the natural-language search endpoint and added interpreted filter chips for zero-cost explainable search.
- Added the Phase 0 source feasibility table with API-key checklist, cost posture, and compliance risk notes for MVP and deferred sources.
- Added safe integration setup metadata to `/api/health` and surfaced missing optional API keys/feed configuration in the System Readiness panel without exposing secrets.
- Expanded research and product summaries with contribution/method/use-case/audience/traction fields, including deterministic detail scaffolding before any LLM call.
- Added a topic briefing API for future Topic pages, grouping recent items by source, research papers, products, companies, and activity timeline.
- Connected topic briefings to the dashboard with selectable topics, trending sources, related papers/products/companies, activity buckets, and a recent-topic timeline.
- Added an inline stock price history chart to stock briefings using existing market snapshot history.
- Added a full ingestion cycle API and dashboard action that runs core ingestion, alert generation, and daily digest snapshotting from the web UI.
- Promoted Saved Items into the primary dashboard navigation so the PRD category views include a dedicated saved-item feed.
- Added an inline "Why am I seeing this?" explanation to every feed card using stored relevance notes and deterministic score signals.
- Added persisted classification confidence for feed items and surfaced it in the dashboard score grid and explanations.
- Expanded stock briefings into a fuller stock-detail view with AI relevance summary, theme breakdown, market-impact event buckets, notes, timeline, and price context.
- Added structured stock-event classification details to each stock timeline item, including event type, possible market impact, confidence, time sensitivity, summary, and uncertainties.
- Enriched event clusters with main summaries, confidence, importance, earliest/latest source timing, and compact timelines in the dashboard.
- Added source-watchlist registration so followed blogs, repositories, companies, and RSS feeds can be tracked from Source Health, with custom RSS feeds runnable through the existing connector.
- Added preferred and blocked source preferences so source credibility can influence ranking and noisy sources can be hidden from the feed.
- Added PRD-aligned daily digest sections for GitHub/Hugging Face highlights and saved items to read later.
- Added persisted product-category watchlists with dashboard controls and digest inclusion toggles.
- Added product-category briefing APIs and dashboard drill-downs for matched product launches, sources, companies, activity, and recent signals.
- Added a bounded watchlist-interest ranking boost so stock, topic, and product watchlists directly influence the main feed order.
- Added cross-source cluster alert generation so repeated signals across multiple sources can create dashboard alerts.
- Added source reliability attention signals so repeated connector failures are visible in Source Health.
- Added last-success timestamps to Source Health so a recent failure no longer hides when a source last worked.
- Added bounded Hacker News top-comment previews so developer discussion can inform classification and summaries without broad comment crawling.
- Added GitHub stars-per-day traction metadata so fast-growing open-source AI repositories stand out without extra API calls.
- Expanded Hugging Face ingestion from model-only updates to a bounded mixed feed of models, datasets, and Spaces.
- Added deterministic source credibility scoring so ranking and importance now reflect source quality instead of a flat default.
- Added optional GitHub token support and readiness reporting so repository ingestion can use higher public API limits when configured.
- Surfaced source credibility and lower-confidence signals in feed explanations so ranking reasons are easier to audit.
- Updated daily digest ranking to include source quality and classifier confidence, improving the trust profile of morning briefings.
