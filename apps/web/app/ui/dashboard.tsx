"use client";

import {
  Activity,
  BarChart3,
  Bookmark,
  Bot,
  DatabaseZap,
  EyeOff,
  ExternalLink,
  FileText,
  Flag,
  FlaskConical,
  Loader2,
  Newspaper,
  RefreshCw,
  Search,
  Send,
  Star,
  TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

type FeedItem = {
  id: number;
  title: string;
  url: string;
  source_name: string;
  author: string | null;
  language: string;
  published_at: string | null;
  category: string;
  subcategory: string | null;
  tickers: string[];
  companies: string[];
  products: string[];
  topics: string[];
  sentiment: string;
  relevance_score: number;
  importance_score: number;
  novelty_score: number;
  source_quality_score: number;
  stock_impact_score: number;
  summary_short: string | null;
  summary_detailed: string | null;
  why_it_matters: string | null;
  is_saved: boolean;
  is_hidden: boolean;
  is_important: boolean;
};

type StockWatchlistItem = {
  ticker: string;
  company_name: string;
  exchange: string;
  sector: string;
  industry: string;
  priority: string;
  group_name: string;
  is_pinned: boolean;
  related_keywords: string[];
  related_companies: string[];
  related_ai_themes: string[];
  notes: string | null;
};

type SourceHealth = {
  id: number;
  name: string;
  type: string;
  access_method: string;
  enabled: boolean;
  latest_status: string;
  latest_error: string | null;
  last_started_at: string | null;
  last_finished_at: string | null;
  items_fetched: number;
  items_stored: number;
};

type LoadState = "idle" | "loading" | "running";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const navItems = [
  { label: "Dashboard", icon: Activity, active: true },
  { label: "AI Trends", icon: TrendingUp, active: false },
  { label: "Research", icon: FlaskConical, active: false },
  { label: "AI Stocks", icon: BarChart3, active: false },
  { label: "Products", icon: Bot, active: false },
  { label: "Search", icon: Search, active: false },
];

export function Dashboard() {
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [stocks, setStocks] = useState<StockWatchlistItem[]>([]);
  const [sources, setSources] = useState<SourceHealth[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [status, setStatus] = useState("Ready");
  const [error, setError] = useState<string | null>(null);
  const [busyItemId, setBusyItemId] = useState<number | null>(null);
  const [manualTitle, setManualTitle] = useState("");
  const [manualUrl, setManualUrl] = useState("");
  const [manualText, setManualText] = useState("");

  const fetchJson = useCallback(async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<T>;
  }, []);

  const refreshAll = useCallback(async () => {
    setLoadState("loading");
    setError(null);
    try {
      const [nextFeed, nextStocks, nextSources] = await Promise.all([
        fetchJson<FeedItem[]>("/api/feed?limit=30"),
        fetchJson<StockWatchlistItem[]>("/api/watchlist/stocks"),
        fetchJson<SourceHealth[]>("/api/sources/health"),
      ]);
      setFeed(nextFeed);
      setStocks(nextStocks);
      setSources(nextSources);
      setStatus(`Loaded ${nextFeed.length} feed items`);
    } catch (err) {
      setError(readError(err));
      setStatus("Backend unavailable");
    } finally {
      setLoadState("idle");
    }
  }, [fetchJson]);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  const runIngestion = async (source: "hacker-news" | "arxiv") => {
    setLoadState("running");
    setError(null);
    try {
      const result = await fetchJson<{
        source_name: string;
        status: string;
        items_fetched: number;
        items_stored: number;
      }>(`/api/ingestion/${source}?limit=${source === "arxiv" ? 15 : 25}`, { method: "POST" });
      setStatus(
        `${result.source_name}: ${result.items_fetched} fetched, ${result.items_stored} stored`,
      );
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Ingestion failed");
    } finally {
      setLoadState("idle");
    }
  };

  const summarizeItem = async (itemId: number) => {
    setBusyItemId(itemId);
    setError(null);
    try {
      const summarized = await fetchJson<FeedItem>(`/api/feed/${itemId}/summarize`, {
        method: "POST",
      });
      setFeed((items) => items.map((item) => (item.id === itemId ? summarized : item)));
      setStatus(`Summarized item ${itemId}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Summarization failed");
    } finally {
      setBusyItemId(null);
    }
  };

  const submitManualItem = async () => {
    if (!manualTitle.trim() || !manualUrl.trim()) {
      setError("Manual submissions need a title and URL.");
      return;
    }

    setLoadState("running");
    setError(null);
    try {
      const result = await fetchJson<{ item: FeedItem }>("/api/manual-submissions", {
        method: "POST",
        body: JSON.stringify({
          title: manualTitle.trim(),
          url: manualUrl.trim(),
          text: manualText.trim() || null,
        }),
      });
      setFeed((items) => [result.item, ...items.filter((item) => item.id !== result.item.id)]);
      setManualTitle("");
      setManualUrl("");
      setManualText("");
      setStatus(`Submitted item ${result.item.id}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Manual submission failed");
    } finally {
      setLoadState("idle");
    }
  };

  const updateFeedAction = async (
    itemId: number,
    action: "save" | "hide" | "mark-important",
  ) => {
    setBusyItemId(itemId);
    setError(null);
    try {
      const updated = await fetchJson<FeedItem>(`/api/feed/${itemId}/${action}`, {
        method: "POST",
      });
      if (action === "hide") {
        setFeed((items) => items.filter((item) => item.id !== itemId));
        setStatus(`Hidden item ${itemId}`);
      } else {
        setFeed((items) => items.map((item) => (item.id === itemId ? updated : item)));
        setStatus(action === "save" ? `Saved item ${itemId}` : `Marked item ${itemId}`);
      }
    } catch (err) {
      setError(readError(err));
      setStatus("Item action failed");
    } finally {
      setBusyItemId(null);
    }
  };

  const metrics = useMemo(() => {
    const highImportance = feed.filter((item) => item.importance_score >= 0.75).length;
    const summarized = feed.filter((item) => item.summary_detailed).length;
    return [
      { label: "Feed", value: feed.length },
      { label: "High", value: highImportance },
      { label: "Summaries", value: summarized },
      { label: "Sources", value: sources.length },
    ];
  }, [feed, sources.length]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-title">SignalLens</div>
          <div className="brand-subtitle">Personal AI intelligence dashboard</div>
        </div>
        <nav className="nav-list" aria-label="Primary">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <div className={`nav-item ${item.active ? "active" : ""}`} key={item.label}>
                <Icon size={16} aria-hidden="true" />
                <span>{item.label}</span>
              </div>
            );
          })}
        </nav>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1 className="page-title">AI Intelligence Dashboard</h1>
            <div className="page-meta">
              Feed, watchlist, source health, and live ingestion over the local SignalLens API
            </div>
          </div>
          <div className="toolbar">
            <button
              className="button"
              onClick={() => runIngestion("hacker-news")}
              disabled={loadState !== "idle"}
              title="Run Hacker News ingestion"
            >
              {loadState === "running" ? <Loader2 className="spin" size={16} /> : <Newspaper size={16} />}
              HN
            </button>
            <button
              className="button"
              onClick={() => runIngestion("arxiv")}
              disabled={loadState !== "idle"}
              title="Run arXiv ingestion"
            >
              {loadState === "running" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <FlaskConical size={16} />
              )}
              arXiv
            </button>
            <button
              className="button icon-button"
              onClick={refreshAll}
              disabled={loadState !== "idle"}
              title="Refresh dashboard"
              aria-label="Refresh dashboard"
            >
              {loadState === "loading" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <RefreshCw size={16} />
              )}
            </button>
          </div>
        </header>

        <div className={`status-line ${error ? "error" : ""}`}>{error ?? status}</div>

        <section className="score-grid" aria-label="Dashboard metrics">
          {metrics.map((metric) => (
            <div className="score-cell" key={metric.label}>
              <span className="score-label">{metric.label}</span>
              <span className="score-value">{metric.value}</span>
            </div>
          ))}
        </section>

        <div className="content-grid">
          <section className="section">
            <div className="section-header">
              <h2 className="section-title">Ranked Feed</h2>
              <span className="small-muted">{feed.length} items</span>
            </div>
            <div className="feed-list">
              {feed.length ? (
                feed.map((item) => (
                  <FeedCard
                    item={item}
                    key={item.id}
                    busy={busyItemId === item.id}
                    onSummarize={summarizeItem}
                    onAction={updateFeedAction}
                  />
                ))
              ) : (
                <div className="empty-state">No feed items loaded from the API.</div>
              )}
            </div>
          </section>

          <aside className="stack">
            <ManualSubmissionPanel
              title={manualTitle}
              url={manualUrl}
              text={manualText}
              disabled={loadState !== "idle"}
              onTitleChange={setManualTitle}
              onUrlChange={setManualUrl}
              onTextChange={setManualText}
              onSubmit={submitManualItem}
            />
            <StockTable stocks={stocks} />
            <SourceTable sources={sources} />
          </aside>
        </div>
      </main>
    </div>
  );
}

function FeedCard({
  item,
  busy,
  onSummarize,
  onAction,
}: {
  item: FeedItem;
  busy: boolean;
  onSummarize: (itemId: number) => void;
  onAction: (itemId: number, action: "save" | "hide" | "mark-important") => void;
}) {
  const displaySummary = item.summary_detailed || item.summary_short || item.why_it_matters;
  return (
    <article className="feed-card">
      <div className="feed-head">
        <div>
          <h3 className="feed-title">{item.title}</h3>
          <div className="feed-source">
            {item.source_name} {item.published_at ? `· ${formatDate(item.published_at)}` : ""}
          </div>
        </div>
        <div className="badges">
          {item.is_important ? <span className="badge stock">important</span> : null}
          {item.is_saved ? <span className="badge">saved</span> : null}
          <span className={`badge ${item.category === "research" ? "research" : ""}`}>
            {item.category}
          </span>
          {item.tickers.map((ticker) => (
            <span className="badge stock" key={ticker}>
              {ticker}
            </span>
          ))}
        </div>
      </div>

      <div className="badges">
        {item.topics.slice(0, 8).map((topic) => (
          <span className="badge" key={topic}>
            {topic}
          </span>
        ))}
      </div>

      <div className="score-grid">
        <Score label="Relevance" value={item.relevance_score} />
        <Score label="Importance" value={item.importance_score} />
        <Score label="Novelty" value={item.novelty_score} />
        <Score label="Stock" value={item.stock_impact_score} />
      </div>

      {displaySummary ? <div className="summary">{displaySummary}</div> : null}

      <div className="feed-actions">
        <div className="small-muted">{item.author ? `by ${item.author}` : "source-linked item"}</div>
        <div className="toolbar">
          <button
            className="button icon-button"
            onClick={() => onAction(item.id, "save")}
            disabled={busy || item.is_saved}
            title="Save item"
            aria-label="Save item"
          >
            {busy ? <Loader2 className="spin" size={16} /> : <Bookmark size={16} />}
          </button>
          <button
            className="button icon-button"
            onClick={() => onAction(item.id, "mark-important")}
            disabled={busy || item.is_important}
            title="Mark important"
            aria-label="Mark important"
          >
            {busy ? <Loader2 className="spin" size={16} /> : <Flag size={16} />}
          </button>
          <button
            className="button icon-button"
            onClick={() => onAction(item.id, "hide")}
            disabled={busy}
            title="Hide item"
            aria-label="Hide item"
          >
            {busy ? <Loader2 className="spin" size={16} /> : <EyeOff size={16} />}
          </button>
          <button
            className="button"
            onClick={() => onSummarize(item.id)}
            disabled={busy}
            title="Summarize with Kimi"
          >
            {busy ? <Loader2 className="spin" size={16} /> : <FileText size={16} />}
            Summarize
          </button>
          <a className="button icon-button" href={item.url} target="_blank" title="Open source">
            <ExternalLink size={16} />
          </a>
        </div>
      </div>
    </article>
  );
}

function ManualSubmissionPanel({
  title,
  url,
  text,
  disabled,
  onTitleChange,
  onUrlChange,
  onTextChange,
  onSubmit,
}: {
  title: string;
  url: string;
  text: string;
  disabled: boolean;
  onTitleChange: (value: string) => void;
  onUrlChange: (value: string) => void;
  onTextChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Manual Submission</h2>
        <Send size={16} aria-hidden="true" />
      </div>
      <div className="form-panel">
        <label className="field-label" htmlFor="manual-title">
          Title
        </label>
        <input
          id="manual-title"
          className="field"
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
          placeholder="Paste an AI item title"
        />
        <label className="field-label" htmlFor="manual-url">
          URL
        </label>
        <input
          id="manual-url"
          className="field"
          value={url}
          onChange={(event) => onUrlChange(event.target.value)}
          placeholder="https://..."
        />
        <label className="field-label" htmlFor="manual-text">
          Notes or excerpt
        </label>
        <textarea
          id="manual-text"
          className="field textarea"
          value={text}
          onChange={(event) => onTextChange(event.target.value)}
          placeholder="Optional context for classification and summary"
        />
        <button className="button primary" onClick={onSubmit} disabled={disabled}>
          {disabled ? <Loader2 className="spin" size={16} /> : <Send size={16} />}
          Submit
        </button>
      </div>
    </section>
  );
}

function StockTable({ stocks }: { stocks: StockWatchlistItem[] }) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">AI Stock Watchlist</h2>
        <span className="small-muted">{stocks.length} tickers</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Company</th>
              <th>Priority</th>
              <th>Themes</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock) => (
              <tr key={stock.ticker}>
                <td>
                  <span className="ticker">{stock.ticker}</span>
                  {stock.is_pinned ? <Star size={13} fill="currentColor" /> : null}
                </td>
                <td>{stock.company_name}</td>
                <td className={`priority-${stock.priority.toLowerCase()}`}>{stock.priority}</td>
                <td>{stock.related_ai_themes.slice(0, 2).join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SourceTable({ sources }: { sources: SourceHealth[] }) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Source Health</h2>
        <DatabaseZap size={16} aria-hidden="true" />
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Status</th>
              <th>Stored</th>
              <th>Last Run</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.id}>
                <td>{source.name}</td>
                <td className={source.latest_status === "success" ? "health-ok" : ""}>
                  {source.latest_status}
                </td>
                <td>{source.items_stored}</td>
                <td>{source.last_finished_at ? formatDate(source.last_finished_at) : "never"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="score-cell">
      <span className="score-label">{label}</span>
      <span className="score-value">{Math.round(value * 100)}</span>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function readError(err: unknown) {
  return err instanceof Error ? err.message : "Unexpected error";
}
