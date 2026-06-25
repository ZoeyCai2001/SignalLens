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
- GitHub ingestion action
- Hugging Face model ingestion action
- Selected RSS feed ingestion action
- Kimi summarization action for stored feed items
- Manual URL submission
- Save, hide, and mark-important item actions
- Search and filters over stored feed items
- Daily digest panel generated from stored feed items
- Topic watchlist display
- Stock watchlist signal counts
