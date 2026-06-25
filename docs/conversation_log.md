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
