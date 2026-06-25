"use client";

import {
  Activity,
  BarChart3,
  BellRing,
  Bookmark,
  Bot,
  CalendarDays,
  DatabaseZap,
  EyeOff,
  ExternalLink,
  FileText,
  Flag,
  FlaskConical,
  Github,
  Loader2,
  Newspaper,
  Plus,
  RefreshCw,
  Rocket,
  Search,
  Send,
  SlidersHorizontal,
  Star,
  TrendingUp,
  Trash2,
  X,
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
  is_holding: boolean;
  shares: number | null;
  average_cost: number | null;
  related_keywords: string[];
  related_companies: string[];
  related_ai_themes: string[];
  notes: string | null;
};

type StockSignalSummary = {
  stock: StockWatchlistItem;
  signal_count: number;
  attention_score: number;
  top_signals: FeedItem[];
  disclaimer: string;
};

type StockBriefingTimelineItem = {
  item: FeedItem;
  signal_score: number;
  reason: string;
};

type StockBriefing = {
  stock: StockWatchlistItem;
  signal_count: number;
  attention_score: number;
  urgency: string;
  latest_signal_at: string | null;
  sentiment_counts: Record<string, number>;
  key_themes: string[];
  recent_timeline: StockBriefingTimelineItem[];
  disclaimer: string;
};

type TopicWatchlistItem = {
  topic: string;
  label: string;
  category: string;
  priority: string;
  is_pinned: boolean;
  include_in_digest: boolean;
  related_terms: string[];
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

type DigestSourceCoverage = {
  source_name: string;
  item_count: number;
};

type DigestSection = {
  key: string;
  title: string;
  focus: string;
  items: FeedItem[];
};

type DailyDigest = {
  digest_date: string;
  generated_at: string;
  headline: string;
  total_items: number;
  sections: DigestSection[];
  source_coverage: DigestSourceCoverage[];
  watchlist_tickers: string[];
  disclaimer: string;
};

type EventCluster = {
  cluster_key: string;
  title: string;
  category: string;
  topics: string[];
  tickers: string[];
  sources: string[];
  item_count: number;
  top_score: number;
  first_seen_at: string | null;
  last_seen_at: string | null;
  representative_item: FeedItem;
  items: FeedItem[];
};

type AlertItem = {
  id: number;
  title: string;
  reason: string;
  severity: string;
  status: string;
  created_at: string;
  item: FeedItem;
  disclaimer: string;
};

type AlertRule = {
  id: number;
  name: string;
  description: string | null;
  category: string;
  severity: string;
  min_importance_score: number;
  min_stock_impact_score: number;
  tickers: string[];
  topics: string[];
  enabled: boolean;
};

type RankingWeights = {
  relevance: number;
  importance: number;
  novelty: number;
  source_quality: number;
  stock_impact: number;
  freshness: number;
};

type UserPreferences = {
  user_id: string;
  ranking_weights: RankingWeights;
};

type LoadState = "idle" | "loading" | "running";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const DEFAULT_RANKING_WEIGHTS: RankingWeights = {
  relevance: 0.25,
  importance: 0.2,
  novelty: 0.15,
  source_quality: 0.15,
  stock_impact: 0.1,
  freshness: 0.05,
};

const rankingWeightFields: { key: keyof RankingWeights; label: string }[] = [
  { key: "relevance", label: "Relevance" },
  { key: "importance", label: "Importance" },
  { key: "novelty", label: "Novelty" },
  { key: "source_quality", label: "Source" },
  { key: "stock_impact", label: "Stock" },
  { key: "freshness", label: "Freshness" },
];

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
  const [stockSignals, setStockSignals] = useState<StockSignalSummary[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [stockBriefing, setStockBriefing] = useState<StockBriefing | null>(null);
  const [topics, setTopics] = useState<TopicWatchlistItem[]>([]);
  const [sources, setSources] = useState<SourceHealth[]>([]);
  const [digest, setDigest] = useState<DailyDigest | null>(null);
  const [eventClusters, setEventClusters] = useState<EventCluster[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [rankingDraft, setRankingDraft] = useState<RankingWeights>(DEFAULT_RANKING_WEIGHTS);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [status, setStatus] = useState("Ready");
  const [error, setError] = useState<string | null>(null);
  const [busyItemId, setBusyItemId] = useState<number | null>(null);
  const [busyAlertId, setBusyAlertId] = useState<number | null>(null);
  const [busySourceId, setBusySourceId] = useState<number | null>(null);
  const [busyStockTicker, setBusyStockTicker] = useState<string | null>(null);
  const [busyWatchlistKey, setBusyWatchlistKey] = useState<string | null>(null);
  const [busyPreferences, setBusyPreferences] = useState(false);
  const [manualTitle, setManualTitle] = useState("");
  const [manualUrl, setManualUrl] = useState("");
  const [manualText, setManualText] = useState("");
  const [stockTicker, setStockTicker] = useState("");
  const [stockCompany, setStockCompany] = useState("");
  const [stockThemes, setStockThemes] = useState("");
  const [stockKeywords, setStockKeywords] = useState("");
  const [topicName, setTopicName] = useState("");
  const [topicLabel, setTopicLabel] = useState("");
  const [topicCategory, setTopicCategory] = useState("technical_trend");
  const [topicTerms, setTopicTerms] = useState("");
  const [alertRuleName, setAlertRuleName] = useState("");
  const [alertRuleCategory, setAlertRuleCategory] = useState("all");
  const [alertRuleTickers, setAlertRuleTickers] = useState("");
  const [alertRuleTopics, setAlertRuleTopics] = useState("");
  const [alertRuleImportance, setAlertRuleImportance] = useState("0.75");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchSource, setSearchSource] = useState("");
  const [searchCategory, setSearchCategory] = useState("");
  const [searchTicker, setSearchTicker] = useState("");
  const [searchTopic, setSearchTopic] = useState("");
  const [savedOnly, setSavedOnly] = useState(false);

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

  const sendRequest = useCallback(async (path: string, init?: RequestInit): Promise<void> => {
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
  }, []);

  const refreshAll = useCallback(async () => {
    setLoadState("loading");
    setError(null);
    try {
      const [
        nextFeed,
        nextStocks,
        nextStockSignals,
        nextTopics,
        nextSources,
        nextDigest,
        nextEventClusters,
        nextAlerts,
        nextAlertRules,
        nextPreferences,
      ] =
        await Promise.all([
          fetchJson<FeedItem[]>("/api/feed?limit=30"),
          fetchJson<StockWatchlistItem[]>("/api/watchlist/stocks"),
          fetchJson<StockSignalSummary[]>("/api/watchlist/stocks/signals/summary"),
          fetchJson<TopicWatchlistItem[]>("/api/watchlist/topics"),
          fetchJson<SourceHealth[]>("/api/sources/health"),
          fetchJson<DailyDigest>("/api/digest/daily"),
          fetchJson<EventCluster[]>("/api/events/clusters?limit=8&min_items=2"),
          fetchJson<AlertItem[]>("/api/alerts?limit=8"),
          fetchJson<AlertRule[]>("/api/alerts/rules"),
          fetchJson<UserPreferences>("/api/preferences"),
        ]);
      setFeed(nextFeed);
      setStocks(nextStocks);
      setStockSignals(nextStockSignals);
      setTopics(nextTopics);
      setSources(nextSources);
      setDigest(nextDigest);
      setEventClusters(nextEventClusters);
      setAlerts(nextAlerts);
      setAlertRules(nextAlertRules);
      setPreferences(nextPreferences);
      setRankingDraft(nextPreferences.ranking_weights);
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

  useEffect(() => {
    if (!selectedTicker && stocks.length) {
      setSelectedTicker(stocks[0].ticker);
    }
  }, [selectedTicker, stocks]);

  useEffect(() => {
    if (!selectedTicker) {
      setStockBriefing(null);
      return;
    }

    let cancelled = false;
    setBusyStockTicker(selectedTicker);
    fetchJson<StockBriefing>(`/api/watchlist/stocks/${selectedTicker}/briefing?limit=8`)
      .then((briefing) => {
        if (!cancelled) {
          setStockBriefing(briefing);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(readError(err));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setBusyStockTicker(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fetchJson, selectedTicker]);

  const runIngestion = async (
    source:
      | "hacker-news"
      | "alpha-vantage-news"
      | "arxiv"
      | "chinese-rss"
      | "github"
      | "hugging-face"
      | "product-hunt"
      | "rss",
  ) => {
    setLoadState("running");
    setError(null);
    try {
      const limit = source === "arxiv" ? 15 : source === "github" ? 20 : 25;
      const result = await fetchJson<{
        source_name: string;
        status: string;
        items_fetched: number;
        items_stored: number;
      }>(`/api/ingestion/${source}?limit=${limit}`, { method: "POST" });
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

  const processTopItemsWithLlm = async () => {
    setLoadState("running");
    setError(null);
    try {
      const result = await fetchJson<{
        summarized_count: number;
        classified_count: number;
        skipped_count: number;
        errors: { item_id: number; stage: string; error: string }[];
      }>("/api/llm/process-feed", {
        method: "POST",
        body: JSON.stringify({
          limit: 3,
          summarize: true,
          classify: false,
          skip_summarized: true,
        }),
      });
      setStatus(
        `LLM processed ${result.summarized_count} summaries, ${result.skipped_count} skipped`,
      );
      if (result.errors.length) {
        setError(`${result.errors.length} LLM item errors; see API response logs.`);
      }
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("LLM batch failed");
    } finally {
      setLoadState("idle");
    }
  };

  const updateRankingDraft = (key: keyof RankingWeights, value: number) => {
    setRankingDraft((current) => ({
      ...current,
      [key]: clampWeight(value),
    }));
  };

  const saveRankingPreferences = async () => {
    setBusyPreferences(true);
    setError(null);
    try {
      const updated = await fetchJson<UserPreferences>("/api/preferences", {
        method: "PATCH",
        body: JSON.stringify({ ranking_weights: rankingDraft }),
      });
      setPreferences(updated);
      setRankingDraft(updated.ranking_weights);
      setStatus("Updated ranking weights");
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Ranking preference update failed");
    } finally {
      setBusyPreferences(false);
    }
  };

  const runSearch = async () => {
    setLoadState("loading");
    setError(null);
    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.set("q", searchQuery.trim());
      if (searchSource.trim()) params.set("source", searchSource.trim());
      if (searchCategory.trim()) params.set("category", searchCategory.trim());
      if (searchTicker.trim()) params.set("ticker", searchTicker.trim().toUpperCase());
      if (searchTopic.trim()) params.set("topic", searchTopic.trim());
      if (savedOnly) params.set("saved_only", "true");
      params.set("limit", "30");

      const results = await fetchJson<FeedItem[]>(`/api/search?${params.toString()}`);
      setFeed(results);
      setStatus(`Search returned ${results.length} items`);
    } catch (err) {
      setError(readError(err));
      setStatus("Search failed");
    } finally {
      setLoadState("idle");
    }
  };

  const clearSearch = async () => {
    setSearchQuery("");
    setSearchSource("");
    setSearchCategory("");
    setSearchTicker("");
    setSearchTopic("");
    setSavedOnly(false);
    await refreshAll();
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

  const classifyItem = async (itemId: number) => {
    setBusyItemId(itemId);
    setError(null);
    try {
      const classified = await fetchJson<FeedItem>(`/api/feed/${itemId}/classify`, {
        method: "POST",
      });
      setFeed((items) => items.map((item) => (item.id === itemId ? classified : item)));
      setStatus(`Classified item ${itemId}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Classification failed");
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

  const submitStock = async () => {
    if (!stockTicker.trim() || !stockCompany.trim()) {
      setError("Stock watchlist entries need a ticker and company name.");
      return;
    }

    setLoadState("running");
    setError(null);
    try {
      const created = await fetchJson<StockWatchlistItem>("/api/watchlist/stocks", {
        method: "POST",
        body: JSON.stringify({
          ticker: stockTicker.trim().toUpperCase(),
          company_name: stockCompany.trim(),
          related_ai_themes: splitTerms(stockThemes),
          related_keywords: splitTerms(stockKeywords),
        }),
      });
      setStocks((items) => [created, ...items.filter((item) => item.ticker !== created.ticker)]);
      setSelectedTicker(created.ticker);
      setStockTicker("");
      setStockCompany("");
      setStockThemes("");
      setStockKeywords("");
      setStatus(`Added ${created.ticker}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Stock add failed");
    } finally {
      setLoadState("idle");
    }
  };

  const deleteStock = async (ticker: string) => {
    const key = `stock:${ticker}`;
    setBusyWatchlistKey(key);
    setError(null);
    try {
      await sendRequest(`/api/watchlist/stocks/${encodeURIComponent(ticker)}`, {
        method: "DELETE",
      });
      const remainingStocks = stocks.filter((item) => item.ticker !== ticker);
      setStocks(remainingStocks);
      setStockSignals((items) => items.filter((item) => item.stock.ticker !== ticker));
      if (selectedTicker === ticker) {
        setSelectedTicker(remainingStocks[0]?.ticker ?? null);
        setStockBriefing(null);
      }
      setStatus(`Removed ${ticker}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Stock remove failed");
    } finally {
      setBusyWatchlistKey(null);
    }
  };

  const updateStock = async (
    ticker: string,
    payload: Partial<Pick<StockWatchlistItem, "priority" | "is_pinned">>,
  ) => {
    const key = `stock:${ticker}`;
    setBusyWatchlistKey(key);
    setError(null);
    try {
      const updated = await fetchJson<StockWatchlistItem>(
        `/api/watchlist/stocks/${encodeURIComponent(ticker)}`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        },
      );
      setStocks((items) => items.map((item) => (item.ticker === updated.ticker ? updated : item)));
      setStockSignals((items) =>
        items.map((item) =>
          item.stock.ticker === updated.ticker ? { ...item, stock: updated } : item,
        ),
      );
      if (stockBriefing?.stock.ticker === updated.ticker) {
        setStockBriefing({ ...stockBriefing, stock: updated });
      }
      setStatus(`Updated ${updated.ticker}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Stock update failed");
    } finally {
      setBusyWatchlistKey(null);
    }
  };

  const submitTopic = async () => {
    if (!topicName.trim()) {
      setError("Topic watchlist entries need a topic name.");
      return;
    }

    setLoadState("running");
    setError(null);
    try {
      const created = await fetchJson<TopicWatchlistItem>("/api/watchlist/topics", {
        method: "POST",
        body: JSON.stringify({
          topic: topicName.trim(),
          label: topicLabel.trim() || null,
          category: topicCategory,
          related_terms: splitTerms(topicTerms),
        }),
      });
      setTopics((items) => [created, ...items.filter((item) => item.topic !== created.topic)]);
      setTopicName("");
      setTopicLabel("");
      setTopicCategory("technical_trend");
      setTopicTerms("");
      setStatus(`Added topic ${created.label}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Topic add failed");
    } finally {
      setLoadState("idle");
    }
  };

  const deleteTopic = async (topic: string) => {
    const key = `topic:${topic}`;
    setBusyWatchlistKey(key);
    setError(null);
    try {
      await sendRequest(`/api/watchlist/topics/${encodeURIComponent(topic)}`, {
        method: "DELETE",
      });
      setTopics((items) => items.filter((item) => item.topic !== topic));
      setStatus(`Removed topic ${topic}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Topic remove failed");
    } finally {
      setBusyWatchlistKey(null);
    }
  };

  const updateTopic = async (
    topic: string,
    payload: Partial<Pick<TopicWatchlistItem, "priority" | "is_pinned" | "include_in_digest">>,
  ) => {
    const key = `topic:${topic}`;
    setBusyWatchlistKey(key);
    setError(null);
    try {
      const updated = await fetchJson<TopicWatchlistItem>(
        `/api/watchlist/topics/${encodeURIComponent(topic)}`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        },
      );
      setTopics((items) => items.map((item) => (item.topic === updated.topic ? updated : item)));
      setStatus(`Updated topic ${updated.label}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Topic update failed");
    } finally {
      setBusyWatchlistKey(null);
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

  const dismissAlert = async (alertId: number) => {
    setBusyAlertId(alertId);
    setError(null);
    try {
      await fetchJson<AlertItem>(`/api/alerts/${alertId}/dismiss`, {
        method: "POST",
      });
      setAlerts((items) => items.filter((item) => item.id !== alertId));
      setStatus(`Dismissed alert ${alertId}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Alert action failed");
    } finally {
      setBusyAlertId(null);
    }
  };

  const submitAlertRule = async () => {
    if (!alertRuleName.trim()) {
      setError("Alert rules need a name.");
      return;
    }

    setLoadState("running");
    setError(null);
    try {
      const created = await fetchJson<AlertRule>("/api/alerts/rules", {
        method: "POST",
        body: JSON.stringify({
          name: alertRuleName.trim(),
          category: alertRuleCategory,
          min_importance_score: Number(alertRuleImportance) || 0.75,
          tickers: splitTerms(alertRuleTickers),
          topics: splitTerms(alertRuleTopics),
        }),
      });
      setAlertRules((rules) => [created, ...rules.filter((rule) => rule.id !== created.id)]);
      setAlertRuleName("");
      setAlertRuleCategory("all");
      setAlertRuleTickers("");
      setAlertRuleTopics("");
      setAlertRuleImportance("0.75");
      setStatus(`Added alert rule ${created.name}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Alert rule add failed");
    } finally {
      setLoadState("idle");
    }
  };

  const toggleSource = async (source: SourceHealth) => {
    setBusySourceId(source.id);
    setError(null);
    try {
      const updated = await fetchJson<SourceHealth>(`/api/sources/${source.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !source.enabled }),
      });
      setSources((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setStatus(`${updated.enabled ? "Enabled" : "Disabled"} ${updated.name}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Source update failed");
    } finally {
      setBusySourceId(null);
    }
  };

  const metrics = useMemo(() => {
    const highImportance = feed.filter((item) => item.importance_score >= 0.75).length;
    const summarized = feed.filter((item) => item.summary_detailed).length;
    return [
      { label: "Feed", value: feed.length },
      { label: "High", value: highImportance },
      { label: "Alerts", value: alerts.length },
      { label: "Summaries", value: summarized },
    ];
  }, [alerts.length, feed]);

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
              onClick={() => runIngestion("alpha-vantage-news")}
              disabled={loadState !== "idle"}
              title="Run Alpha Vantage stock news ingestion"
            >
              {loadState === "running" ? <Loader2 className="spin" size={16} /> : <BarChart3 size={16} />}
              Stocks
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
              className="button"
              onClick={() => runIngestion("chinese-rss")}
              disabled={loadState !== "idle"}
              title="Run configured Chinese RSS ingestion"
            >
              {loadState === "running" ? <Loader2 className="spin" size={16} /> : <Newspaper size={16} />}
              CN
            </button>
            <button
              className="button"
              onClick={() => runIngestion("github")}
              disabled={loadState !== "idle"}
              title="Run GitHub repository ingestion"
            >
              {loadState === "running" ? <Loader2 className="spin" size={16} /> : <Github size={16} />}
              GitHub
            </button>
            <button
              className="button"
              onClick={() => runIngestion("hugging-face")}
              disabled={loadState !== "idle"}
              title="Run Hugging Face model ingestion"
            >
              {loadState === "running" ? <Loader2 className="spin" size={16} /> : <Bot size={16} />}
              HF
            </button>
            <button
              className="button"
              onClick={() => runIngestion("product-hunt")}
              disabled={loadState !== "idle"}
              title="Run Product Hunt launch ingestion"
            >
              {loadState === "running" ? <Loader2 className="spin" size={16} /> : <Rocket size={16} />}
              PH
            </button>
            <button
              className="button"
              onClick={() => runIngestion("rss")}
              disabled={loadState !== "idle"}
              title="Run selected RSS feed ingestion"
            >
              {loadState === "running" ? <Loader2 className="spin" size={16} /> : <Newspaper size={16} />}
              RSS
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
            <button
              className="button"
              onClick={processTopItemsWithLlm}
              disabled={loadState !== "idle"}
              title="Summarize top feed items with Kimi"
            >
              {loadState === "running" ? <Loader2 className="spin" size={16} /> : <Bot size={16} />}
              LLM
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
            <SearchPanel
              query={searchQuery}
              source={searchSource}
              category={searchCategory}
              ticker={searchTicker}
              topic={searchTopic}
              savedOnly={savedOnly}
              disabled={loadState !== "idle"}
              onQueryChange={setSearchQuery}
              onSourceChange={setSearchSource}
              onCategoryChange={setSearchCategory}
              onTickerChange={setSearchTicker}
              onTopicChange={setSearchTopic}
              onSavedOnlyChange={setSavedOnly}
              onSearch={runSearch}
              onClear={clearSearch}
            />
            <div className="feed-list">
              {feed.length ? (
                feed.map((item) => (
                  <FeedCard
                    item={item}
                    key={item.id}
                    busy={busyItemId === item.id}
                    onSummarize={summarizeItem}
                    onClassify={classifyItem}
                    onAction={updateFeedAction}
                  />
                ))
              ) : (
                <div className="empty-state">No feed items loaded from the API.</div>
              )}
            </div>
          </section>

          <aside className="stack">
            <RankingPreferencesPanel
              preferences={preferences}
              draft={rankingDraft}
              disabled={loadState !== "idle"}
              busy={busyPreferences}
              onDraftChange={updateRankingDraft}
              onReset={() => setRankingDraft(DEFAULT_RANKING_WEIGHTS)}
              onSave={saveRankingPreferences}
            />
            <AlertPanel
              alerts={alerts}
              rules={alertRules}
              busyAlertId={busyAlertId}
              ruleName={alertRuleName}
              ruleCategory={alertRuleCategory}
              ruleTickers={alertRuleTickers}
              ruleTopics={alertRuleTopics}
              ruleImportance={alertRuleImportance}
              disabled={loadState !== "idle"}
              onDismiss={dismissAlert}
              onRuleNameChange={setAlertRuleName}
              onRuleCategoryChange={setAlertRuleCategory}
              onRuleTickersChange={setAlertRuleTickers}
              onRuleTopicsChange={setAlertRuleTopics}
              onRuleImportanceChange={setAlertRuleImportance}
              onRuleSubmit={submitAlertRule}
            />
            <DailyDigestPanel digest={digest} />
            <ChineseSocialPanel items={feed} />
            <EventClusterPanel clusters={eventClusters} />
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
            <StockTable
              stocks={stocks}
              signalSummaries={stockSignals}
              stockBriefing={stockBriefing}
              selectedTicker={selectedTicker}
              busyStockTicker={busyStockTicker}
              busyWatchlistKey={busyWatchlistKey}
              ticker={stockTicker}
              company={stockCompany}
              themes={stockThemes}
              keywords={stockKeywords}
              disabled={loadState !== "idle"}
              onTickerChange={setStockTicker}
              onCompanyChange={setStockCompany}
              onThemesChange={setStockThemes}
              onKeywordsChange={setStockKeywords}
              onSelectTicker={setSelectedTicker}
              onUpdateStock={updateStock}
              onDeleteStock={deleteStock}
              onSubmit={submitStock}
            />
            <TopicTable
              topics={topics}
              topic={topicName}
              label={topicLabel}
              category={topicCategory}
              terms={topicTerms}
              disabled={loadState !== "idle"}
              busyWatchlistKey={busyWatchlistKey}
              onTopicChange={setTopicName}
              onLabelChange={setTopicLabel}
              onCategoryChange={setTopicCategory}
              onTermsChange={setTopicTerms}
              onUpdateTopic={updateTopic}
              onDeleteTopic={deleteTopic}
              onSubmit={submitTopic}
            />
            <SourceTable
              sources={sources}
              busySourceId={busySourceId}
              onToggleSource={toggleSource}
            />
          </aside>
        </div>
      </main>
    </div>
  );
}

function RankingPreferencesPanel({
  preferences,
  draft,
  disabled,
  busy,
  onDraftChange,
  onReset,
  onSave,
}: {
  preferences: UserPreferences | null;
  draft: RankingWeights;
  disabled: boolean;
  busy: boolean;
  onDraftChange: (key: keyof RankingWeights, value: number) => void;
  onReset: () => void;
  onSave: () => void;
}) {
  const totalWeight = rankingWeightFields.reduce((sum, field) => sum + draft[field.key], 0);
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Ranking Weights</h2>
        <SlidersHorizontal size={16} aria-hidden="true" />
      </div>
      <div className="digest-panel">
        <div className="digest-meta">
          <span>{preferences?.user_id ?? "local"}</span>
          <span>{totalWeight.toFixed(2)}</span>
        </div>
        <div className="weights-grid">
          {rankingWeightFields.map((field) => (
            <label className="weight-field" key={field.key}>
              <span className="field-label">{field.label}</span>
              <input
                className="field"
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={draft[field.key]}
                onChange={(event) => onDraftChange(field.key, Number(event.target.value))}
                disabled={disabled || busy}
              />
            </label>
          ))}
        </div>
        <div className="toolbar">
          <button className="button" onClick={onReset} disabled={disabled || busy}>
            Reset
          </button>
          <button className="button primary" onClick={onSave} disabled={disabled || busy}>
            {busy ? <Loader2 className="spin" size={16} /> : <SlidersHorizontal size={16} />}
            Save
          </button>
        </div>
      </div>
    </section>
  );
}

function ChineseSocialPanel({ items }: { items: FeedItem[] }) {
  const chineseItems = items.filter(
    (item) => item.category === "social_trend" || item.language === "zh",
  );
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Chinese Social Trends</h2>
        <span className="small-muted">{chineseItems.length} items</span>
      </div>
      <div className="digest-panel">
        {chineseItems.length ? (
          chineseItems.slice(0, 5).map((item) => (
            <div className="digest-section" key={item.id}>
              <div className="digest-section-title">
                {item.source_name} {item.published_at ? `· ${formatDate(item.published_at)}` : ""}
              </div>
              <a className="digest-link" href={item.url} target="_blank">
                {item.title}
              </a>
              <div className="badges">
                {item.topics.slice(0, 4).map((topic) => (
                  <span className="badge" key={topic}>
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state">No Chinese social signals loaded.</div>
        )}
      </div>
    </section>
  );
}

function AlertPanel({
  alerts,
  rules,
  busyAlertId,
  ruleName,
  ruleCategory,
  ruleTickers,
  ruleTopics,
  ruleImportance,
  disabled,
  onDismiss,
  onRuleNameChange,
  onRuleCategoryChange,
  onRuleTickersChange,
  onRuleTopicsChange,
  onRuleImportanceChange,
  onRuleSubmit,
}: {
  alerts: AlertItem[];
  rules: AlertRule[];
  busyAlertId: number | null;
  ruleName: string;
  ruleCategory: string;
  ruleTickers: string;
  ruleTopics: string;
  ruleImportance: string;
  disabled: boolean;
  onDismiss: (alertId: number) => void;
  onRuleNameChange: (value: string) => void;
  onRuleCategoryChange: (value: string) => void;
  onRuleTickersChange: (value: string) => void;
  onRuleTopicsChange: (value: string) => void;
  onRuleImportanceChange: (value: string) => void;
  onRuleSubmit: () => void;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Alerts</h2>
        <BellRing size={16} aria-hidden="true" />
      </div>
      <div className="form-panel compact-form">
        <input
          className="field"
          value={ruleName}
          onChange={(event) => onRuleNameChange(event.target.value)}
          placeholder="Rule name"
          aria-label="Alert rule name"
        />
        <select
          className="field"
          value={ruleCategory}
          onChange={(event) => onRuleCategoryChange(event.target.value)}
          aria-label="Alert rule category"
        >
          <option value="all">Any</option>
          <option value="technical_trend">Trend</option>
          <option value="research">Research</option>
          <option value="product">Product</option>
          <option value="stock_company_event">Stock</option>
          <option value="social_trend">Social</option>
        </select>
        <input
          className="field"
          value={ruleTickers}
          onChange={(event) => onRuleTickersChange(event.target.value)}
          placeholder="Tickers"
          aria-label="Alert rule tickers"
        />
        <input
          className="field"
          value={ruleTopics}
          onChange={(event) => onRuleTopicsChange(event.target.value)}
          placeholder="Topics"
          aria-label="Alert rule topics"
        />
        <input
          className="field"
          value={ruleImportance}
          onChange={(event) => onRuleImportanceChange(event.target.value)}
          placeholder="Min"
          aria-label="Alert rule minimum importance"
        />
        <button className="button primary" onClick={onRuleSubmit} disabled={disabled}>
          {disabled ? <Loader2 className="spin" size={16} /> : <Plus size={16} />}
          Add
        </button>
      </div>
      <div className="badges">
        {rules.slice(0, 5).map((rule) => (
          <span className={`badge ${rule.enabled ? "" : "muted-badge"}`} key={rule.id}>
            {rule.name}
          </span>
        ))}
      </div>
      <div className="alert-list">
        {alerts.length ? (
          alerts.map((alert) => (
            <article className={`alert-card severity-${alert.severity}`} key={alert.id}>
              <div className="alert-head">
                <div>
                  <div className="alert-title">{alert.title}</div>
                  <div className="small-muted">
                    {alert.severity} · {formatDate(alert.created_at)}
                  </div>
                </div>
                <button
                  className="button icon-button"
                  onClick={() => onDismiss(alert.id)}
                  disabled={busyAlertId === alert.id}
                  title="Dismiss alert"
                  aria-label="Dismiss alert"
                >
                  {busyAlertId === alert.id ? <Loader2 className="spin" size={16} /> : <X size={16} />}
                </button>
              </div>
              <div className="summary">{alert.reason}</div>
              <div className="badges">
                {alert.item.tickers.map((ticker) => (
                  <span className="badge stock" key={ticker}>
                    {ticker}
                  </span>
                ))}
                <span className="badge">{alert.item.category}</span>
              </div>
              <a className="digest-link" href={alert.item.url} target="_blank">
                {alert.item.source_name}
              </a>
              <div className="small-muted">{alert.disclaimer}</div>
            </article>
          ))
        ) : (
          <div className="empty-state">No active alerts.</div>
        )}
      </div>
    </section>
  );
}

function DailyDigestPanel({ digest }: { digest: DailyDigest | null }) {
  const sectionsWithItems = digest?.sections.filter((section) => section.items.length) ?? [];
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Daily Digest</h2>
        <CalendarDays size={16} aria-hidden="true" />
      </div>
      {digest ? (
        <div className="digest-panel">
          <div className="digest-meta">
            <span>{digest.digest_date}</span>
            <span>{digest.total_items} items</span>
          </div>
          <div className="digest-headline">{digest.headline}</div>
          <div className="digest-coverage">
            {digest.source_coverage.slice(0, 4).map((source) => (
              <span className="badge" key={source.source_name}>
                {source.source_name} {source.item_count}
              </span>
            ))}
          </div>
          <div className="digest-sections">
            {sectionsWithItems.length ? (
              sectionsWithItems.map((section) => (
                <div className="digest-section" key={section.key}>
                  <div className="digest-section-title">{section.title}</div>
                  <div className="digest-list">
                    {section.items.slice(0, 3).map((item) => (
                      <a className="digest-link" href={item.url} target="_blank" key={item.id}>
                        {item.title}
                      </a>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">No collected items for this digest date.</div>
            )}
          </div>
          <div className="small-muted">{digest.disclaimer}</div>
        </div>
      ) : (
        <div className="empty-state">Digest unavailable.</div>
      )}
    </section>
  );
}

function EventClusterPanel({ clusters }: { clusters: EventCluster[] }) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Event Clusters</h2>
        <span className="small-muted">{clusters.length} clusters</span>
      </div>
      <div className="digest-panel">
        {clusters.length ? (
          clusters.slice(0, 5).map((cluster) => (
            <div className="digest-section" key={cluster.cluster_key}>
              <div className="digest-section-title">
                {cluster.item_count} item{cluster.item_count === 1 ? "" : "s"} ·{" "}
                {cluster.sources.slice(0, 2).join(", ")}
              </div>
              <a className="digest-link" href={cluster.representative_item.url} target="_blank">
                {cluster.title}
              </a>
              <div className="badges">
                {[...cluster.tickers, ...cluster.topics.slice(0, 3)].map((label) => (
                  <span className="badge" key={label}>
                    {label}
                  </span>
                ))}
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state">No clusters available.</div>
        )}
      </div>
    </section>
  );
}

function SearchPanel({
  query,
  source,
  category,
  ticker,
  topic,
  savedOnly,
  disabled,
  onQueryChange,
  onSourceChange,
  onCategoryChange,
  onTickerChange,
  onTopicChange,
  onSavedOnlyChange,
  onSearch,
  onClear,
}: {
  query: string;
  source: string;
  category: string;
  ticker: string;
  topic: string;
  savedOnly: boolean;
  disabled: boolean;
  onQueryChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
  onTickerChange: (value: string) => void;
  onTopicChange: (value: string) => void;
  onSavedOnlyChange: (value: boolean) => void;
  onSearch: () => void;
  onClear: () => void;
}) {
  return (
    <div className="search-panel">
      <div className="search-row">
        <input
          className="field search-input"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") onSearch();
          }}
          placeholder="Search AI topics, companies, summaries"
        />
        <button className="button primary" onClick={onSearch} disabled={disabled}>
          {disabled ? <Loader2 className="spin" size={16} /> : <Search size={16} />}
          Search
        </button>
        <button className="button" onClick={onClear} disabled={disabled}>
          Clear
        </button>
      </div>
      <div className="filter-row">
        <input
          className="field"
          value={source}
          onChange={(event) => onSourceChange(event.target.value)}
          placeholder="Source"
        />
        <select
          className="field"
          value={category}
          onChange={(event) => onCategoryChange(event.target.value)}
          aria-label="Category filter"
        >
          <option value="">Any category</option>
          <option value="research">Research</option>
          <option value="technical_trend">Technical trend</option>
          <option value="manual_submission">Manual submission</option>
          <option value="stock_company_event">Stock/company</option>
          <option value="product">Product</option>
          <option value="social_trend">Social trend</option>
        </select>
        <input
          className="field"
          value={ticker}
          onChange={(event) => onTickerChange(event.target.value)}
          placeholder="Ticker"
        />
        <input
          className="field"
          value={topic}
          onChange={(event) => onTopicChange(event.target.value)}
          placeholder="Topic"
        />
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={savedOnly}
            onChange={(event) => onSavedOnlyChange(event.target.checked)}
          />
          Saved
        </label>
      </div>
    </div>
  );
}

function FeedCard({
  item,
  busy,
  onSummarize,
  onClassify,
  onAction,
}: {
  item: FeedItem;
  busy: boolean;
  onSummarize: (itemId: number) => void;
  onClassify: (itemId: number) => void;
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
          <button
            className="button"
            onClick={() => onClassify(item.id)}
            disabled={busy}
            title="Classify with Kimi"
          >
            {busy ? <Loader2 className="spin" size={16} /> : <Bot size={16} />}
            Classify
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

function StockTable({
  stocks,
  signalSummaries,
  stockBriefing,
  selectedTicker,
  busyStockTicker,
  busyWatchlistKey,
  ticker,
  company,
  themes,
  keywords,
  disabled,
  onTickerChange,
  onCompanyChange,
  onThemesChange,
  onKeywordsChange,
  onSelectTicker,
  onUpdateStock,
  onDeleteStock,
  onSubmit,
}: {
  stocks: StockWatchlistItem[];
  signalSummaries: StockSignalSummary[];
  stockBriefing: StockBriefing | null;
  selectedTicker: string | null;
  busyStockTicker: string | null;
  busyWatchlistKey: string | null;
  ticker: string;
  company: string;
  themes: string;
  keywords: string;
  disabled: boolean;
  onTickerChange: (value: string) => void;
  onCompanyChange: (value: string) => void;
  onThemesChange: (value: string) => void;
  onKeywordsChange: (value: string) => void;
  onSelectTicker: (value: string) => void;
  onUpdateStock: (
    ticker: string,
    payload: Partial<Pick<StockWatchlistItem, "priority" | "is_pinned">>,
  ) => void;
  onDeleteStock: (ticker: string) => void;
  onSubmit: () => void;
}) {
  const signalMap = new Map(signalSummaries.map((summary) => [summary.stock.ticker, summary]));
  const disclaimer = signalSummaries[0]?.disclaimer;
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">AI Stock Watchlist</h2>
        <span className="small-muted">{stocks.length} tickers</span>
      </div>
      <div className="form-panel compact-form">
        <input
          className="field"
          value={ticker}
          onChange={(event) => onTickerChange(event.target.value)}
          placeholder="Ticker"
          aria-label="Stock ticker"
        />
        <input
          className="field"
          value={company}
          onChange={(event) => onCompanyChange(event.target.value)}
          placeholder="Company"
          aria-label="Company name"
        />
        <input
          className="field"
          value={themes}
          onChange={(event) => onThemesChange(event.target.value)}
          placeholder="AI themes"
          aria-label="AI themes"
        />
        <input
          className="field"
          value={keywords}
          onChange={(event) => onKeywordsChange(event.target.value)}
          placeholder="Keywords"
          aria-label="Stock keywords"
        />
        <button className="button primary" onClick={onSubmit} disabled={disabled}>
          {disabled ? <Loader2 className="spin" size={16} /> : <Plus size={16} />}
          Add
        </button>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Company</th>
              <th>Priority</th>
              <th>Signals</th>
              <th>Attention</th>
              <th>Themes</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock) => {
              const summary = signalMap.get(stock.ticker);
              const deleting = busyWatchlistKey === `stock:${stock.ticker}`;
              return (
                <tr key={stock.ticker}>
                  <td>
                    <button
                      className={`ticker-button ${
                        selectedTicker === stock.ticker ? "active" : ""
                      }`}
                      onClick={() => onSelectTicker(stock.ticker)}
                    >
                      {stock.ticker}
                    </button>
                    {stock.is_pinned ? <Star size={13} fill="currentColor" /> : null}
                  </td>
                  <td>{stock.company_name}</td>
                  <td>
                    <select
                      className={`field table-field priority-${stock.priority.toLowerCase()}`}
                      value={stock.priority}
                      onChange={(event) =>
                        onUpdateStock(stock.ticker, { priority: event.target.value })
                      }
                      disabled={disabled || deleting}
                      aria-label={`Priority for ${stock.ticker}`}
                    >
                      <option value="High">High</option>
                      <option value="Medium">Medium</option>
                      <option value="Low">Low</option>
                    </select>
                  </td>
                  <td>{summary?.signal_count ?? 0}</td>
                  <td>{Math.round((summary?.attention_score ?? 0) * 100)}</td>
                  <td>{stock.related_ai_themes.slice(0, 2).join(", ")}</td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="button icon-button"
                        onClick={() => onUpdateStock(stock.ticker, { is_pinned: !stock.is_pinned })}
                        disabled={disabled || deleting}
                        title={stock.is_pinned ? `Unpin ${stock.ticker}` : `Pin ${stock.ticker}`}
                        aria-label={
                          stock.is_pinned ? `Unpin ${stock.ticker}` : `Pin ${stock.ticker}`
                        }
                      >
                        {deleting ? (
                          <Loader2 className="spin" size={16} />
                        ) : (
                          <Star size={16} fill={stock.is_pinned ? "currentColor" : "none"} />
                        )}
                      </button>
                      <button
                        className="button icon-button"
                        onClick={() => onDeleteStock(stock.ticker)}
                        disabled={disabled || deleting}
                        title={`Remove ${stock.ticker}`}
                        aria-label={`Remove ${stock.ticker}`}
                      >
                        {deleting ? <Loader2 className="spin" size={16} /> : <Trash2 size={16} />}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <StockBriefingPanel
        briefing={stockBriefing}
        loading={busyStockTicker === selectedTicker && selectedTicker !== null}
        selectedTicker={selectedTicker}
      />
      {disclaimer ? <div className="small-muted">{disclaimer}</div> : null}
    </section>
  );
}

function StockBriefingPanel({
  briefing,
  loading,
  selectedTicker,
}: {
  briefing: StockBriefing | null;
  loading: boolean;
  selectedTicker: string | null;
}) {
  if (!selectedTicker) {
    return <div className="empty-state">No stock selected.</div>;
  }

  if (loading && !briefing) {
    return (
      <div className="stock-briefing">
        <div className="section-header">
          <h3 className="section-title">{selectedTicker} briefing</h3>
          <Loader2 className="spin" size={16} />
        </div>
      </div>
    );
  }

  if (!briefing || briefing.stock.ticker !== selectedTicker) {
    return <div className="empty-state">No briefing available for {selectedTicker}.</div>;
  }

  return (
    <div className="stock-briefing">
      <div className="section-header">
        <div>
          <h3 className="section-title">
            {briefing.stock.ticker} · {briefing.stock.company_name}
          </h3>
          <div className="small-muted">
            {briefing.latest_signal_at ? formatDate(briefing.latest_signal_at) : "No recent signal"}
          </div>
        </div>
        <span className={`urgency urgency-${briefing.urgency}`}>{briefing.urgency}</span>
      </div>

      <div className="score-grid">
        <div className="score-cell">
          <span className="score-label">Signals</span>
          <span className="score-value">{briefing.signal_count}</span>
        </div>
        <div className="score-cell">
          <span className="score-label">Attention</span>
          <span className="score-value">{Math.round(briefing.attention_score * 100)}</span>
        </div>
        <div className="score-cell">
          <span className="score-label">Positive</span>
          <span className="score-value">{briefing.sentiment_counts.positive ?? 0}</span>
        </div>
        <div className="score-cell">
          <span className="score-label">Mixed</span>
          <span className="score-value">{briefing.sentiment_counts.mixed ?? 0}</span>
        </div>
        <div className="score-cell">
          <span className="score-label">Negative</span>
          <span className="score-value">{briefing.sentiment_counts.negative ?? 0}</span>
        </div>
      </div>

      {briefing.key_themes.length ? (
        <div className="badges">
          {briefing.key_themes.map((theme) => (
            <span className="badge" key={theme}>
              {theme}
            </span>
          ))}
        </div>
      ) : null}

      <div className="stock-timeline">
        {briefing.recent_timeline.length ? (
          briefing.recent_timeline.map((entry) => (
            <a
              className="timeline-row"
              href={entry.item.url}
              target="_blank"
              rel="noreferrer"
              key={entry.item.id}
            >
              <div>
                <div className="timeline-title">{entry.item.title}</div>
                <div className="small-muted">
                  {entry.item.source_name}
                  {entry.item.published_at ? ` · ${formatDate(entry.item.published_at)}` : ""}
                </div>
                <div className="timeline-reason">{entry.reason}</div>
              </div>
              <div className="timeline-score">{Math.round(entry.signal_score * 100)}</div>
            </a>
          ))
        ) : (
          <div className="empty-state">No stock-linked signals yet.</div>
        )}
      </div>
    </div>
  );
}

function TopicTable({
  topics,
  topic,
  label,
  category,
  terms,
  disabled,
  busyWatchlistKey,
  onTopicChange,
  onLabelChange,
  onCategoryChange,
  onTermsChange,
  onUpdateTopic,
  onDeleteTopic,
  onSubmit,
}: {
  topics: TopicWatchlistItem[];
  topic: string;
  label: string;
  category: string;
  terms: string;
  disabled: boolean;
  busyWatchlistKey: string | null;
  onTopicChange: (value: string) => void;
  onLabelChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
  onTermsChange: (value: string) => void;
  onUpdateTopic: (
    topic: string,
    payload: Partial<Pick<TopicWatchlistItem, "priority" | "is_pinned" | "include_in_digest">>,
  ) => void;
  onDeleteTopic: (topic: string) => void;
  onSubmit: () => void;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Topic Watchlist</h2>
        <span className="small-muted">{topics.length} topics</span>
      </div>
      <div className="form-panel compact-form">
        <input
          className="field"
          value={topic}
          onChange={(event) => onTopicChange(event.target.value)}
          placeholder="Topic"
          aria-label="Topic"
        />
        <input
          className="field"
          value={label}
          onChange={(event) => onLabelChange(event.target.value)}
          placeholder="Label"
          aria-label="Topic label"
        />
        <select
          className="field"
          value={category}
          onChange={(event) => onCategoryChange(event.target.value)}
          aria-label="Topic category"
        >
          <option value="technical_trend">Trend</option>
          <option value="research">Research</option>
          <option value="product">Product</option>
          <option value="stock_company_event">Stock</option>
          <option value="social_trend">Social</option>
        </select>
        <input
          className="field"
          value={terms}
          onChange={(event) => onTermsChange(event.target.value)}
          placeholder="Terms"
          aria-label="Related terms"
        />
        <button className="button primary" onClick={onSubmit} disabled={disabled}>
          {disabled ? <Loader2 className="spin" size={16} /> : <Plus size={16} />}
          Add
        </button>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Topic</th>
              <th>Category</th>
              <th>Priority</th>
              <th>Terms</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {topics.map((topic) => {
              const deleting = busyWatchlistKey === `topic:${topic.topic}`;
              return (
                <tr key={topic.topic}>
                  <td>
                    <span className="ticker">{topic.label}</span>
                    {topic.is_pinned ? <Star size={13} fill="currentColor" /> : null}
                  </td>
                  <td>{topic.category}</td>
                  <td>
                    <select
                      className={`field table-field priority-${topic.priority.toLowerCase()}`}
                      value={topic.priority}
                      onChange={(event) =>
                        onUpdateTopic(topic.topic, { priority: event.target.value })
                      }
                      disabled={disabled || deleting}
                      aria-label={`Priority for ${topic.label}`}
                    >
                      <option value="High">High</option>
                      <option value="Medium">Medium</option>
                      <option value="Low">Low</option>
                    </select>
                  </td>
                  <td>{topic.related_terms.slice(0, 3).join(", ")}</td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="button icon-button"
                        onClick={() => onUpdateTopic(topic.topic, { is_pinned: !topic.is_pinned })}
                        disabled={disabled || deleting}
                        title={topic.is_pinned ? `Unpin ${topic.label}` : `Pin ${topic.label}`}
                        aria-label={topic.is_pinned ? `Unpin ${topic.label}` : `Pin ${topic.label}`}
                      >
                        {deleting ? (
                          <Loader2 className="spin" size={16} />
                        ) : (
                          <Star size={16} fill={topic.is_pinned ? "currentColor" : "none"} />
                        )}
                      </button>
                      <button
                        className={`button icon-button ${
                          topic.include_in_digest ? "active-icon-button" : ""
                        }`}
                        onClick={() =>
                          onUpdateTopic(topic.topic, {
                            include_in_digest: !topic.include_in_digest,
                          })
                        }
                        disabled={disabled || deleting}
                        title={
                          topic.include_in_digest
                            ? `Exclude ${topic.label} from digest`
                            : `Include ${topic.label} in digest`
                        }
                        aria-label={
                          topic.include_in_digest
                            ? `Exclude ${topic.label} from digest`
                            : `Include ${topic.label} in digest`
                        }
                      >
                        {deleting ? <Loader2 className="spin" size={16} /> : <CalendarDays size={16} />}
                      </button>
                      <button
                        className="button icon-button"
                        onClick={() => onDeleteTopic(topic.topic)}
                        disabled={disabled || deleting}
                        title={`Remove ${topic.label}`}
                        aria-label={`Remove ${topic.label}`}
                      >
                        {deleting ? <Loader2 className="spin" size={16} /> : <Trash2 size={16} />}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SourceTable({
  sources,
  busySourceId,
  onToggleSource,
}: {
  sources: SourceHealth[];
  busySourceId: number | null;
  onToggleSource: (source: SourceHealth) => void;
}) {
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
              <th>Enabled</th>
              <th>Status</th>
              <th>Stored</th>
              <th>Last Run</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.id}>
                <td>{source.name}</td>
                <td>{source.enabled ? "Yes" : "No"}</td>
                <td className={source.latest_status === "success" ? "health-ok" : ""}>
                  {source.latest_status}
                </td>
                <td>{source.items_stored}</td>
                <td>{source.last_finished_at ? formatDate(source.last_finished_at) : "never"}</td>
                <td>
                  <button
                    className="button"
                    onClick={() => onToggleSource(source)}
                    disabled={busySourceId === source.id}
                  >
                    {busySourceId === source.id ? (
                      <Loader2 className="spin" size={16} />
                    ) : null}
                    {source.enabled ? "Disable" : "Enable"}
                  </button>
                </td>
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

function splitTerms(value: string) {
  return value
    .split(",")
    .map((term) => term.trim())
    .filter(Boolean);
}

function clampWeight(value: number) {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.min(1, Math.max(0, Number(value.toFixed(2))));
}

function readError(err: unknown) {
  return err instanceof Error ? err.message : "Unexpected error";
}
