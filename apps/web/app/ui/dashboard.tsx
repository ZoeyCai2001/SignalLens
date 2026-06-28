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
  Save,
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
  classification_confidence: number;
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

type FeedItemDetail = FeedItem & {
  text: string | null;
  score_explanation: string;
  action_state: Record<string, boolean>;
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

type StockDetailDraft = {
  exchange: string;
  sector: string;
  industry: string;
  group_name: string;
  is_holding: boolean;
  shares: string;
  average_cost: string;
  notes: string;
};

type StockPricePoint = {
  price_date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  adjusted_close: number | null;
  volume: number | null;
};

type StockMarketSnapshot = {
  latest: StockPricePoint | null;
  previous_close: number | null;
  change: number | null;
  change_percent: number | null;
  history: StockPricePoint[];
};

type StockSignalSummary = {
  stock: StockWatchlistItem;
  signal_count: number;
  high_impact_count: number;
  attention_score: number;
  market: StockMarketSnapshot | null;
  latest_event_title: string | null;
  latest_event_at: string | null;
  sentiment_counts: Record<string, number>;
  top_signals: FeedItem[];
  disclaimer: string;
};

type StockBriefingTimelineItem = {
  item: FeedItem;
  signal_score: number;
  reason: string;
  event_type: string;
  possible_market_impact: string;
  confidence: number;
  time_sensitivity: string;
  event_summary: string;
  uncertainties: string[];
};

type StockThemeBreakdown = {
  theme: string;
  item_count: number;
};

type StockMarketImpactEvent = {
  event_type: string;
  item_count: number;
  latest_title: string | null;
  latest_at: string | null;
};

type StockBriefing = {
  stock: StockWatchlistItem;
  signal_count: number;
  attention_score: number;
  market: StockMarketSnapshot | null;
  urgency: string;
  latest_signal_at: string | null;
  sentiment_counts: Record<string, number>;
  key_themes: string[];
  ai_relevance_summary: string;
  theme_breakdown: StockThemeBreakdown[];
  market_impact_events: StockMarketImpactEvent[];
  recent_timeline: StockBriefingTimelineItem[];
  disclaimer: string;
};

type CompanyWatchlistItem = {
  company_key: string;
  company_name: string;
  ticker: string | null;
  category: string;
  priority: string;
  is_pinned: boolean;
  include_in_digest: boolean;
  related_terms: string[];
  notes: string | null;
};

type CompanyBriefing = {
  company: CompanyWatchlistItem;
  item_count: number;
  trending_sources: TopicSourceCount[];
  related_topics: string[];
  related_products: string[];
  related_tickers: string[];
  recent_timeline: FeedItem[];
  activity_timeline: TopicActivityBucket[];
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

type ProductWatchlistItem = {
  category: string;
  label: string;
  priority: string;
  is_pinned: boolean;
  include_in_digest: boolean;
  related_terms: string[];
  notes: string | null;
};

type ProductBriefing = {
  product: ProductWatchlistItem;
  item_count: number;
  trending_sources: TopicSourceCount[];
  matched_products: string[];
  related_companies: string[];
  recent_timeline: FeedItem[];
  activity_timeline: TopicActivityBucket[];
};

type TopicSourceCount = {
  source_name: string;
  item_count: number;
};

type TopicActivityBucket = {
  activity_date: string;
  item_count: number;
};

type TopicBriefing = {
  topic: TopicWatchlistItem;
  item_count: number;
  trending_sources: TopicSourceCount[];
  related_papers: FeedItem[];
  related_products: FeedItem[];
  related_companies: string[];
  recent_timeline: FeedItem[];
  activity_timeline: TopicActivityBucket[];
};

type SourceHealth = {
  id: number;
  name: string;
  type: string;
  access_method: string;
  base_url: string | null;
  auth_required: boolean;
  rate_limit: string | null;
  polling_interval: string | null;
  enabled: boolean;
  priority: number;
  terms_notes: string | null;
  latest_status: string;
  latest_error: string | null;
  last_started_at: string | null;
  last_finished_at: string | null;
  last_success_at: string | null;
  items_fetched: number;
  items_stored: number;
  failure_count: number;
  needs_attention: boolean;
};

type SourceRunHistoryItem = {
  id: number;
  source_id: number;
  source_name: string;
  status: string;
  items_fetched: number;
  items_stored: number;
  error_message: string | null;
  started_at: string;
  finished_at: string | null;
};

type IngestionRunResponse = {
  source_name: string;
  status: string;
  items_fetched: number;
  items_stored: number;
  error_message: string | null;
};

type ScheduledCycleResponse = {
  started_at: string;
  finished_at: string;
  seeded_stock_count: number;
  seeded_company_count: number;
  seeded_topic_count: number;
  seeded_product_count: number;
  generated_alert_count: number;
  saved_digest_date: string | null;
  ingestion_results: IngestionRunResponse[];
};

type FeedProcessingResponse = {
  requested_limit: number;
  candidates_seen: number;
  summarized_count: number;
  classified_count: number;
  skipped_count: number;
  item_ids: number[];
  errors: { item_id: number; stage: string; error: string }[];
};

type SearchIntent = {
  query: string | null;
  category: string | null;
  ticker: string | null;
  company: string | null;
  topic: string | null;
  language: string | null;
  date_from: string | null;
  min_importance_score: number | null;
  saved_only: boolean;
};

type NaturalLanguageSearchResponse = {
  intent: SearchIntent;
  items: FeedItem[];
};

type IntegrationStatus = {
  kimi_coding_api: boolean;
  github_api: boolean;
  product_hunt_api: boolean;
  alpha_vantage_api: boolean;
  chinese_rss_feeds: boolean;
};

type SetupItem = {
  key: string;
  label: string;
  configured: boolean;
  importance: "core" | "recommended" | "optional";
  required_for: string;
  env_var: string;
  setup_hint: string;
};

type SystemStatus = {
  status: string;
  service: string;
  environment: string;
  llm_provider: string;
  llm_model: string;
  llm_configured: boolean;
  integrations: IntegrationStatus;
  setup_items: SetupItem[];
};

type SourceUpdatePayload = {
  enabled?: boolean;
  priority?: number;
  rate_limit?: string | null;
  polling_interval?: string | null;
  terms_notes?: string | null;
};

type SourceCreatePayload = {
  name: string;
  type: string;
  access_method: string;
  base_url: string | null;
  enabled: boolean;
  priority: number;
  terms_notes: string | null;
};

type SourceDraft = {
  priority: string;
  polling_interval: string;
  rate_limit: string;
  terms_notes: string;
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
  watchlist_companies: string[];
  disclaimer: string;
};

type DailyDigestMarkdown = {
  digest_date: string;
  generated_at: string;
  markdown: string;
};

type DailyDigestSnapshot = {
  id: number;
  digest_date: string;
  generated_at: string;
  headline: string;
  total_items: number;
  limit_per_section: number;
  digest: DailyDigest;
  markdown: string;
  created_at: string;
  updated_at: string;
};

type EventCluster = {
  cluster_key: string;
  title: string;
  main_summary: string;
  category: string;
  topics: string[];
  tickers: string[];
  sources: string[];
  item_count: number;
  top_score: number;
  importance_score: number;
  confidence: number;
  earliest_source: string | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
  latest_update_at: string | null;
  timeline: EventClusterTimelineItem[];
  representative_item: FeedItem;
  items: FeedItem[];
};

type EventClusterTimelineItem = {
  item_id: number;
  title: string;
  source_name: string;
  published_at: string | null;
  importance_score: number;
};

type AlertItem = {
  id: number;
  title: string;
  reason: string;
  severity: string;
  status: string;
  created_at: string;
  rule: AlertRule;
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
  preferred_sources: string[];
  blocked_sources: string[];
};

type IngestionSource =
  | "hacker-news"
  | "alpha-vantage-news"
  | "alpha-vantage-prices"
  | "arxiv"
  | "chinese-rss"
  | "github"
  | "hugging-face"
  | "product-hunt"
  | "rss";

type LoadState = "idle" | "loading" | "running";
type DashboardOperation =
  | "refresh"
  | "cycle"
  | "llm:classify"
  | "llm:summarize"
  | `ingest:${IngestionSource}`;
type ModuleKey =
  | "dashboard"
  | "trends"
  | "research"
  | "products"
  | "stocks"
  | "chinese"
  | "saved"
  | "digest";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const STOCK_DISCLAIMER =
  "SignalLens links AI-related items to watched stocks for research only and does not provide investment advice.";

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

const moduleNavItems: { key: ModuleKey; label: string; icon: typeof Activity }[] = [
  { key: "dashboard", label: "Dashboard", icon: Activity },
  { key: "trends", label: "AI Trends", icon: TrendingUp },
  { key: "research", label: "Research", icon: FlaskConical },
  { key: "products", label: "Products", icon: Bot },
  { key: "stocks", label: "AI Stocks", icon: BarChart3 },
  { key: "chinese", label: "Chinese Social", icon: Newspaper },
  { key: "saved", label: "Saved Items", icon: Bookmark },
  { key: "digest", label: "Daily Digest", icon: CalendarDays },
];

export function Dashboard() {
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [selectedFeedDetail, setSelectedFeedDetail] = useState<FeedItemDetail | null>(null);
  const [savedItems, setSavedItems] = useState<FeedItem[]>([]);
  const [stocks, setStocks] = useState<StockWatchlistItem[]>([]);
  const [stockSignals, setStockSignals] = useState<StockSignalSummary[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [stockBriefing, setStockBriefing] = useState<StockBriefing | null>(null);
  const [companies, setCompanies] = useState<CompanyWatchlistItem[]>([]);
  const [selectedCompanyKey, setSelectedCompanyKey] = useState<string | null>(null);
  const [companyBriefing, setCompanyBriefing] = useState<CompanyBriefing | null>(null);
  const [productWatchlist, setProductWatchlist] = useState<ProductWatchlistItem[]>([]);
  const [selectedProductCategory, setSelectedProductCategory] = useState<string | null>(null);
  const [productBriefing, setProductBriefing] = useState<ProductBriefing | null>(null);
  const [topics, setTopics] = useState<TopicWatchlistItem[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [topicBriefing, setTopicBriefing] = useState<TopicBriefing | null>(null);
  const [sources, setSources] = useState<SourceHealth[]>([]);
  const [sourceRuns, setSourceRuns] = useState<SourceRunHistoryItem[]>([]);
  const [lastCycleResult, setLastCycleResult] = useState<ScheduledCycleResponse | null>(null);
  const [digest, setDigest] = useState<DailyDigest | null>(null);
  const [digestSnapshots, setDigestSnapshots] = useState<DailyDigestSnapshot[]>([]);
  const [eventClusters, setEventClusters] = useState<EventCluster[]>([]);
  const [selectedEventCluster, setSelectedEventCluster] = useState<EventCluster | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [rankingDraft, setRankingDraft] = useState<RankingWeights>(DEFAULT_RANKING_WEIGHTS);
  const [preferredSourcesDraft, setPreferredSourcesDraft] = useState("");
  const [blockedSourcesDraft, setBlockedSourcesDraft] = useState("");
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [activeOperation, setActiveOperation] = useState<DashboardOperation | null>(null);
  const [status, setStatus] = useState("Ready");
  const [error, setError] = useState<string | null>(null);
  const [activeModule, setActiveModule] = useState<ModuleKey>("dashboard");
  const [busyItemId, setBusyItemId] = useState<number | null>(null);
  const [busyDetailItemId, setBusyDetailItemId] = useState<number | null>(null);
  const [busyAlertId, setBusyAlertId] = useState<number | null>(null);
  const [busyAlertRuleId, setBusyAlertRuleId] = useState<number | null>(null);
  const [busyClusterKey, setBusyClusterKey] = useState<string | null>(null);
  const [busySourceId, setBusySourceId] = useState<number | null>(null);
  const [busyStockTicker, setBusyStockTicker] = useState<string | null>(null);
  const [busyCompanyBriefing, setBusyCompanyBriefing] = useState<string | null>(null);
  const [busyProductBriefing, setBusyProductBriefing] = useState<string | null>(null);
  const [busyTopicBriefing, setBusyTopicBriefing] = useState<string | null>(null);
  const [busyWatchlistKey, setBusyWatchlistKey] = useState<string | null>(null);
  const [busyPreferences, setBusyPreferences] = useState(false);
  const [busyDigestCopy, setBusyDigestCopy] = useState(false);
  const [busyDigestSave, setBusyDigestSave] = useState(false);
  const [manualTitle, setManualTitle] = useState("");
  const [manualUrl, setManualUrl] = useState("");
  const [manualText, setManualText] = useState("");
  const [stockTicker, setStockTicker] = useState("");
  const [stockCompany, setStockCompany] = useState("");
  const [stockThemes, setStockThemes] = useState("");
  const [stockKeywords, setStockKeywords] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [companyTicker, setCompanyTicker] = useState("");
  const [companyCategory, setCompanyCategory] = useState("ai_company");
  const [companyTerms, setCompanyTerms] = useState("");
  const [topicName, setTopicName] = useState("");
  const [topicLabel, setTopicLabel] = useState("");
  const [topicCategory, setTopicCategory] = useState("technical_trend");
  const [topicTerms, setTopicTerms] = useState("");
  const [productCategory, setProductCategory] = useState("");
  const [productLabel, setProductLabel] = useState("");
  const [productTerms, setProductTerms] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [sourceType, setSourceType] = useState("blog");
  const [sourceAccessMethod, setSourceAccessMethod] = useState("rss");
  const [sourceBaseUrl, setSourceBaseUrl] = useState("");
  const [sourceTermsNotes, setSourceTermsNotes] = useState("");
  const [alertRuleName, setAlertRuleName] = useState("");
  const [alertRuleCategory, setAlertRuleCategory] = useState("all");
  const [alertRuleTickers, setAlertRuleTickers] = useState("");
  const [alertRuleTopics, setAlertRuleTopics] = useState("");
  const [alertRuleImportance, setAlertRuleImportance] = useState("0.75");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchSource, setSearchSource] = useState("");
  const [searchCategory, setSearchCategory] = useState("");
  const [searchTicker, setSearchTicker] = useState("");
  const [searchCompany, setSearchCompany] = useState("");
  const [searchTopic, setSearchTopic] = useState("");
  const [searchLanguage, setSearchLanguage] = useState("");
  const [searchDateFrom, setSearchDateFrom] = useState("");
  const [searchDateTo, setSearchDateTo] = useState("");
  const [searchMinImportance, setSearchMinImportance] = useState("");
  const [searchIntent, setSearchIntent] = useState<SearchIntent | null>(null);
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

  const refreshAll = useCallback(async (operation?: DashboardOperation) => {
    if (operation) {
      setActiveOperation(operation);
    }
    setLoadState("loading");
    setError(null);
    try {
      const [
        nextFeed,
        nextSavedItems,
        nextStocks,
        nextStockSignals,
        nextCompanies,
        nextProductWatchlist,
        nextTopics,
        nextSources,
        nextSourceRuns,
        nextDigest,
        nextDigestSnapshots,
        nextEventClusters,
        nextAlerts,
        nextAlertRules,
        nextPreferences,
        nextSystemStatus,
      ] =
        await Promise.all([
          fetchJson<FeedItem[]>("/api/feed?limit=30"),
          fetchJson<FeedItem[]>("/api/feed?limit=30&saved_only=true"),
          fetchJson<StockWatchlistItem[]>("/api/watchlist/stocks"),
          fetchJson<StockSignalSummary[]>("/api/watchlist/stocks/signals/summary"),
          fetchJson<CompanyWatchlistItem[]>("/api/watchlist/companies"),
          fetchJson<ProductWatchlistItem[]>("/api/watchlist/products"),
          fetchJson<TopicWatchlistItem[]>("/api/watchlist/topics"),
          fetchJson<SourceHealth[]>("/api/sources/health"),
          fetchJson<SourceRunHistoryItem[]>("/api/sources/runs?limit=8"),
          fetchJson<DailyDigest>("/api/digest/daily"),
          fetchJson<DailyDigestSnapshot[]>("/api/digest/daily/snapshots?limit=5"),
          fetchJson<EventCluster[]>("/api/events/clusters?limit=8&min_items=2"),
          fetchJson<AlertItem[]>("/api/alerts?limit=8"),
          fetchJson<AlertRule[]>("/api/alerts/rules"),
          fetchJson<UserPreferences>("/api/preferences"),
          fetchJson<SystemStatus>("/api/health"),
        ]);
      setFeed(nextFeed);
      setSavedItems(nextSavedItems);
      setStocks(nextStocks);
      setStockSignals(nextStockSignals);
      setCompanies(nextCompanies);
      setProductWatchlist(nextProductWatchlist);
      setTopics(nextTopics);
      setSources(nextSources);
      setSourceRuns(nextSourceRuns);
      setDigest(nextDigest);
      setDigestSnapshots(nextDigestSnapshots);
      setEventClusters(nextEventClusters);
      setAlerts(nextAlerts);
      setAlertRules(nextAlertRules);
      setPreferences(nextPreferences);
      setSystemStatus(nextSystemStatus);
      setRankingDraft(nextPreferences.ranking_weights);
      setPreferredSourcesDraft(nextPreferences.preferred_sources.join(", "));
      setBlockedSourcesDraft(nextPreferences.blocked_sources.join(", "));
      setStatus(`Loaded ${nextFeed.length} feed items`);
    } catch (err) {
      setError(readError(err));
      setStatus("Backend unavailable");
    } finally {
      setLoadState("idle");
      if (operation) {
        setActiveOperation(null);
      }
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
    if (!selectedProductCategory && productWatchlist.length) {
      setSelectedProductCategory(productWatchlist[0].category);
    }
  }, [productWatchlist, selectedProductCategory]);

  useEffect(() => {
    if (!selectedCompanyKey && companies.length) {
      setSelectedCompanyKey(companies[0].company_key);
    }
  }, [companies, selectedCompanyKey]);

  useEffect(() => {
    if (!selectedTopic && topics.length) {
      setSelectedTopic(topics[0].topic);
    }
  }, [selectedTopic, topics]);

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

  useEffect(() => {
    if (!selectedProductCategory) {
      setProductBriefing(null);
      return;
    }

    let cancelled = false;
    setBusyProductBriefing(selectedProductCategory);
    fetchJson<ProductBriefing>(
      `/api/watchlist/products/${encodeURIComponent(selectedProductCategory)}/briefing?limit=20`,
    )
      .then((briefing) => {
        if (!cancelled) {
          setProductBriefing(briefing);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(readError(err));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setBusyProductBriefing(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fetchJson, selectedProductCategory]);

  useEffect(() => {
    if (!selectedCompanyKey) {
      setCompanyBriefing(null);
      return;
    }

    let cancelled = false;
    setBusyCompanyBriefing(selectedCompanyKey);
    fetchJson<CompanyBriefing>(
      `/api/watchlist/companies/${encodeURIComponent(selectedCompanyKey)}/briefing?limit=20`,
    )
      .then((briefing) => {
        if (!cancelled) {
          setCompanyBriefing(briefing);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(readError(err));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setBusyCompanyBriefing(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fetchJson, selectedCompanyKey]);

  useEffect(() => {
    if (!selectedTopic) {
      setTopicBriefing(null);
      return;
    }

    let cancelled = false;
    setBusyTopicBriefing(selectedTopic);
    fetchJson<TopicBriefing>(
      `/api/watchlist/topics/${encodeURIComponent(selectedTopic)}/briefing?limit=20`,
    )
      .then((briefing) => {
        if (!cancelled) {
          setTopicBriefing(briefing);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(readError(err));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setBusyTopicBriefing(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fetchJson, selectedTopic]);

  const runIngestion = async (source: IngestionSource) => {
    setActiveOperation(`ingest:${source}`);
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
      setActiveOperation(null);
    }
  };

  const runFullCycle = async () => {
    setActiveOperation("cycle");
    setLoadState("running");
    setError(null);
    try {
      const result = await fetchJson<ScheduledCycleResponse>("/api/ingestion/cycle", {
        method: "POST",
      });
      setLastCycleResult(result);
      const storedCount = result.ingestion_results.reduce(
        (total, item) => total + item.items_stored,
        0,
      );
      await refreshAll();
      setLastCycleResult(result);
      setStatus(
        `Cycle completed: ${storedCount} stored, ${result.generated_alert_count} alerts, ${result.seeded_stock_count + result.seeded_company_count + result.seeded_topic_count + result.seeded_product_count} watchlist defaults, digest ${result.saved_digest_date ?? "not saved"}`,
      );
    } catch (err) {
      setError(readError(err));
      setStatus("Full ingestion cycle failed");
    } finally {
      setLoadState("idle");
      setActiveOperation(null);
    }
  };

  const processTopItemsWithLlm = async ({
    summarize,
    classify,
    label,
    operation,
  }: {
    summarize: boolean;
    classify: boolean;
    label: string;
    operation: DashboardOperation;
  }) => {
    setActiveOperation(operation);
    setLoadState("running");
    setError(null);
    try {
      const result = await fetchJson<FeedProcessingResponse>("/api/llm/process-feed", {
        method: "POST",
        body: JSON.stringify({
          limit: 3,
          summarize,
          classify,
          skip_summarized: true,
          skip_classified: true,
          min_classification_confidence: 0.7,
        }),
      });
      setStatus(
        `${label}: ${result.classified_count} classified, ${result.summarized_count} summarized, ${result.skipped_count} skipped`,
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
      setActiveOperation(null);
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
        body: JSON.stringify({
          ranking_weights: rankingDraft,
          preferred_sources: splitTerms(preferredSourcesDraft),
          blocked_sources: splitTerms(blockedSourcesDraft),
        }),
      });
      setPreferences(updated);
      setRankingDraft(updated.ranking_weights);
      setPreferredSourcesDraft(updated.preferred_sources.join(", "));
      setBlockedSourcesDraft(updated.blocked_sources.join(", "));
      setStatus("Updated ranking preferences");
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
      const hasManualFilters = [
        searchSource,
        searchCategory,
        searchTicker,
        searchCompany,
        searchTopic,
        searchLanguage,
        searchDateFrom,
        searchDateTo,
        searchMinImportance,
      ].some((value) => value.trim()) || savedOnly;

      if (searchQuery.trim() && !hasManualFilters) {
        const result = await fetchJson<NaturalLanguageSearchResponse>(
          "/api/search/natural-language",
          {
            method: "POST",
            body: JSON.stringify({ query: searchQuery.trim(), limit: 30 }),
          },
        );
        setFeed(result.items);
        setSearchIntent(result.intent);
        setStatus(`Search returned ${result.items.length} items`);
        return;
      }

      const params = new URLSearchParams();
      if (searchQuery.trim()) params.set("q", searchQuery.trim());
      if (searchSource.trim()) params.set("source", searchSource.trim());
      if (searchCategory.trim()) params.set("category", searchCategory.trim());
      if (searchTicker.trim()) params.set("ticker", searchTicker.trim().toUpperCase());
      if (searchCompany.trim()) params.set("company", searchCompany.trim());
      if (searchTopic.trim()) params.set("topic", searchTopic.trim());
      if (searchLanguage.trim()) params.set("language", searchLanguage.trim().toLowerCase());
      if (searchDateFrom.trim()) params.set("date_from", searchDateFrom.trim());
      if (searchDateTo.trim()) params.set("date_to", searchDateTo.trim());
      if (searchMinImportance.trim()) {
        params.set("min_importance_score", searchMinImportance.trim());
      }
      if (savedOnly) params.set("saved_only", "true");
      params.set("limit", "30");

      const results = await fetchJson<FeedItem[]>(`/api/search?${params.toString()}`);
      setFeed(results);
      setSearchIntent(null);
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
    setSearchCompany("");
    setSearchTopic("");
    setSearchLanguage("");
    setSearchDateFrom("");
    setSearchDateTo("");
    setSearchMinImportance("");
    setSearchIntent(null);
    setSavedOnly(false);
    await refreshAll();
  };

  const updateSearchField = (setter: (value: string) => void, value: string) => {
    setter(value);
    setSearchIntent(null);
  };

  const updateSavedOnlySearchFilter = (value: boolean) => {
    setSavedOnly(value);
    setSearchIntent(null);
  };

  const copyDailyDigest = async () => {
    setBusyDigestCopy(true);
    setError(null);
    try {
      const result = await fetchJson<DailyDigestMarkdown>("/api/digest/daily/markdown");
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard API unavailable.");
      }
      await navigator.clipboard.writeText(result.markdown);
      setStatus(`Copied digest ${result.digest_date}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Digest copy failed");
    } finally {
      setBusyDigestCopy(false);
    }
  };

  const saveDailyDigestSnapshot = async () => {
    setBusyDigestSave(true);
    setError(null);
    try {
      const snapshot = await fetchJson<DailyDigestSnapshot>("/api/digest/daily/snapshots", {
        method: "POST",
      });
      setDigest(snapshot.digest);
      setDigestSnapshots((items) => [
        snapshot,
        ...items.filter((item) => item.digest_date !== snapshot.digest_date),
      ].slice(0, 5));
      setStatus(`Saved digest snapshot ${snapshot.digest_date}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Digest snapshot failed");
    } finally {
      setBusyDigestSave(false);
    }
  };

  const loadFeedDetail = async (itemId: number) => {
    if (selectedFeedDetail?.id === itemId) {
      setSelectedFeedDetail(null);
      return;
    }

    setBusyDetailItemId(itemId);
    setError(null);
    try {
      const detail = await fetchJson<FeedItemDetail>(`/api/feed/${itemId}`);
      setSelectedFeedDetail(detail);
      setStatus(`Loaded item ${itemId} details`);
    } catch (err) {
      setError(readError(err));
      setStatus("Item detail failed");
    } finally {
      setBusyDetailItemId(null);
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
    payload: Partial<Omit<StockWatchlistItem, "ticker">>,
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

  const submitCompany = async () => {
    if (!companyName.trim()) {
      setError("Company watchlist entries need a company name.");
      return;
    }

    setLoadState("running");
    setError(null);
    try {
      const created = await fetchJson<CompanyWatchlistItem>("/api/watchlist/companies", {
        method: "POST",
        body: JSON.stringify({
          company_name: companyName.trim(),
          ticker: companyTicker.trim() || null,
          category: companyCategory,
          related_terms: splitTerms(companyTerms),
        }),
      });
      setCompanies((items) => [
        created,
        ...items.filter((item) => item.company_key !== created.company_key),
      ]);
      setSelectedCompanyKey(created.company_key);
      setCompanyName("");
      setCompanyTicker("");
      setCompanyCategory("ai_company");
      setCompanyTerms("");
      setStatus(`Added company ${created.company_name}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Company add failed");
    } finally {
      setLoadState("idle");
    }
  };

  const updateCompany = async (
    companyKey: string,
    payload: Partial<Pick<CompanyWatchlistItem, "priority" | "is_pinned" | "include_in_digest">>,
  ) => {
    const key = `company:${companyKey}`;
    setBusyWatchlistKey(key);
    setError(null);
    try {
      const updated = await fetchJson<CompanyWatchlistItem>(
        `/api/watchlist/companies/${encodeURIComponent(companyKey)}`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        },
      );
      setCompanies((items) =>
        items.map((item) => (item.company_key === updated.company_key ? updated : item)),
      );
      if (companyBriefing?.company.company_key === updated.company_key) {
        setCompanyBriefing({ ...companyBriefing, company: updated });
      }
      setStatus(`Updated company ${updated.company_name}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Company update failed");
    } finally {
      setBusyWatchlistKey(null);
    }
  };

  const deleteCompany = async (companyKey: string) => {
    const key = `company:${companyKey}`;
    setBusyWatchlistKey(key);
    setError(null);
    try {
      await sendRequest(`/api/watchlist/companies/${encodeURIComponent(companyKey)}`, {
        method: "DELETE",
      });
      const remainingCompanies = companies.filter((item) => item.company_key !== companyKey);
      setCompanies(remainingCompanies);
      if (selectedCompanyKey === companyKey) {
        setSelectedCompanyKey(remainingCompanies[0]?.company_key ?? null);
        setCompanyBriefing(null);
      }
      setStatus(`Removed company ${companyKey}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Company remove failed");
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
      setSelectedTopic(created.topic);
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
      const remainingTopics = topics.filter((item) => item.topic !== topic);
      setTopics(remainingTopics);
      if (selectedTopic === topic) {
        setSelectedTopic(remainingTopics[0]?.topic ?? null);
        setTopicBriefing(null);
      }
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
      if (topicBriefing?.topic.topic === updated.topic) {
        setTopicBriefing({ ...topicBriefing, topic: updated });
      }
      setStatus(`Updated topic ${updated.label}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Topic update failed");
    } finally {
      setBusyWatchlistKey(null);
    }
  };

  const submitProductCategory = async () => {
    if (!productCategory.trim()) {
      setError("Product watchlist entries need a category.");
      return;
    }

    setLoadState("running");
    setError(null);
    try {
      const created = await fetchJson<ProductWatchlistItem>("/api/watchlist/products", {
        method: "POST",
        body: JSON.stringify({
          category: productCategory.trim(),
          label: productLabel.trim() || null,
          related_terms: splitTerms(productTerms),
        }),
      });
      setProductWatchlist((items) => [
        created,
        ...items.filter((item) => item.category !== created.category),
      ]);
      setSelectedProductCategory(created.category);
      setProductCategory("");
      setProductLabel("");
      setProductTerms("");
      setStatus(`Added product category ${created.label}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Product category add failed");
    } finally {
      setLoadState("idle");
    }
  };

  const updateProductCategory = async (
    category: string,
    payload: Partial<Pick<ProductWatchlistItem, "priority" | "is_pinned" | "include_in_digest">>,
  ) => {
    const key = `product:${category}`;
    setBusyWatchlistKey(key);
    setError(null);
    try {
      const updated = await fetchJson<ProductWatchlistItem>(
        `/api/watchlist/products/${encodeURIComponent(category)}`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        },
      );
      setProductWatchlist((items) =>
        items.map((item) => (item.category === updated.category ? updated : item)),
      );
      if (productBriefing?.product.category === updated.category) {
        setProductBriefing({ ...productBriefing, product: updated });
      }
      setStatus(`Updated product category ${updated.label}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Product category update failed");
    } finally {
      setBusyWatchlistKey(null);
    }
  };

  const deleteProductCategory = async (category: string) => {
    const key = `product:${category}`;
    setBusyWatchlistKey(key);
    setError(null);
    try {
      await sendRequest(`/api/watchlist/products/${encodeURIComponent(category)}`, {
        method: "DELETE",
      });
      const remainingProducts = productWatchlist.filter((item) => item.category !== category);
      setProductWatchlist(remainingProducts);
      if (selectedProductCategory === category) {
        setSelectedProductCategory(remainingProducts[0]?.category ?? null);
        setProductBriefing(null);
      }
      setStatus(`Removed product category ${category}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Product category remove failed");
    } finally {
      setBusyWatchlistKey(null);
    }
  };

  const updateFeedAction = async (
    itemId: number,
    action: "save" | "unsave" | "hide" | "mark-important",
  ) => {
    setBusyItemId(itemId);
    setError(null);
    try {
      const updated = await fetchJson<FeedItem>(`/api/feed/${itemId}/${action}`, {
        method: "POST",
      });
      if (action === "hide") {
        setFeed((items) => items.filter((item) => item.id !== itemId));
        setSavedItems((items) => items.filter((item) => item.id !== itemId));
        setStatus(`Hidden item ${itemId}`);
      } else if (action === "unsave") {
        setFeed((items) => items.map((item) => (item.id === itemId ? updated : item)));
        setSavedItems((items) => items.filter((item) => item.id !== itemId));
        setStatus(`Removed saved item ${itemId}`);
      } else {
        setFeed((items) => items.map((item) => (item.id === itemId ? updated : item)));
        if (action === "save") {
          setSavedItems((items) => [updated, ...items.filter((item) => item.id !== itemId)]);
        }
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

  const toggleAlertRule = async (rule: AlertRule) => {
    setBusyAlertRuleId(rule.id);
    setError(null);
    try {
      const updated = await fetchJson<AlertRule>(`/api/alerts/rules/${rule.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !rule.enabled }),
      });
      setAlertRules((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setStatus(`${updated.enabled ? "Enabled" : "Disabled"} alert rule ${updated.name}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Alert rule update failed");
    } finally {
      setBusyAlertRuleId(null);
    }
  };

  const deleteAlertRule = async (ruleId: number) => {
    setBusyAlertRuleId(ruleId);
    setError(null);
    try {
      await sendRequest(`/api/alerts/rules/${ruleId}`, { method: "DELETE" });
      setAlertRules((items) => items.filter((item) => item.id !== ruleId));
      setAlerts((items) => items.filter((item) => item.rule.id !== ruleId));
      setStatus(`Deleted alert rule ${ruleId}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Alert rule delete failed");
    } finally {
      setBusyAlertRuleId(null);
    }
  };

  const loadEventCluster = async (cluster: EventCluster) => {
    if (selectedEventCluster?.cluster_key === cluster.cluster_key) {
      setSelectedEventCluster(null);
      return;
    }

    setBusyClusterKey(cluster.cluster_key);
    setError(null);
    try {
      const detail = await fetchJson<EventCluster>(
        `/api/events/clusters/${encodeURIComponent(cluster.cluster_key)}`,
      );
      setSelectedEventCluster(detail);
      setStatus(`Loaded cluster with ${detail.item_count} item${detail.item_count === 1 ? "" : "s"}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Cluster load failed");
    } finally {
      setBusyClusterKey(null);
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
    await updateSource(source, { enabled: !source.enabled });
  };

  const updateSource = async (source: SourceHealth, payload: SourceUpdatePayload) => {
    setBusySourceId(source.id);
    setError(null);
    try {
      const updated = await fetchJson<SourceHealth>(`/api/sources/${source.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setSources((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setStatus(`Updated ${updated.name}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Source update failed");
    } finally {
      setBusySourceId(null);
    }
  };

  const submitSource = async () => {
    if (!sourceName.trim()) {
      setError("Source entries need a name.");
      return;
    }
    setLoadState("running");
    setError(null);
    try {
      const created = await fetchJson<SourceHealth>("/api/sources", {
        method: "POST",
        body: JSON.stringify({
          name: sourceName.trim(),
          type: sourceType,
          access_method: sourceAccessMethod,
          base_url: sourceBaseUrl.trim() || null,
          enabled: true,
          priority: 90,
          terms_notes: sourceTermsNotes.trim() || null,
        } satisfies SourceCreatePayload),
      });
      setSourceName("");
      setSourceType("blog");
      setSourceAccessMethod("rss");
      setSourceBaseUrl("");
      setSourceTermsNotes("");
      setSources((items) => [...items, created].sort((a, b) => a.priority - b.priority));
      setStatus(`Following source ${created.name}`);
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Source add failed");
    } finally {
      setLoadState("idle");
    }
  };

  const runSourceNow = async (source: SourceHealth) => {
    setBusySourceId(source.id);
    setError(null);
    try {
      const result = await fetchJson<{
        source_name: string;
        status: string;
        items_fetched: number;
        items_stored: number;
      }>(`/api/sources/${source.id}/run`, { method: "POST" });
      setStatus(
        `${result.source_name}: ${result.status}, ${result.items_fetched} fetched, ${result.items_stored} stored`,
      );
      await refreshAll();
    } catch (err) {
      setError(readError(err));
      setStatus("Source run failed");
    } finally {
      setBusySourceId(null);
    }
  };

  const moduleCounts = useMemo(
    () => buildModuleCounts(feed, digest, savedItems),
    [digest, feed, savedItems],
  );
  const moduleFeed = useMemo(
    () => filterFeedByModule(feed, activeModule, digest, savedItems),
    [activeModule, digest, feed, savedItems],
  );
  const activeModuleLabel =
    moduleNavItems.find((item) => item.key === activeModule)?.label ?? "Dashboard";

  const metrics = useMemo(() => {
    const highImportance = moduleFeed.filter((item) => item.importance_score >= 0.75).length;
    const summarized = moduleFeed.filter((item) => item.summary_detailed).length;
    return [
      { label: "Feed", value: feed.length },
      { label: "View", value: moduleFeed.length },
      { label: "High", value: highImportance },
      { label: "Alerts", value: alerts.length },
      { label: "Summaries", value: summarized },
    ];
  }, [alerts.length, feed.length, moduleFeed]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-title">SignalLens</div>
          <div className="brand-subtitle">Personal AI intelligence dashboard</div>
        </div>
        <nav className="nav-list" aria-label="Primary">
          {moduleNavItems.map((item) => {
            const Icon = item.icon;
            const active = item.key === activeModule;
            return (
              <button
                className={`nav-item ${active ? "active" : ""}`}
                key={item.key}
                onClick={() => setActiveModule(item.key)}
                type="button"
              >
                <Icon size={16} aria-hidden="true" />
                <span>{item.label}</span>
                <span className="nav-count">{moduleCounts[item.key]}</span>
              </button>
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
              onClick={runFullCycle}
              disabled={loadState !== "idle"}
              title="Run full ingestion cycle, generate alerts, and save a digest snapshot"
            >
              {activeOperation === "cycle" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <DatabaseZap size={16} />
              )}
              Cycle
            </button>
            <button
              className="button"
              onClick={() => runIngestion("hacker-news")}
              disabled={loadState !== "idle"}
              title="Run Hacker News ingestion"
            >
              {activeOperation === "ingest:hacker-news" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <Newspaper size={16} />
              )}
              HN
            </button>
            <button
              className="button"
              onClick={() => runIngestion("alpha-vantage-news")}
              disabled={loadState !== "idle"}
              title="Run Alpha Vantage stock news ingestion"
            >
              {activeOperation === "ingest:alpha-vantage-news" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <BarChart3 size={16} />
              )}
              Stocks
            </button>
            <button
              className="button"
              onClick={() => runIngestion("alpha-vantage-prices")}
              disabled={loadState !== "idle"}
              title="Run Alpha Vantage daily price ingestion"
            >
              {activeOperation === "ingest:alpha-vantage-prices" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <TrendingUp size={16} />
              )}
              Prices
            </button>
            <button
              className="button"
              onClick={() => runIngestion("arxiv")}
              disabled={loadState !== "idle"}
              title="Run arXiv ingestion"
            >
              {activeOperation === "ingest:arxiv" ? (
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
              {activeOperation === "ingest:chinese-rss" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <Newspaper size={16} />
              )}
              CN
            </button>
            <button
              className="button"
              onClick={() => runIngestion("github")}
              disabled={loadState !== "idle"}
              title="Run GitHub repository ingestion"
            >
              {activeOperation === "ingest:github" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <Github size={16} />
              )}
              GitHub
            </button>
            <button
              className="button"
              onClick={() => runIngestion("hugging-face")}
              disabled={loadState !== "idle"}
              title="Run Hugging Face model ingestion"
            >
              {activeOperation === "ingest:hugging-face" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <Bot size={16} />
              )}
              HF
            </button>
            <button
              className="button"
              onClick={() => runIngestion("product-hunt")}
              disabled={loadState !== "idle"}
              title="Run Product Hunt launch ingestion"
            >
              {activeOperation === "ingest:product-hunt" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <Rocket size={16} />
              )}
              PH
            </button>
            <button
              className="button"
              onClick={() => runIngestion("rss")}
              disabled={loadState !== "idle"}
              title="Run selected RSS feed ingestion"
            >
              {activeOperation === "ingest:rss" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <Newspaper size={16} />
              )}
              RSS
            </button>
            <button
              className="button icon-button"
              onClick={() => refreshAll("refresh")}
              disabled={loadState !== "idle"}
              title="Refresh dashboard"
              aria-label="Refresh dashboard"
            >
              {activeOperation === "refresh" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <RefreshCw size={16} />
              )}
            </button>
            <button
              className="button"
              onClick={() =>
                processTopItemsWithLlm({
                  summarize: false,
                  classify: true,
                  label: "LLM classify",
                  operation: "llm:classify",
                })
              }
              disabled={loadState !== "idle"}
              title="Classify top feed items with Kimi"
            >
              {activeOperation === "llm:classify" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <Bot size={16} />
              )}
              Classify
            </button>
            <button
              className="button"
              onClick={() =>
                processTopItemsWithLlm({
                  summarize: true,
                  classify: false,
                  label: "LLM summarize",
                  operation: "llm:summarize",
                })
              }
              disabled={loadState !== "idle"}
              title="Summarize top feed items with Kimi"
            >
              {activeOperation === "llm:summarize" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <Bot size={16} />
              )}
              Summarize
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
              <h2 className="section-title">
                {activeModule === "dashboard" ? "Ranked Feed" : `${activeModuleLabel} Feed`}
              </h2>
              <span className="small-muted">{moduleFeed.length} items</span>
            </div>
            <SearchPanel
              query={searchQuery}
              source={searchSource}
              category={searchCategory}
              ticker={searchTicker}
              company={searchCompany}
              topic={searchTopic}
              language={searchLanguage}
              dateFrom={searchDateFrom}
              dateTo={searchDateTo}
              minImportance={searchMinImportance}
              intent={searchIntent}
              savedOnly={savedOnly}
              disabled={loadState !== "idle"}
              onQueryChange={(value) => updateSearchField(setSearchQuery, value)}
              onSourceChange={(value) => updateSearchField(setSearchSource, value)}
              onCategoryChange={(value) => updateSearchField(setSearchCategory, value)}
              onTickerChange={(value) => updateSearchField(setSearchTicker, value)}
              onCompanyChange={(value) => updateSearchField(setSearchCompany, value)}
              onTopicChange={(value) => updateSearchField(setSearchTopic, value)}
              onLanguageChange={(value) => updateSearchField(setSearchLanguage, value)}
              onDateFromChange={(value) => updateSearchField(setSearchDateFrom, value)}
              onDateToChange={(value) => updateSearchField(setSearchDateTo, value)}
              onMinImportanceChange={(value) => updateSearchField(setSearchMinImportance, value)}
              onSavedOnlyChange={updateSavedOnlySearchFilter}
              onSearch={runSearch}
              onClear={clearSearch}
            />
            <div className="feed-list">
              {moduleFeed.length ? (
                moduleFeed.map((item) => (
                  <FeedCard
                    item={item}
                    key={item.id}
                    busy={busyItemId === item.id}
                    detail={selectedFeedDetail?.id === item.id ? selectedFeedDetail : null}
                    busyDetail={busyDetailItemId === item.id}
                    onSummarize={summarizeItem}
                    onClassify={classifyItem}
                    onDetail={loadFeedDetail}
                    onAction={updateFeedAction}
                  />
                ))
              ) : (
                <div className="empty-state">No items for this module.</div>
              )}
            </div>
          </section>

          <aside className="stack">
            <SystemStatusPanel
              status={systemStatus}
              itemCount={feed.length}
              sourceCount={sources.length}
              enabledSourceCount={sources.filter((source) => source.enabled).length}
              alertCount={alerts.length}
              watchlistCount={stocks.length + companies.length + topics.length + productWatchlist.length}
            />
            <RankingPreferencesPanel
              preferences={preferences}
              draft={rankingDraft}
              preferredSources={preferredSourcesDraft}
              blockedSources={blockedSourcesDraft}
              disabled={loadState !== "idle"}
              busy={busyPreferences}
              onDraftChange={updateRankingDraft}
              onPreferredSourcesChange={setPreferredSourcesDraft}
              onBlockedSourcesChange={setBlockedSourcesDraft}
              onReset={() => setRankingDraft(DEFAULT_RANKING_WEIGHTS)}
              onSave={saveRankingPreferences}
            />
            <AlertPanel
              alerts={alerts}
              rules={alertRules}
              busyAlertId={busyAlertId}
              busyAlertRuleId={busyAlertRuleId}
              ruleName={alertRuleName}
              ruleCategory={alertRuleCategory}
              ruleTickers={alertRuleTickers}
              ruleTopics={alertRuleTopics}
              ruleImportance={alertRuleImportance}
              disabled={loadState !== "idle"}
              onDismiss={dismissAlert}
              onRuleToggle={toggleAlertRule}
              onRuleDelete={deleteAlertRule}
              onRuleNameChange={setAlertRuleName}
              onRuleCategoryChange={setAlertRuleCategory}
              onRuleTickersChange={setAlertRuleTickers}
              onRuleTopicsChange={setAlertRuleTopics}
              onRuleImportanceChange={setAlertRuleImportance}
              onRuleSubmit={submitAlertRule}
            />
            <DailyDigestPanel
              digest={digest}
              snapshotCount={digestSnapshots.length}
              busyCopy={busyDigestCopy}
              busySave={busyDigestSave}
              onCopy={copyDailyDigest}
              onSave={saveDailyDigestSnapshot}
            />
            <SavedItemsPanel
              items={savedItems.slice(0, 8)}
              busyItemId={busyItemId}
              onUnsave={(itemId) => updateFeedAction(itemId, "unsave")}
            />
            <ChineseSocialPanel items={feed} />
            <EventClusterPanel
              clusters={eventClusters}
              selectedCluster={selectedEventCluster}
              busyClusterKey={busyClusterKey}
              onSelectCluster={loadEventCluster}
            />
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
            <CompanyWatchlistPanel
              companies={companies}
              briefing={companyBriefing}
              selectedCompanyKey={selectedCompanyKey}
              busyCompanyBriefing={busyCompanyBriefing}
              name={companyName}
              ticker={companyTicker}
              category={companyCategory}
              terms={companyTerms}
              disabled={loadState !== "idle"}
              busyWatchlistKey={busyWatchlistKey}
              onNameChange={setCompanyName}
              onTickerChange={setCompanyTicker}
              onCategoryChange={setCompanyCategory}
              onTermsChange={setCompanyTerms}
              onSelect={setSelectedCompanyKey}
              onUpdate={updateCompany}
              onDelete={deleteCompany}
              onSubmit={submitCompany}
            />
            <TopicTable
              topics={topics}
              topicBriefing={topicBriefing}
              selectedTopic={selectedTopic}
              busyTopicBriefing={busyTopicBriefing}
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
              onSelectTopic={setSelectedTopic}
              onUpdateTopic={updateTopic}
              onDeleteTopic={deleteTopic}
              onSubmit={submitTopic}
            />
            <ProductWatchlistPanel
              items={productWatchlist}
              briefing={productBriefing}
              selectedCategory={selectedProductCategory}
              busyProductBriefing={busyProductBriefing}
              category={productCategory}
              label={productLabel}
              terms={productTerms}
              disabled={loadState !== "idle"}
              busyWatchlistKey={busyWatchlistKey}
              onCategoryChange={setProductCategory}
              onLabelChange={setProductLabel}
              onTermsChange={setProductTerms}
              onSelect={setSelectedProductCategory}
              onUpdate={updateProductCategory}
              onDelete={deleteProductCategory}
              onSubmit={submitProductCategory}
            />
            <SourceTable
              sources={sources}
              runs={sourceRuns}
              lastCycleResult={lastCycleResult}
              name={sourceName}
              type={sourceType}
              accessMethod={sourceAccessMethod}
              baseUrl={sourceBaseUrl}
              termsNotes={sourceTermsNotes}
              disabled={loadState !== "idle"}
              busySourceId={busySourceId}
              onNameChange={setSourceName}
              onTypeChange={setSourceType}
              onAccessMethodChange={setSourceAccessMethod}
              onBaseUrlChange={setSourceBaseUrl}
              onTermsNotesChange={setSourceTermsNotes}
              onSubmit={submitSource}
              onRunSource={runSourceNow}
              onToggleSource={toggleSource}
              onUpdateSource={updateSource}
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
  preferredSources,
  blockedSources,
  disabled,
  busy,
  onDraftChange,
  onPreferredSourcesChange,
  onBlockedSourcesChange,
  onReset,
  onSave,
}: {
  preferences: UserPreferences | null;
  draft: RankingWeights;
  preferredSources: string;
  blockedSources: string;
  disabled: boolean;
  busy: boolean;
  onDraftChange: (key: keyof RankingWeights, value: number) => void;
  onPreferredSourcesChange: (value: string) => void;
  onBlockedSourcesChange: (value: string) => void;
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
        <div className="weights-grid">
          <label className="weight-field">
            <span className="field-label">Preferred Sources</span>
            <input
              className="field"
              value={preferredSources}
              onChange={(event) => onPreferredSourcesChange(event.target.value)}
              placeholder="GitHub, arXiv"
              disabled={disabled || busy}
            />
          </label>
          <label className="weight-field">
            <span className="field-label">Blocked Sources</span>
            <input
              className="field"
              value={blockedSources}
              onChange={(event) => onBlockedSourcesChange(event.target.value)}
              placeholder="Noisy Feed"
              disabled={disabled || busy}
            />
          </label>
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

function SystemStatusPanel({
  status,
  itemCount,
  sourceCount,
  enabledSourceCount,
  alertCount,
  watchlistCount,
}: {
  status: SystemStatus | null;
  itemCount: number;
  sourceCount: number;
  enabledSourceCount: number;
  alertCount: number;
  watchlistCount: number;
}) {
  const integrationRows: Array<[string, boolean]> = status
    ? [
        ["Kimi", status.integrations.kimi_coding_api],
        ["GitHub", status.integrations.github_api],
        ["Alpha Vantage", status.integrations.alpha_vantage_api],
        ["Product Hunt", status.integrations.product_hunt_api],
        ["Chinese RSS", status.integrations.chinese_rss_feeds],
      ]
    : [];

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">System Readiness</h2>
        <DatabaseZap size={16} aria-hidden="true" />
      </div>
      <div className="digest-panel">
        {status ? (
          <>
            <div className="readiness-head">
              <div>
                <div className="digest-section-title">{status.environment}</div>
                <div className="digest-headline">
                  {status.llm_provider} · {status.llm_model}
                </div>
              </div>
              <span className={`badge ${status.llm_configured ? "" : "muted-badge"}`}>
                {status.llm_configured ? "LLM ready" : "LLM key missing"}
              </span>
            </div>
            <div className="readiness-grid">
              <ReadinessMetric label="Items" value={itemCount} />
              <ReadinessMetric label="Sources" value={`${enabledSourceCount}/${sourceCount}`} />
              <ReadinessMetric label="Alerts" value={alertCount} />
              <ReadinessMetric label="Watchlist" value={watchlistCount} />
            </div>
            <div className="badges">
              {integrationRows.map(([label, ready]) => (
                <span className={`badge ${ready ? "" : "muted-badge"}`} key={label}>
                  {label} {ready ? "on" : "off"}
                </span>
              ))}
            </div>
            <div className="setup-list">
              {status.setup_items.map((item) => (
                <div className="setup-row" key={item.key}>
                  <div>
                    <div className="setup-title-row">
                      <div className="digest-section-title">{item.label}</div>
                      <span className={`badge ${setupImportanceClass(item.importance)}`}>
                        {item.importance}
                      </span>
                    </div>
                    <div className="small-muted">
                      {item.env_var} · {item.required_for}
                    </div>
                    {!item.configured ? (
                      <div className="setup-hint">{item.setup_hint}</div>
                    ) : null}
                  </div>
                  <span className={`badge ${item.configured ? "" : "muted-badge"}`}>
                    {item.configured ? "ready" : "missing"}
                  </span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="empty-state">System status unavailable.</div>
        )}
      </div>
    </section>
  );
}

function ReadinessMetric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="readiness-metric">
      <span className="score-label">{label}</span>
      <span className="score-value">{value}</span>
    </div>
  );
}

function setupImportanceClass(importance: SetupItem["importance"]): string {
  if (importance === "core") {
    return "";
  }
  return "muted-badge";
}

function AlertPanel({
  alerts,
  rules,
  busyAlertId,
  busyAlertRuleId,
  ruleName,
  ruleCategory,
  ruleTickers,
  ruleTopics,
  ruleImportance,
  disabled,
  onDismiss,
  onRuleToggle,
  onRuleDelete,
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
  busyAlertRuleId: number | null;
  ruleName: string;
  ruleCategory: string;
  ruleTickers: string;
  ruleTopics: string;
  ruleImportance: string;
  disabled: boolean;
  onDismiss: (alertId: number) => void;
  onRuleToggle: (rule: AlertRule) => void;
  onRuleDelete: (ruleId: number) => void;
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
          <option value="cross_source_cluster">Cross-source</option>
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
      <div className="alert-rule-list">
        {rules.slice(0, 6).map((rule) => (
          <div className={`alert-rule-row ${rule.enabled ? "" : "muted"}`} key={rule.id}>
            <div>
              <div className="digest-link">{rule.name}</div>
              <div className="small-muted">
                {rule.category} · {rule.severity} · min{" "}
                {Math.round(rule.min_importance_score * 100)}
                {rule.tickers.length ? ` · ${rule.tickers.join(", ")}` : ""}
              </div>
            </div>
            <div className="table-actions">
              <button
                className={`button icon-button ${rule.enabled ? "active-icon-button" : ""}`}
                onClick={() => onRuleToggle(rule)}
                disabled={disabled || busyAlertRuleId === rule.id}
                title={rule.enabled ? "Disable alert rule" : "Enable alert rule"}
                aria-label={rule.enabled ? "Disable alert rule" : "Enable alert rule"}
                type="button"
              >
                {busyAlertRuleId === rule.id ? (
                  <Loader2 className="spin" size={16} />
                ) : rule.enabled ? (
                  <BellRing size={16} />
                ) : (
                  <EyeOff size={16} />
                )}
              </button>
              <button
                className="button icon-button"
                onClick={() => onRuleDelete(rule.id)}
                disabled={disabled || busyAlertRuleId === rule.id}
                title="Delete alert rule"
                aria-label="Delete alert rule"
                type="button"
              >
                {busyAlertRuleId === rule.id ? (
                  <Loader2 className="spin" size={16} />
                ) : (
                  <Trash2 size={16} />
                )}
              </button>
            </div>
          </div>
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

function DailyDigestPanel({
  digest,
  snapshotCount,
  busyCopy,
  busySave,
  onCopy,
  onSave,
}: {
  digest: DailyDigest | null;
  snapshotCount: number;
  busyCopy: boolean;
  busySave: boolean;
  onCopy: () => void;
  onSave: () => void;
}) {
  const sectionsWithItems = digest?.sections.filter((section) => section.items.length) ?? [];
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Daily Digest</h2>
        <div className="table-actions">
          <button
            className="button icon-button"
            onClick={onSave}
            disabled={!digest || busySave}
            title="Save digest snapshot"
            aria-label="Save digest snapshot"
          >
            {busySave ? <Loader2 className="spin" size={16} /> : <DatabaseZap size={16} />}
          </button>
          <button
            className="button icon-button"
            onClick={onCopy}
            disabled={!digest || busyCopy}
            title="Copy digest markdown"
            aria-label="Copy digest markdown"
          >
            {busyCopy ? <Loader2 className="spin" size={16} /> : <FileText size={16} />}
          </button>
        </div>
      </div>
      {digest ? (
        <div className="digest-panel">
          <div className="digest-meta">
            <span>{digest.digest_date}</span>
            <span>
              {digest.total_items} items · {snapshotCount} saved
            </span>
          </div>
          <div className="digest-headline">{digest.headline}</div>
          <div className="digest-coverage">
            {digest.watchlist_tickers.slice(0, 4).map((ticker) => (
              <span className="badge stock" key={`ticker:${ticker}`}>
                {ticker}
              </span>
            ))}
            {digest.watchlist_companies.slice(0, 4).map((company) => (
              <span className="badge" key={`company:${company}`}>
                {company}
              </span>
            ))}
          </div>
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

function SavedItemsPanel({
  items,
  busyItemId,
  onUnsave,
}: {
  items: FeedItem[];
  busyItemId: number | null;
  onUnsave: (itemId: number) => void;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Saved Items</h2>
        <Bookmark size={16} aria-hidden="true" />
      </div>
      <div className="digest-panel">
        {items.length ? (
          <div className="digest-list">
            {items.map((item) => (
              <div className="saved-row" key={item.id}>
                <a className="digest-link" href={item.url} target="_blank" rel="noreferrer">
                  {item.title}
                </a>
                <button
                  className="button icon-button"
                  onClick={() => onUnsave(item.id)}
                  disabled={busyItemId === item.id}
                  title="Remove saved item"
                  aria-label="Remove saved item"
                >
                  {busyItemId === item.id ? <Loader2 className="spin" size={16} /> : <X size={16} />}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">No saved items yet.</div>
        )}
      </div>
    </section>
  );
}

function EventClusterPanel({
  clusters,
  selectedCluster,
  busyClusterKey,
  onSelectCluster,
}: {
  clusters: EventCluster[];
  selectedCluster: EventCluster | null;
  busyClusterKey: string | null;
  onSelectCluster: (cluster: EventCluster) => void;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Event Clusters</h2>
        <span className="small-muted">{clusters.length} clusters</span>
      </div>
      <div className="digest-panel">
        {clusters.length ? (
          clusters.slice(0, 5).map((cluster) => {
            const expanded = selectedCluster?.cluster_key === cluster.cluster_key;
            const detail = expanded ? selectedCluster : cluster;
            return (
              <div className="digest-section" key={cluster.cluster_key}>
                <div className="cluster-head">
                  <div>
                    <div className="digest-section-title">
                      {cluster.item_count} item{cluster.item_count === 1 ? "" : "s"} ·{" "}
                      {cluster.sources.slice(0, 2).join(", ")}
                    </div>
                    <div className="small-muted">
                      Confidence {Math.round(cluster.confidence * 100)} · Importance{" "}
                      {Math.round(cluster.importance_score * 100)}
                      {cluster.earliest_source ? ` · first ${cluster.earliest_source}` : ""}
                      {cluster.latest_update_at
                        ? ` · latest ${formatDate(cluster.latest_update_at)}`
                        : ""}
                    </div>
                    <a
                      className="digest-link"
                      href={cluster.representative_item.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {cluster.title}
                    </a>
                  </div>
                  <button
                    className={`button icon-button ${expanded ? "active-icon-button" : ""}`}
                    onClick={() => onSelectCluster(cluster)}
                    disabled={busyClusterKey === cluster.cluster_key}
                    title={expanded ? "Hide cluster evidence" : "View cluster evidence"}
                    aria-label={expanded ? "Hide cluster evidence" : "View cluster evidence"}
                    type="button"
                  >
                    {busyClusterKey === cluster.cluster_key ? (
                      <Loader2 className="spin" size={16} />
                    ) : (
                      <FileText size={16} />
                    )}
                  </button>
                </div>
                <div className="badges">
                  {[...cluster.tickers, ...cluster.topics.slice(0, 3)].map((label) => (
                    <span className="badge" key={label}>
                      {label}
                    </span>
                  ))}
                </div>
                <div className="summary">{cluster.main_summary}</div>
                <div className="cluster-timeline">
                  {cluster.timeline.slice(0, 4).map((event) => (
                    <div
                      className="cluster-timeline-row"
                      key={`${cluster.cluster_key}-${event.item_id}`}
                    >
                      <span>{event.published_at ? formatDate(event.published_at) : "undated"}</span>
                      <span>{event.source_name}</span>
                      <span>{Math.round(event.importance_score * 100)}</span>
                    </div>
                  ))}
                </div>
                {expanded ? (
                  <div className="cluster-evidence-list">
                    {detail.items.map((item) => (
                      <a
                        className="cluster-evidence-row"
                        href={item.url}
                        key={item.id}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <span>{item.title}</span>
                        <span className="small-muted">
                          {item.source_name} · {Math.round(item.importance_score * 100)}
                          {item.published_at ? ` · ${formatDate(item.published_at)}` : ""}
                        </span>
                      </a>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })
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
  company,
  topic,
  language,
  dateFrom,
  dateTo,
  minImportance,
  intent,
  savedOnly,
  disabled,
  onQueryChange,
  onSourceChange,
  onCategoryChange,
  onTickerChange,
  onCompanyChange,
  onTopicChange,
  onLanguageChange,
  onDateFromChange,
  onDateToChange,
  onMinImportanceChange,
  onSavedOnlyChange,
  onSearch,
  onClear,
}: {
  query: string;
  source: string;
  category: string;
  ticker: string;
  company: string;
  topic: string;
  language: string;
  dateFrom: string;
  dateTo: string;
  minImportance: string;
  intent: SearchIntent | null;
  savedOnly: boolean;
  disabled: boolean;
  onQueryChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
  onTickerChange: (value: string) => void;
  onCompanyChange: (value: string) => void;
  onTopicChange: (value: string) => void;
  onLanguageChange: (value: string) => void;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
  onMinImportanceChange: (value: string) => void;
  onSavedOnlyChange: (value: boolean) => void;
  onSearch: () => void;
  onClear: () => void;
}) {
  const intentChips = buildSearchIntentChips(intent);

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
          value={company}
          onChange={(event) => onCompanyChange(event.target.value)}
          placeholder="Company"
        />
        <input
          className="field"
          value={topic}
          onChange={(event) => onTopicChange(event.target.value)}
          placeholder="Topic"
        />
        <select
          className="field"
          value={language}
          onChange={(event) => onLanguageChange(event.target.value)}
          aria-label="Language filter"
        >
          <option value="">Any language</option>
          <option value="en">English</option>
          <option value="zh">Chinese</option>
        </select>
      </div>
      <div className="filter-row advanced-filter-row">
        <input
          className="field"
          type="date"
          value={dateFrom}
          onChange={(event) => onDateFromChange(event.target.value)}
          aria-label="Date from"
        />
        <input
          className="field"
          type="date"
          value={dateTo}
          onChange={(event) => onDateToChange(event.target.value)}
          aria-label="Date to"
        />
        <input
          className="field"
          type="number"
          min="0"
          max="1"
          step="0.05"
          value={minImportance}
          onChange={(event) => onMinImportanceChange(event.target.value)}
          placeholder="Min importance"
          aria-label="Minimum importance score"
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
      {intentChips.length ? (
        <div className="intent-row" aria-label="Interpreted search filters">
          {intentChips.map((chip) => (
            <span className="badge" key={chip}>
              {chip}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function FeedCard({
  item,
  busy,
  detail,
  busyDetail,
  onSummarize,
  onClassify,
  onDetail,
  onAction,
}: {
  item: FeedItem;
  busy: boolean;
  detail: FeedItemDetail | null;
  busyDetail: boolean;
  onSummarize: (itemId: number) => void;
  onClassify: (itemId: number) => void;
  onDetail: (itemId: number) => void;
  onAction: (
    itemId: number,
    action: "save" | "unsave" | "hide" | "mark-important",
  ) => void;
}) {
  const displaySummary = item.summary_detailed || item.summary_short;
  const cardExplanation = buildFeedCardExplanation(item);
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
        <Score label="Confidence" value={item.classification_confidence} />
        <Score label="Source" value={item.source_quality_score} />
        <Score label="Importance" value={item.importance_score} />
        <Score label="Novelty" value={item.novelty_score} />
        <Score label="Stock" value={item.stock_impact_score} />
      </div>

      {displaySummary ? <div className="summary">{displaySummary}</div> : null}

      <div className="why-card">
        <div className="why-card-label">Why am I seeing this?</div>
        <div>{cardExplanation}</div>
      </div>

      <div className="feed-actions">
        <div className="small-muted">{item.author ? `by ${item.author}` : "source-linked item"}</div>
        <div className="toolbar">
          <button
            className="button icon-button"
            onClick={() => onAction(item.id, item.is_saved ? "unsave" : "save")}
            disabled={busy}
            title={item.is_saved ? "Remove saved item" : "Save item"}
            aria-label={item.is_saved ? "Remove saved item" : "Save item"}
          >
            {busy ? (
              <Loader2 className="spin" size={16} />
            ) : (
              <Bookmark size={16} fill={item.is_saved ? "currentColor" : "none"} />
            )}
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
            onClick={() => onDetail(item.id)}
            disabled={busyDetail}
            title="Show item details"
          >
            {busyDetail ? <Loader2 className="spin" size={16} /> : <Search size={16} />}
            Details
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
      {detail ? <FeedDetailPanel detail={detail} /> : null}
    </article>
  );
}

function buildFeedCardExplanation(item: FeedItem): string {
  const relatedSignals = [...item.tickers, ...item.topics.slice(0, 3)];
  const scoreSignals = [
    item.classification_confidence >= 0.8 ? "high classifier confidence" : null,
    item.classification_confidence < 0.6 ? "lower classifier confidence" : null,
    item.source_quality_score >= 0.8 ? "high source credibility" : null,
    item.source_quality_score < 0.6 ? "lower source credibility" : null,
    item.relevance_score >= 0.72 ? "high AI relevance" : null,
    item.importance_score >= 0.72 ? "high importance" : null,
    item.novelty_score >= 0.72 ? "novel signal" : null,
    item.stock_impact_score >= 0.45 ? "stock-watchlist impact" : null,
  ].filter(Boolean);
  const signalText =
    scoreSignals.length > 0 ? scoreSignals.join(", ") : "matched the current source and category filters";
  const relatedText = relatedSignals.length > 0 ? ` Related: ${relatedSignals.join(", ")}.` : "";

  if (item.why_it_matters?.trim()) {
    return `${item.why_it_matters.trim()} Signals: ${signalText}.${relatedText}`;
  }

  return `${formatCategoryLabel(item.category)} item selected because it has ${signalText}.${relatedText}`;
}

function FeedDetailPanel({ detail }: { detail: FeedItemDetail }) {
  return (
    <div className="feed-detail-panel">
      <div className="section-header">
        <h4 className="section-title">Item Details</h4>
        <span className="small-muted">{detail.language}</span>
      </div>
      <div className="summary">{detail.score_explanation}</div>
      <div className="score-grid">
        <Score label="Source" value={detail.source_quality_score} />
        <Score label="Relevance" value={detail.relevance_score} />
        <Score label="Importance" value={detail.importance_score} />
        <Score label="Stock" value={detail.stock_impact_score} />
      </div>
      <div className="badges">
        {detail.companies.slice(0, 6).map((company) => (
          <span className="badge" key={company}>
            {company}
          </span>
        ))}
        {detail.products.slice(0, 6).map((product) => (
          <span className="badge" key={product}>
            {product}
          </span>
        ))}
      </div>
      {detail.why_it_matters ? (
        <div className="summary">
          <strong>Why it matters:</strong> {detail.why_it_matters}
        </div>
      ) : null}
      {detail.text ? <div className="detail-text">{detail.text}</div> : null}
    </div>
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
    payload: Partial<Omit<StockWatchlistItem, "ticker">>,
  ) => void;
  onDeleteStock: (ticker: string) => void;
  onSubmit: () => void;
}) {
  const signalMap = new Map(signalSummaries.map((summary) => [summary.stock.ticker, summary]));
  const disclaimer =
    signalSummaries[0]?.disclaimer ?? stockBriefing?.disclaimer ?? STOCK_DISCLAIMER;
  const selectedStock = stocks.find((stock) => stock.ticker === selectedTicker) ?? null;
  const [detailDraft, setDetailDraft] = useState<StockDetailDraft>(() =>
    stockToDetailDraft(selectedStock),
  );
  const [portfolioFieldsEnabled, setPortfolioFieldsEnabled] = useState(() =>
    hasPortfolioDetails(selectedStock),
  );
  const detailBusy = selectedStock ? busyWatchlistKey === `stock:${selectedStock.ticker}` : false;

  useEffect(() => {
    setDetailDraft(stockToDetailDraft(selectedStock));
    setPortfolioFieldsEnabled(hasPortfolioDetails(selectedStock));
  }, [selectedStock]);

  const updateDetailDraft = (key: keyof StockDetailDraft, value: string | boolean) => {
    setDetailDraft((current) => ({ ...current, [key]: value }));
  };

  const saveStockDetails = () => {
    if (!selectedStock) {
      return;
    }
    const payload: Partial<Omit<StockWatchlistItem, "ticker">> = {
      exchange: detailDraft.exchange.trim(),
      sector: detailDraft.sector.trim(),
      industry: detailDraft.industry.trim(),
      group_name: detailDraft.group_name.trim(),
      notes: detailDraft.notes.trim() || null,
    };
    if (portfolioFieldsEnabled) {
      payload.is_holding = detailDraft.is_holding;
      payload.shares = parseOptionalNumber(detailDraft.shares);
      payload.average_cost = parseOptionalNumber(detailDraft.average_cost);
    }
    onUpdateStock(selectedStock.ticker, payload);
  };

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
              <th>Price</th>
              <th>Change</th>
              <th>Priority</th>
              <th>Signals</th>
              <th>High</th>
              <th>Latest Event</th>
              <th>Sentiment</th>
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
                  <td>{formatPrice(summary?.market?.latest?.close_price)}</td>
                  <td className={marketChangeClass(summary?.market?.change ?? null)}>
                    {formatChange(summary?.market)}
                  </td>
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
                  <td>{summary?.high_impact_count ?? 0}</td>
                  <td className="table-event-cell">
                    {summary?.latest_event_title ?? "--"}
                    {summary?.latest_event_at ? (
                      <div className="small-muted">{formatDate(summary.latest_event_at)}</div>
                    ) : null}
                  </td>
                  <td>{formatDominantSentiment(summary?.sentiment_counts)}</td>
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
      <StockDetailEditor
        stock={selectedStock}
        draft={detailDraft}
        portfolioFieldsEnabled={portfolioFieldsEnabled}
        disabled={disabled || detailBusy}
        onDraftChange={updateDetailDraft}
        onPortfolioFieldsEnabledChange={setPortfolioFieldsEnabled}
        onSave={saveStockDetails}
      />
      <StockBriefingPanel
        briefing={stockBriefing}
        loading={busyStockTicker === selectedTicker && selectedTicker !== null}
        selectedTicker={selectedTicker}
      />
      <div className="small-muted">{disclaimer}</div>
    </section>
  );
}

function StockDetailEditor({
  stock,
  draft,
  portfolioFieldsEnabled,
  disabled,
  onDraftChange,
  onPortfolioFieldsEnabledChange,
  onSave,
}: {
  stock: StockWatchlistItem | null;
  draft: StockDetailDraft;
  portfolioFieldsEnabled: boolean;
  disabled: boolean;
  onDraftChange: (key: keyof StockDetailDraft, value: string | boolean) => void;
  onPortfolioFieldsEnabledChange: (value: boolean) => void;
  onSave: () => void;
}) {
  if (!stock) {
    return <div className="empty-state">Select a stock to edit watchlist details.</div>;
  }

  return (
    <div className="form-panel stock-detail-form">
      <div className="section-header">
        <div>
          <h3 className="section-title">{stock.ticker} watchlist details</h3>
          <div className="small-muted">{stock.company_name}</div>
        </div>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={portfolioFieldsEnabled}
            onChange={(event) => onPortfolioFieldsEnabledChange(event.target.checked)}
            disabled={disabled}
          />
          Portfolio notes
        </label>
      </div>
      <div className="stock-detail-grid">
        <label className="weight-field">
          <span className="field-label">Exchange</span>
          <input
            className="field"
            value={draft.exchange}
            onChange={(event) => onDraftChange("exchange", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Sector</span>
          <input
            className="field"
            value={draft.sector}
            onChange={(event) => onDraftChange("sector", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Industry</span>
          <input
            className="field"
            value={draft.industry}
            onChange={(event) => onDraftChange("industry", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Group</span>
          <input
            className="field"
            value={draft.group_name}
            onChange={(event) => onDraftChange("group_name", event.target.value)}
            disabled={disabled}
          />
        </label>
      </div>
      {portfolioFieldsEnabled ? (
        <div className="stock-detail-grid">
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={draft.is_holding}
              onChange={(event) => onDraftChange("is_holding", event.target.checked)}
              disabled={disabled}
            />
            Holding
          </label>
          <label className="weight-field">
            <span className="field-label">Shares</span>
            <input
              className="field"
              type="number"
              min="0"
              step="any"
              inputMode="decimal"
              value={draft.shares}
              onChange={(event) => onDraftChange("shares", event.target.value)}
              disabled={disabled}
            />
          </label>
          <label className="weight-field">
            <span className="field-label">Average Cost</span>
            <input
              className="field"
              type="number"
              min="0"
              step="any"
              inputMode="decimal"
              value={draft.average_cost}
              onChange={(event) => onDraftChange("average_cost", event.target.value)}
              disabled={disabled}
            />
          </label>
        </div>
      ) : null}
      <label className="weight-field">
        <span className="field-label">Notes</span>
        <textarea
          className="field textarea"
          value={draft.notes}
          onChange={(event) => onDraftChange("notes", event.target.value)}
          disabled={disabled}
        />
      </label>
      <div className="toolbar">
        <button className="button primary" onClick={onSave} disabled={disabled}>
          {disabled ? <Loader2 className="spin" size={16} /> : <FileText size={16} />}
          Save
        </button>
      </div>
    </div>
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
          <span className="score-label">Price</span>
          <span className="score-value">{formatPrice(briefing.market?.latest?.close_price)}</span>
        </div>
        <div className="score-cell">
          <span className="score-label">Change</span>
          <span className={`score-value ${marketChangeClass(briefing.market?.change ?? null)}`}>
            {formatChange(briefing.market)}
          </span>
        </div>
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

      <StockPriceChart market={briefing.market} />

      <div className="stock-detail-grid-view">
        <div className="digest-section">
          <div className="digest-section-title">Company Overview</div>
          <div className="summary">
            {briefing.stock.exchange} · {briefing.stock.sector} · {briefing.stock.industry}
          </div>
          <div className="summary">{briefing.ai_relevance_summary}</div>
          {briefing.stock.notes ? (
            <div className="small-muted">Notes: {briefing.stock.notes}</div>
          ) : null}
        </div>
        <div className="digest-section">
          <div className="digest-section-title">Theme Breakdown</div>
          {briefing.theme_breakdown.length ? (
            <div className="theme-breakdown-list">
              {briefing.theme_breakdown.map((theme) => (
                <span className="badge" key={theme.theme}>
                  {theme.theme} · {theme.item_count}
                </span>
              ))}
            </div>
          ) : (
            <div className="empty-state">No recurring themes yet.</div>
          )}
        </div>
      </div>

      <div className="digest-section">
        <div className="digest-section-title">Market-Impact Events</div>
        {briefing.market_impact_events.length ? (
          <div className="impact-event-list">
            {briefing.market_impact_events.map((event) => (
              <div className="impact-event-row" key={event.event_type}>
                <div>
                  <div className="digest-link">{formatCategoryLabel(event.event_type)}</div>
                  <div className="small-muted">
                    {event.item_count} item{event.item_count === 1 ? "" : "s"}
                    {event.latest_at ? ` · latest ${formatDate(event.latest_at)}` : ""}
                  </div>
                  {event.latest_title ? (
                    <div className="timeline-reason">{event.latest_title}</div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">No market-impact buckets yet.</div>
        )}
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
                <div className="timeline-event-classification">
                  <span className="badge">{formatCategoryLabel(entry.event_type)}</span>
                  <span
                    className={`badge ${
                      entry.possible_market_impact === "positive" ? "success-badge" : ""
                    }`}
                  >
                    Impact: {entry.possible_market_impact}
                  </span>
                  <span className="badge">Confidence {Math.round(entry.confidence * 100)}</span>
                  <span className="badge">Time: {entry.time_sensitivity}</span>
                </div>
                <div className="timeline-reason">{entry.event_summary}</div>
                {entry.uncertainties.length ? (
                  <div className="small-muted">
                    Uncertainty: {entry.uncertainties.slice(0, 2).join(" ")}
                  </div>
                ) : null}
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

function StockPriceChart({ market }: { market: StockMarketSnapshot | null }) {
  const history = market?.history ?? [];
  if (history.length < 2) {
    return <div className="empty-state">No price history loaded yet.</div>;
  }

  const width = 280;
  const height = 76;
  const padding = 8;
  const closes = history.map((point) => point.close_price);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const chartPoints = history.map((point, index) => {
    const x = padding + (index / (history.length - 1)) * (width - padding * 2);
    const y = height - padding - ((point.close_price - min) / range) * (height - padding * 2);
    return { x, y };
  });
  const points = chartPoints.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
  const latestChartPoint = chartPoints[chartPoints.length - 1]!;
  const first = history[0]!;
  const latest = history[history.length - 1]!;
  const trendClass = marketChangeClass(market?.change ?? null);

  return (
    <div className="price-chart" aria-label="Recent stock price chart">
      <div className="price-chart-head">
        <span className="digest-section-title">Price History</span>
        <span className={`small-muted ${trendClass}`}>{formatChange(market)}</span>
      </div>
      <svg className="price-chart-svg" viewBox={`0 0 ${width} ${height}`} role="img">
        <polyline className="price-chart-line" points={points} />
        <circle
          className="price-chart-dot"
          cx={latestChartPoint.x}
          cy={latestChartPoint.y}
          r="3"
        />
      </svg>
      <div className="price-chart-meta">
        <span>
          {first.price_date} · {formatPrice(first.close_price)}
        </span>
        <span>
          {latest.price_date} · {formatPrice(latest.close_price)}
        </span>
      </div>
    </div>
  );
}

function CompanyWatchlistPanel({
  companies,
  briefing,
  selectedCompanyKey,
  busyCompanyBriefing,
  name,
  ticker,
  category,
  terms,
  disabled,
  busyWatchlistKey,
  onNameChange,
  onTickerChange,
  onCategoryChange,
  onTermsChange,
  onSelect,
  onUpdate,
  onDelete,
  onSubmit,
}: {
  companies: CompanyWatchlistItem[];
  briefing: CompanyBriefing | null;
  selectedCompanyKey: string | null;
  busyCompanyBriefing: string | null;
  name: string;
  ticker: string;
  category: string;
  terms: string;
  disabled: boolean;
  busyWatchlistKey: string | null;
  onNameChange: (value: string) => void;
  onTickerChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
  onTermsChange: (value: string) => void;
  onSelect: (companyKey: string) => void;
  onUpdate: (
    companyKey: string,
    payload: Partial<Pick<CompanyWatchlistItem, "priority" | "is_pinned" | "include_in_digest">>,
  ) => void;
  onDelete: (companyKey: string) => void;
  onSubmit: () => void;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Company Watchlist</h2>
        <span className="small-muted">{companies.length} companies</span>
      </div>
      <div className="form-panel compact-form">
        <input
          className="field"
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
          placeholder="Company"
          aria-label="Company name"
        />
        <input
          className="field"
          value={ticker}
          onChange={(event) => onTickerChange(event.target.value)}
          placeholder="Ticker"
          aria-label="Company ticker"
        />
        <select
          className="field"
          value={category}
          onChange={(event) => onCategoryChange(event.target.value)}
          aria-label="Company category"
        >
          <option value="ai_company">AI company</option>
          <option value="semiconductor">Semiconductor</option>
          <option value="cloud_ai">Cloud AI</option>
          <option value="ai_platform">AI platform</option>
          <option value="ai_lab">AI lab</option>
        </select>
        <input
          className="field"
          value={terms}
          onChange={(event) => onTermsChange(event.target.value)}
          placeholder="Terms"
          aria-label="Company related terms"
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
              <th>Company</th>
              <th>Category</th>
              <th>Priority</th>
              <th>Terms</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {companies.map((company) => {
              const busy = busyWatchlistKey === `company:${company.company_key}`;
              return (
                <tr key={company.company_key}>
                  <td>
                    <button
                      className={`ticker-button ${
                        selectedCompanyKey === company.company_key ? "active" : ""
                      }`}
                      onClick={() => onSelect(company.company_key)}
                      type="button"
                    >
                      {company.company_name}
                    </button>
                    {company.is_pinned ? <Star size={13} fill="currentColor" /> : null}
                    <div className="small-muted">{company.ticker ?? company.company_key}</div>
                  </td>
                  <td>{company.category}</td>
                  <td>
                    <select
                      className={`field table-field priority-${company.priority.toLowerCase()}`}
                      value={company.priority}
                      onChange={(event) =>
                        onUpdate(company.company_key, { priority: event.target.value })
                      }
                      disabled={disabled || busy}
                      aria-label={`Priority for ${company.company_name}`}
                    >
                      <option value="High">High</option>
                      <option value="Medium">Medium</option>
                      <option value="Low">Low</option>
                    </select>
                  </td>
                  <td>{company.related_terms.slice(0, 3).join(", ")}</td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="button icon-button"
                        onClick={() =>
                          onUpdate(company.company_key, { is_pinned: !company.is_pinned })
                        }
                        disabled={disabled || busy}
                        title={
                          company.is_pinned
                            ? `Unpin ${company.company_name}`
                            : `Pin ${company.company_name}`
                        }
                        aria-label={
                          company.is_pinned
                            ? `Unpin ${company.company_name}`
                            : `Pin ${company.company_name}`
                        }
                      >
                        {busy ? (
                          <Loader2 className="spin" size={16} />
                        ) : (
                          <Star size={16} fill={company.is_pinned ? "currentColor" : "none"} />
                        )}
                      </button>
                      <button
                        className={`button icon-button ${
                          company.include_in_digest ? "active-icon-button" : ""
                        }`}
                        onClick={() =>
                          onUpdate(company.company_key, {
                            include_in_digest: !company.include_in_digest,
                          })
                        }
                        disabled={disabled || busy}
                        title={
                          company.include_in_digest
                            ? `Exclude ${company.company_name} from digest`
                            : `Include ${company.company_name} in digest`
                        }
                        aria-label={
                          company.include_in_digest
                            ? `Exclude ${company.company_name} from digest`
                            : `Include ${company.company_name} in digest`
                        }
                      >
                        {busy ? <Loader2 className="spin" size={16} /> : <CalendarDays size={16} />}
                      </button>
                      <button
                        className="button icon-button"
                        onClick={() => onDelete(company.company_key)}
                        disabled={disabled || busy}
                        title={`Remove ${company.company_name}`}
                        aria-label={`Remove ${company.company_name}`}
                      >
                        {busy ? <Loader2 className="spin" size={16} /> : <Trash2 size={16} />}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <CompanyBriefingPanel
        briefing={briefing}
        loading={busyCompanyBriefing === selectedCompanyKey && selectedCompanyKey !== null}
        selectedCompanyKey={selectedCompanyKey}
      />
    </section>
  );
}

function CompanyBriefingPanel({
  briefing,
  loading,
  selectedCompanyKey,
}: {
  briefing: CompanyBriefing | null;
  loading: boolean;
  selectedCompanyKey: string | null;
}) {
  if (!selectedCompanyKey) {
    return <div className="empty-state">Select a company to inspect related signals.</div>;
  }

  if (loading && !briefing) {
    return (
      <div className="topic-briefing">
        <Loader2 className="spin" size={16} />
        <span className="small-muted">Loading company briefing...</span>
      </div>
    );
  }

  if (!briefing || briefing.company.company_key !== selectedCompanyKey) {
    return <div className="empty-state">No company briefing available for {selectedCompanyKey}.</div>;
  }

  return (
    <div className="topic-briefing">
      <div className="readiness-head">
        <div>
          <div className="digest-section-title">{briefing.company.category}</div>
          <div className="digest-headline">{briefing.company.company_name}</div>
          <div className="small-muted">
            {briefing.company.notes ?? "Company watchlist signal view"}
          </div>
        </div>
        <span className="badge">{briefing.item_count} items</span>
      </div>

      <div className="badges">
        {briefing.company.ticker ? <span className="badge">{briefing.company.ticker}</span> : null}
        {briefing.company.related_terms.map((term) => (
          <span className="badge" key={term}>
            {term}
          </span>
        ))}
      </div>

      <div className="topic-briefing-grid">
        <TopicBriefingList
          title="Trending Sources"
          emptyText="No source activity yet."
          items={briefing.trending_sources.map(
            (source) => `${source.source_name} (${source.item_count})`,
          )}
        />
        <TopicBriefingList
          title="Related Topics"
          emptyText="No related topics yet."
          items={briefing.related_topics}
        />
        <TopicBriefingList
          title="Related Products"
          emptyText="No related products yet."
          items={briefing.related_products}
        />
        <TopicBriefingList
          title="Related Tickers"
          emptyText="No related tickers yet."
          items={briefing.related_tickers}
        />
      </div>

      <div className="topic-activity-row">
        {briefing.activity_timeline.length ? (
          briefing.activity_timeline.map((bucket) => (
            <span className="badge" key={bucket.activity_date}>
              {bucket.activity_date}: {bucket.item_count}
            </span>
          ))
        ) : (
          <span className="small-muted">No dated activity yet.</span>
        )}
      </div>

      <div className="stock-timeline">
        {briefing.recent_timeline.length ? (
          briefing.recent_timeline.map((item) => (
            <a className="timeline-row" href={item.url} target="_blank" rel="noreferrer" key={item.id}>
              <div>
                <div className="timeline-title">{item.title}</div>
                <div className="small-muted">
                  {item.source_name}
                  {item.published_at ? ` · ${formatDate(item.published_at)}` : ""}
                </div>
              </div>
              <div className="timeline-score">{Math.round(item.importance_score * 100)}</div>
            </a>
          ))
        ) : (
          <div className="empty-state">No company-linked signals yet.</div>
        )}
      </div>
    </div>
  );
}

function TopicTable({
  topics,
  topicBriefing,
  selectedTopic,
  busyTopicBriefing,
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
  onSelectTopic,
  onUpdateTopic,
  onDeleteTopic,
  onSubmit,
}: {
  topics: TopicWatchlistItem[];
  topicBriefing: TopicBriefing | null;
  selectedTopic: string | null;
  busyTopicBriefing: string | null;
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
  onSelectTopic: (topic: string) => void;
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
                    <button
                      className={`ticker-button ${selectedTopic === topic.topic ? "active" : ""}`}
                      onClick={() => onSelectTopic(topic.topic)}
                      type="button"
                    >
                      {topic.label}
                    </button>
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
      <TopicBriefingPanel
        briefing={topicBriefing}
        loading={busyTopicBriefing === selectedTopic && selectedTopic !== null}
        selectedTopic={selectedTopic}
      />
    </section>
  );
}

function TopicBriefingPanel({
  briefing,
  loading,
  selectedTopic,
}: {
  briefing: TopicBriefing | null;
  loading: boolean;
  selectedTopic: string | null;
}) {
  if (!selectedTopic) {
    return <div className="empty-state">Select a topic to inspect related signals.</div>;
  }

  if (loading && !briefing) {
    return (
      <div className="topic-briefing">
        <Loader2 className="spin" size={16} />
        <span className="small-muted">Loading topic briefing...</span>
      </div>
    );
  }

  if (!briefing || briefing.topic.topic !== selectedTopic) {
    return <div className="empty-state">No topic briefing available for {selectedTopic}.</div>;
  }

  return (
    <div className="topic-briefing">
      <div className="readiness-head">
        <div>
          <div className="digest-section-title">{briefing.topic.category}</div>
          <div className="digest-headline">{briefing.topic.label}</div>
          <div className="small-muted">{briefing.topic.notes ?? "Topic watchlist signal view"}</div>
        </div>
        <span className="badge">{briefing.item_count} items</span>
      </div>

      <div className="badges">
        {briefing.topic.related_terms.map((term) => (
          <span className="badge" key={term}>
            {term}
          </span>
        ))}
      </div>

      <div className="topic-briefing-grid">
        <TopicBriefingList
          title="Trending Sources"
          emptyText="No source activity yet."
          items={briefing.trending_sources.map(
            (source) => `${source.source_name} (${source.item_count})`,
          )}
        />
        <TopicBriefingList
          title="Related Companies"
          emptyText="No related companies yet."
          items={briefing.related_companies}
        />
        <TopicBriefingLinks
          title="Related Papers"
          emptyText="No related papers yet."
          items={briefing.related_papers}
        />
        <TopicBriefingLinks
          title="Related Products"
          emptyText="No related products yet."
          items={briefing.related_products}
        />
      </div>

      <div className="topic-activity-row">
        {briefing.activity_timeline.length ? (
          briefing.activity_timeline.map((bucket) => (
            <span className="badge" key={bucket.activity_date}>
              {bucket.activity_date}: {bucket.item_count}
            </span>
          ))
        ) : (
          <span className="small-muted">No dated activity yet.</span>
        )}
      </div>

      <div className="stock-timeline">
        {briefing.recent_timeline.length ? (
          briefing.recent_timeline.map((item) => (
            <a className="timeline-row" href={item.url} target="_blank" rel="noreferrer" key={item.id}>
              <div>
                <div className="timeline-title">{item.title}</div>
                <div className="small-muted">
                  {item.source_name}
                  {item.published_at ? ` · ${formatDate(item.published_at)}` : ""}
                </div>
              </div>
              <div className="timeline-score">{Math.round(item.importance_score * 100)}</div>
            </a>
          ))
        ) : (
          <div className="empty-state">No topic-linked signals yet.</div>
        )}
      </div>
    </div>
  );
}

function TopicBriefingList({
  title,
  emptyText,
  items,
}: {
  title: string;
  emptyText: string;
  items: string[];
}) {
  return (
    <div className="digest-section">
      <div className="digest-section-title">{title}</div>
      {items.length ? (
        <div className="badges">
          {items.slice(0, 8).map((item) => (
            <span className="badge" key={item}>
              {item}
            </span>
          ))}
        </div>
      ) : (
        <div className="small-muted">{emptyText}</div>
      )}
    </div>
  );
}

function TopicBriefingLinks({
  title,
  emptyText,
  items,
}: {
  title: string;
  emptyText: string;
  items: FeedItem[];
}) {
  return (
    <div className="digest-section">
      <div className="digest-section-title">{title}</div>
      {items.length ? (
        <div className="digest-list">
          {items.slice(0, 5).map((item) => (
            <a className="digest-link" href={item.url} target="_blank" rel="noreferrer" key={item.id}>
              {item.title}
            </a>
          ))}
        </div>
      ) : (
        <div className="small-muted">{emptyText}</div>
      )}
    </div>
  );
}

function ProductWatchlistPanel({
  items,
  briefing,
  selectedCategory,
  busyProductBriefing,
  category,
  label,
  terms,
  disabled,
  busyWatchlistKey,
  onCategoryChange,
  onLabelChange,
  onTermsChange,
  onSelect,
  onUpdate,
  onDelete,
  onSubmit,
}: {
  items: ProductWatchlistItem[];
  briefing: ProductBriefing | null;
  selectedCategory: string | null;
  busyProductBriefing: string | null;
  category: string;
  label: string;
  terms: string;
  disabled: boolean;
  busyWatchlistKey: string | null;
  onCategoryChange: (value: string) => void;
  onLabelChange: (value: string) => void;
  onTermsChange: (value: string) => void;
  onSelect: (category: string) => void;
  onUpdate: (
    category: string,
    payload: Partial<Pick<ProductWatchlistItem, "priority" | "is_pinned" | "include_in_digest">>,
  ) => void;
  onDelete: (category: string) => void;
  onSubmit: () => void;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Product Categories</h2>
        <span className="small-muted">{items.length} categories</span>
      </div>
      <div className="form-panel compact-form">
        <input
          className="field"
          value={category}
          onChange={(event) => onCategoryChange(event.target.value)}
          placeholder="Category"
          aria-label="Product category"
        />
        <input
          className="field"
          value={label}
          onChange={(event) => onLabelChange(event.target.value)}
          placeholder="Label"
          aria-label="Product category label"
        />
        <input
          className="field"
          value={terms}
          onChange={(event) => onTermsChange(event.target.value)}
          placeholder="Terms"
          aria-label="Product category terms"
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
              <th>Category</th>
              <th>Priority</th>
              <th>Terms</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const busy = busyWatchlistKey === `product:${item.category}`;
              return (
                <tr key={item.category}>
                  <td>
                    <button
                      className={`ticker-button ${
                        selectedCategory === item.category ? "active" : ""
                      }`}
                      onClick={() => onSelect(item.category)}
                      type="button"
                    >
                      {item.label}
                    </button>
                    {item.is_pinned ? <Star size={13} fill="currentColor" /> : null}
                  </td>
                  <td>
                    <select
                      className={`field table-field priority-${item.priority.toLowerCase()}`}
                      value={item.priority}
                      onChange={(event) =>
                        onUpdate(item.category, { priority: event.target.value })
                      }
                      disabled={disabled || busy}
                      aria-label={`Priority for ${item.label}`}
                    >
                      <option value="High">High</option>
                      <option value="Medium">Medium</option>
                      <option value="Low">Low</option>
                    </select>
                  </td>
                  <td>{item.related_terms.slice(0, 3).join(", ")}</td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="button icon-button"
                        onClick={() => onUpdate(item.category, { is_pinned: !item.is_pinned })}
                        disabled={disabled || busy}
                        title={item.is_pinned ? `Unpin ${item.label}` : `Pin ${item.label}`}
                        aria-label={item.is_pinned ? `Unpin ${item.label}` : `Pin ${item.label}`}
                      >
                        {busy ? (
                          <Loader2 className="spin" size={16} />
                        ) : (
                          <Star size={16} fill={item.is_pinned ? "currentColor" : "none"} />
                        )}
                      </button>
                      <button
                        className={`button icon-button ${
                          item.include_in_digest ? "active-icon-button" : ""
                        }`}
                        onClick={() =>
                          onUpdate(item.category, {
                            include_in_digest: !item.include_in_digest,
                          })
                        }
                        disabled={disabled || busy}
                        title={
                          item.include_in_digest
                            ? `Exclude ${item.label} from digest`
                            : `Include ${item.label} in digest`
                        }
                        aria-label={
                          item.include_in_digest
                            ? `Exclude ${item.label} from digest`
                            : `Include ${item.label} in digest`
                        }
                      >
                        {busy ? <Loader2 className="spin" size={16} /> : <CalendarDays size={16} />}
                      </button>
                      <button
                        className="button icon-button"
                        onClick={() => onDelete(item.category)}
                        disabled={disabled || busy}
                        title={`Remove ${item.label}`}
                        aria-label={`Remove ${item.label}`}
                      >
                        {busy ? <Loader2 className="spin" size={16} /> : <Trash2 size={16} />}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <ProductBriefingPanel
        briefing={briefing}
        loading={busyProductBriefing === selectedCategory && selectedCategory !== null}
        selectedCategory={selectedCategory}
      />
    </section>
  );
}

function ProductBriefingPanel({
  briefing,
  loading,
  selectedCategory,
}: {
  briefing: ProductBriefing | null;
  loading: boolean;
  selectedCategory: string | null;
}) {
  if (!selectedCategory) {
    return <div className="empty-state">Select a product category to inspect launches.</div>;
  }

  if (loading && !briefing) {
    return (
      <div className="topic-briefing">
        <Loader2 className="spin" size={16} />
        <span className="small-muted">Loading product briefing...</span>
      </div>
    );
  }

  if (!briefing || briefing.product.category !== selectedCategory) {
    return <div className="empty-state">No product briefing available for {selectedCategory}.</div>;
  }

  return (
    <div className="topic-briefing">
      <div className="readiness-head">
        <div>
          <div className="digest-section-title">{briefing.product.category}</div>
          <div className="digest-headline">{briefing.product.label}</div>
          <div className="small-muted">
            {briefing.product.notes ?? "Product category signal view"}
          </div>
        </div>
        <span className="badge">{briefing.item_count} items</span>
      </div>

      <div className="badges">
        {briefing.product.related_terms.map((term) => (
          <span className="badge" key={term}>
            {term}
          </span>
        ))}
      </div>

      <div className="topic-briefing-grid">
        <TopicBriefingList
          title="Trending Sources"
          emptyText="No source activity yet."
          items={briefing.trending_sources.map(
            (source) => `${source.source_name} (${source.item_count})`,
          )}
        />
        <TopicBriefingList
          title="Matched Products"
          emptyText="No matched products yet."
          items={briefing.matched_products}
        />
        <TopicBriefingList
          title="Related Companies"
          emptyText="No related companies yet."
          items={briefing.related_companies}
        />
        <TopicBriefingList
          title="Activity"
          emptyText="No dated activity yet."
          items={briefing.activity_timeline.map(
            (bucket) => `${bucket.activity_date}: ${bucket.item_count}`,
          )}
        />
      </div>

      <div className="stock-timeline">
        {briefing.recent_timeline.length ? (
          briefing.recent_timeline.map((item) => (
            <a className="timeline-row" href={item.url} target="_blank" rel="noreferrer" key={item.id}>
              <div>
                <div className="timeline-title">{item.title}</div>
                <div className="small-muted">
                  {item.source_name}
                  {item.published_at ? ` · ${formatDate(item.published_at)}` : ""}
                </div>
              </div>
              <div className="timeline-score">{Math.round(item.importance_score * 100)}</div>
            </a>
          ))
        ) : (
          <div className="empty-state">No product-category signals yet.</div>
        )}
      </div>
    </div>
  );
}

function SourceTable({
  sources,
  runs,
  lastCycleResult,
  name,
  type,
  accessMethod,
  baseUrl,
  termsNotes,
  disabled,
  busySourceId,
  onNameChange,
  onTypeChange,
  onAccessMethodChange,
  onBaseUrlChange,
  onTermsNotesChange,
  onSubmit,
  onRunSource,
  onToggleSource,
  onUpdateSource,
}: {
  sources: SourceHealth[];
  runs: SourceRunHistoryItem[];
  lastCycleResult: ScheduledCycleResponse | null;
  name: string;
  type: string;
  accessMethod: string;
  baseUrl: string;
  termsNotes: string;
  disabled: boolean;
  busySourceId: number | null;
  onNameChange: (value: string) => void;
  onTypeChange: (value: string) => void;
  onAccessMethodChange: (value: string) => void;
  onBaseUrlChange: (value: string) => void;
  onTermsNotesChange: (value: string) => void;
  onSubmit: () => void;
  onRunSource: (source: SourceHealth) => void;
  onToggleSource: (source: SourceHealth) => void;
  onUpdateSource: (source: SourceHealth, payload: SourceUpdatePayload) => void;
}) {
  const [drafts, setDrafts] = useState<Record<number, SourceDraft>>({});

  useEffect(() => {
    setDrafts(Object.fromEntries(sources.map((source) => [source.id, buildSourceDraft(source)])));
  }, [sources]);

  const setDraftValue = (sourceId: number, field: keyof SourceDraft, value: string) => {
    setDrafts((current) => ({
      ...current,
      [sourceId]: {
        ...(current[sourceId] ?? buildSourceDraft(sources.find((source) => source.id === sourceId)!)),
        [field]: value,
      },
    }));
  };
  const cycleFetched = lastCycleResult?.ingestion_results.reduce(
    (total, item) => total + item.items_fetched,
    0,
  );
  const cycleStored = lastCycleResult?.ingestion_results.reduce(
    (total, item) => total + item.items_stored,
    0,
  );

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Source Health</h2>
        <DatabaseZap size={16} aria-hidden="true" />
      </div>
      <div className="form-panel compact-form">
        <input
          className="field"
          placeholder="Source name"
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
          disabled={disabled}
        />
        <select
          className="field"
          value={type}
          onChange={(event) => onTypeChange(event.target.value)}
          disabled={disabled}
          aria-label="Source type"
        >
          <option value="blog">Blog</option>
          <option value="company">Company</option>
          <option value="github_repository">GitHub repository</option>
          <option value="product_topic">Product topic</option>
          <option value="social_keyword">Social keyword</option>
          <option value="rss">RSS</option>
        </select>
        <select
          className="field"
          value={accessMethod}
          onChange={(event) => onAccessMethodChange(event.target.value)}
          disabled={disabled}
          aria-label="Access method"
        >
          <option value="rss">RSS</option>
          <option value="official_api">Official API</option>
          <option value="manual_watch">Manual watch</option>
        </select>
        <input
          className="field"
          placeholder="URL or feed"
          value={baseUrl}
          onChange={(event) => onBaseUrlChange(event.target.value)}
          disabled={disabled}
        />
        <input
          className="field"
          placeholder="Terms or scope notes"
          value={termsNotes}
          onChange={(event) => onTermsNotesChange(event.target.value)}
          disabled={disabled}
        />
        <button className="button primary" onClick={onSubmit} disabled={disabled}>
          {disabled ? <Loader2 className="spin" size={16} /> : <Plus size={16} />}
          Follow
        </button>
      </div>
      <div className="table-wrap">
        <table className="source-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Enabled</th>
              <th>Priority</th>
              <th>Polling</th>
              <th>Rate Limit</th>
              <th>Terms Notes</th>
              <th>Status</th>
              <th>Stored</th>
              <th>Last Run</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => {
              const draft = drafts[source.id] ?? buildSourceDraft(source);
              const changed = isSourceDraftChanged(source, draft);
              const saving = busySourceId === source.id;
              const failureCopy = `${source.failure_count} recent ${
                source.failure_count === 1 ? "failure" : "failures"
              }`;
              return (
                <tr key={source.id}>
                  <td>
                    <div className="table-event-cell">{source.name}</div>
                    <div className="small-muted">
                      {source.type} · {source.access_method}
                      {source.auth_required ? " · key required" : ""}
                    </div>
                  </td>
                  <td>{source.enabled ? "Yes" : "No"}</td>
                  <td>
                    <input
                      className="field table-field source-priority-field"
                      min="0"
                      type="number"
                      value={draft.priority}
                      onChange={(event) => setDraftValue(source.id, "priority", event.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      className="field table-field source-short-field"
                      value={draft.polling_interval}
                      onChange={(event) =>
                        setDraftValue(source.id, "polling_interval", event.target.value)
                      }
                      placeholder="hourly"
                    />
                  </td>
                  <td>
                    <input
                      className="field table-field source-short-field"
                      value={draft.rate_limit}
                      onChange={(event) => setDraftValue(source.id, "rate_limit", event.target.value)}
                      placeholder="60/hour"
                    />
                  </td>
                  <td>
                    <input
                      className="field table-field source-notes-field"
                      value={draft.terms_notes}
                      onChange={(event) => setDraftValue(source.id, "terms_notes", event.target.value)}
                      placeholder="Usage notes"
                    />
                  </td>
                  <td className={source.latest_status === "success" ? "health-ok" : ""}>
                    <div>{source.latest_status}</div>
                    {source.needs_attention ? (
                      <div className="small-muted source-attention">
                        needs attention{source.failure_count > 0 ? ` · ${failureCopy}` : ""}
                      </div>
                    ) : source.failure_count > 0 ? (
                      <div className="small-muted">{failureCopy}</div>
                    ) : null}
                  </td>
                  <td>{source.items_stored}</td>
                  <td>
                    <div>{source.last_finished_at ? formatDate(source.last_finished_at) : "never"}</div>
                    {source.last_success_at ? (
                      <div className="small-muted">success {formatDate(source.last_success_at)}</div>
                    ) : null}
                  </td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="button icon-button"
                        onClick={() => onRunSource(source)}
                        disabled={disabled || saving}
                        title="Run source now"
                        type="button"
                      >
                        {saving ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
                      </button>
                      <button
                        className="button icon-button"
                        onClick={() => onToggleSource(source)}
                        disabled={disabled || saving}
                        title={source.enabled ? "Disable source" : "Enable source"}
                        type="button"
                      >
                        {saving ? <Loader2 className="spin" size={16} /> : <DatabaseZap size={16} />}
                      </button>
                      <button
                        className="button icon-button"
                        onClick={() => onUpdateSource(source, buildSourcePayload(draft))}
                        disabled={disabled || saving || !changed}
                        title="Save source settings"
                        type="button"
                      >
                        {saving ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {lastCycleResult ? (
        <div className="cycle-summary">
          <div>
            <div className="digest-section-title">Last full cycle</div>
            <div className="small-muted">
              {formatDate(lastCycleResult.started_at)} to {formatDate(lastCycleResult.finished_at)}
            </div>
          </div>
          <div className="cycle-metrics">
            <span className="badge">{cycleFetched ?? 0} fetched</span>
            <span className="badge">{cycleStored ?? 0} stored</span>
            <span className="badge">{lastCycleResult.generated_alert_count} alerts</span>
            <span className="badge">{lastCycleResult.seeded_stock_count} stocks</span>
            <span className="badge">{lastCycleResult.seeded_company_count} companies</span>
            <span className="badge">{lastCycleResult.seeded_topic_count} topics</span>
            <span className="badge">{lastCycleResult.seeded_product_count} products</span>
            <span className="badge">
              Digest {lastCycleResult.saved_digest_date ?? "not saved"}
            </span>
          </div>
          <div className="cycle-source-list">
            {lastCycleResult.ingestion_results.map((result) => (
              <span
                className={`badge ${result.status === "success" ? "" : "muted-badge"}`}
                key={result.source_name}
                title={result.error_message ?? undefined}
              >
                {result.source_name}: {result.status}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      <div className="source-run-list">
        {runs.length ? (
          runs.map((run) => (
            <div className="source-run-row" key={run.id}>
              <div>
                <div className="digest-link">{run.source_name}</div>
                <div className="small-muted">
                  {formatDate(run.started_at)} · fetched {run.items_fetched} · stored{" "}
                  {run.items_stored}
                  {run.error_message ? ` · ${run.error_message}` : ""}
                </div>
              </div>
              <span className={`badge ${run.status === "success" ? "" : "muted-badge"}`}>
                {run.status}
              </span>
            </div>
          ))
        ) : (
          <div className="empty-state">No source runs recorded yet.</div>
        )}
      </div>
    </section>
  );
}

function buildSourceDraft(source: SourceHealth): SourceDraft {
  return {
    priority: String(source.priority),
    polling_interval: source.polling_interval ?? "",
    rate_limit: source.rate_limit ?? "",
    terms_notes: source.terms_notes ?? "",
  };
}

function buildSourcePayload(draft: SourceDraft): SourceUpdatePayload {
  const priority = Number(draft.priority);

  return {
    priority: Number.isFinite(priority) && priority >= 0 ? priority : 100,
    polling_interval: draft.polling_interval.trim() || null,
    rate_limit: draft.rate_limit.trim() || null,
    terms_notes: draft.terms_notes.trim() || null,
  };
}

function isSourceDraftChanged(source: SourceHealth, draft: SourceDraft): boolean {
  return (
    String(source.priority) !== draft.priority.trim() ||
    (source.polling_interval ?? "") !== draft.polling_interval.trim() ||
    (source.rate_limit ?? "") !== draft.rate_limit.trim() ||
    (source.terms_notes ?? "") !== draft.terms_notes.trim()
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

function buildModuleCounts(
  feed: FeedItem[],
  digest: DailyDigest | null,
  savedItems: FeedItem[],
): Record<ModuleKey, number> {
  return {
    dashboard: feed.length,
    trends: feed.filter((item) => itemMatchesModule(item, "trends")).length,
    research: feed.filter((item) => itemMatchesModule(item, "research")).length,
    products: feed.filter((item) => itemMatchesModule(item, "products")).length,
    stocks: feed.filter((item) => itemMatchesModule(item, "stocks")).length,
    chinese: feed.filter((item) => itemMatchesModule(item, "chinese")).length,
    saved: savedItems.length,
    digest: collectDigestFeedItems(digest).length,
  };
}

function filterFeedByModule(
  feed: FeedItem[],
  moduleKey: ModuleKey,
  digest: DailyDigest | null,
  savedItems: FeedItem[],
): FeedItem[] {
  if (moduleKey === "dashboard") {
    return feed;
  }
  if (moduleKey === "saved") {
    return savedItems;
  }
  if (moduleKey === "digest") {
    return collectDigestFeedItems(digest);
  }
  return feed.filter((item) => itemMatchesModule(item, moduleKey));
}

function itemMatchesModule(item: FeedItem, moduleKey: ModuleKey): boolean {
  if (moduleKey === "trends") {
    return item.category === "technical_trend";
  }
  if (moduleKey === "research") {
    return item.category === "research";
  }
  if (moduleKey === "products") {
    return item.category === "product" || item.products.length > 0;
  }
  if (moduleKey === "stocks") {
    return item.category === "stock_company_event" || item.tickers.length > 0;
  }
  if (moduleKey === "chinese") {
    return item.category === "social_trend" || item.language === "zh";
  }
  return false;
}

function collectDigestFeedItems(digest: DailyDigest | null): FeedItem[] {
  const byId = new Map<number, FeedItem>();
  digest?.sections.forEach((section) => {
    section.items.forEach((item) => byId.set(item.id, item));
  });
  return [...byId.values()];
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatCategoryLabel(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function splitTerms(value: string) {
  return value
    .split(",")
    .map((term) => term.trim())
    .filter(Boolean);
}

function buildSearchIntentChips(intent: SearchIntent | null): string[] {
  if (!intent) {
    return [];
  }

  const chips = [
    intent.query ? `query: ${intent.query}` : null,
    intent.category ? `category: ${intent.category}` : null,
    intent.ticker ? `ticker: ${intent.ticker}` : null,
    intent.company ? `company: ${intent.company}` : null,
    intent.topic ? `topic: ${intent.topic}` : null,
    intent.language ? `language: ${intent.language}` : null,
    intent.date_from ? `from: ${intent.date_from}` : null,
    intent.min_importance_score !== null ? `importance: ${intent.min_importance_score}` : null,
    intent.saved_only ? "saved" : null,
  ];

  return chips.filter(Boolean) as string[];
}

function stockToDetailDraft(stock: StockWatchlistItem | null): StockDetailDraft {
  return {
    exchange: stock?.exchange ?? "",
    sector: stock?.sector ?? "",
    industry: stock?.industry ?? "",
    group_name: stock?.group_name ?? "",
    is_holding: stock?.is_holding ?? false,
    shares: stock?.shares === null || stock?.shares === undefined ? "" : String(stock.shares),
    average_cost:
      stock?.average_cost === null || stock?.average_cost === undefined
        ? ""
        : String(stock.average_cost),
    notes: stock?.notes ?? "",
  };
}

function hasPortfolioDetails(stock: StockWatchlistItem | null): boolean {
  if (!stock) {
    return false;
  }
  return Boolean(stock?.is_holding || stock?.shares !== null || stock?.average_cost !== null);
}

function parseOptionalNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "--";
  }
  return `$${value.toFixed(2)}`;
}

function formatChange(market: StockMarketSnapshot | null | undefined): string {
  if (!market || market.change === null || market.change_percent === null) {
    return "--";
  }
  const sign = market.change > 0 ? "+" : "";
  return `${sign}${market.change.toFixed(2)} (${sign}${market.change_percent.toFixed(2)}%)`;
}

function formatDominantSentiment(counts: Record<string, number> | null | undefined): string {
  if (!counts) {
    return "--";
  }
  const [sentiment, count] =
    Object.entries(counts).sort((left, right) => right[1] - left[1])[0] ?? [];
  if (!sentiment || !count) {
    return "--";
  }
  return `${sentiment} ${count}`;
}

function marketChangeClass(value: number | null): string {
  if (value === null || value === 0) {
    return "";
  }
  return value > 0 ? "market-up" : "market-down";
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
