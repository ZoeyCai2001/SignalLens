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
