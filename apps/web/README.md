# SignalLens Web

This is the Next.js frontend for SignalLens.

## Local Development

From the repository root:

```bash
pnpm install
pnpm web:dev
```

Open:

```text
http://127.0.0.1:3000
```

The dashboard expects the FastAPI backend at:

```text
http://127.0.0.1:8000
```

## Current Views

- Ranked feed
- AI Stock Watchlist
- Source health
- Hacker News ingestion action
- arXiv ingestion action
- Kimi summarization action for stored feed items
- Manual URL submission
- Save, hide, and mark-important item actions
