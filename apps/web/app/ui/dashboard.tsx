"use client";

import {
  Activity,
  BarChart3,
  BellRing,
  Bookmark,
  Bot,
  CalendarDays,
  ChevronDown,
  ChevronUp,
  CircleCheck,
  DatabaseZap,
  Download,
  EyeOff,
  ExternalLink,
  FileText,
  Flag,
  FlaskConical,
  Github,
  History,
  Loader2,
  Mail,
  Newspaper,
  Plus,
  RefreshCw,
  Rocket,
  Save,
  Search,
  Send,
  SlidersHorizontal,
  Star,
  ThumbsDown,
  ThumbsUp,
  TrendingUp,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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
  technologies: string[];
  sentiment: string;
  is_ai_related: boolean;
  relevance_score: number;
  classification_confidence: number;
  importance_score: number;
  novelty_score: number;
  source_quality_score: number;
  social_signal_score: number;
  stock_impact_score: number;
  market_impact_type: string;
  summary_short: string | null;
  summary_detailed: string | null;
  why_it_matters: string | null;
  is_saved: boolean;
  is_hidden: boolean;
  is_important: boolean;
  is_read: boolean;
  read_at: string | null;
  personal_note: string | null;
  manual_tags: string[];
  usefulness_feedback: "useful" | "not_useful" | null;
  usefulness_feedback_at: string | null;
};

type FeedItemDetail = FeedItem & {
  text: string | null;
  one_line_summary: string | null;
  card_summary: string[];
  technical_summary: string | null;
  market_watch_summary: string | null;
  public_engagement: PublicEngagementMetric[];
  stock_reaction_summary: {
    ticker: string;
    possible_market_impact: string;
    price_reaction: string;
    event_price_date: string | null;
    event_price_change_percent: number | null;
    summary: string;
  } | null;
  summary_source: string;
  score_explanation: string;
  uncertainty_notes: string[];
  personalization_notes: string[];
  action_state: Record<string, boolean>;
};

type PublicEngagementMetric = {
  key: string;
  label: string;
  value: number;
};

type ManualSubmissionResponse = {
  item: FeedItem;
  created: boolean;
  updated_existing: boolean;
  classification_status: "not_requested" | "succeeded" | "failed";
  classification_error: string | null;
  summary_status: "not_requested" | "succeeded" | "failed";
  summary_error: string | null;
};

type ManualEngagementDraft = {
  likes: string;
  comments_count: string;
  collects: string;
  reposts: string;
  views: string;
};

type ResearchInsights = {
  contribution?: string;
  method?: string;
  relevance?: string;
};

type StockWatchlistItem = {
  ticker: string;
  company_name: string;
  exchange: string;
  sector: string;
  industry: string;
  market_cap_usd: number | null;
  priority: string;
  group_name: string;
  display_order: number;
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
  company_name: string;
  exchange: string;
  sector: string;
  industry: string;
  market_cap_usd: string;
  group_name: string;
  related_keywords: string;
  related_companies: string;
  related_ai_themes: string;
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
  volume_change_percent: number | null;
  history: StockPricePoint[];
};

type StockPriceRangeKey = "1d" | "5d" | "1m" | "6m" | "1y";
type StockSortMode = "attention" | "watchlist";
type StockDetailTabKey = "overview" | "signals" | "clusters" | "notes" | "summary";

type StockAttentionComponent = {
  key: string;
  label: string;
  value: number;
  weight: number;
  contribution: number;
};

type StockSignalSummary = {
  stock: StockWatchlistItem;
  signal_count: number;
  today_signal_count: number;
  high_impact_count: number;
  attention_score: number;
  attention_reasons: string[];
  attention_components: StockAttentionComponent[];
  market: StockMarketSnapshot | null;
  latest_event_title: string | null;
  latest_event_at: string | null;
  last_updated_at: string | null;
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
  price_reaction: string;
  event_price_date: string | null;
  event_price_change_percent: number | null;
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
  today_signal_count: number;
  high_impact_count: number;
  attention_score: number;
  attention_reasons: string[];
  attention_components: StockAttentionComponent[];
  market: StockMarketSnapshot | null;
  urgency: string;
  latest_signal_at: string | null;
  last_updated_at: string | null;
  sentiment_counts: Record<string, number>;
  key_themes: string[];
  ai_relevance_summary: string;
  theme_breakdown: StockThemeBreakdown[];
  market_impact_events: StockMarketImpactEvent[];
  recent_timeline: StockBriefingTimelineItem[];
  disclaimer: string;
};

type StockBriefingLlmSummary = {
  ticker: string;
  model: string;
  summary: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
};

type StockLlmSummarySection = {
  heading: string;
  body: string[];
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

type CompanyDetailDraft = {
  company_name: string;
  ticker: string;
  category: string;
  related_terms: string;
  notes: string;
};

type CompanyBriefing = {
  company: CompanyWatchlistItem;
  item_count: number;
  high_impact_count: number;
  average_importance_score: number;
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

type TopicDetailDraft = {
  label: string;
  category: string;
  related_terms: string;
  notes: string;
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

type ProductDetailDraft = {
  label: string;
  related_terms: string;
  notes: string;
};

type ProductBriefing = {
  product: ProductWatchlistItem;
  item_count: number;
  high_impact_count: number;
  average_importance_score: number;
  average_novelty_score: number;
  trending_sources: TopicSourceCount[];
  use_case_counts: TopicSourceCount[];
  matched_products: string[];
  related_companies: string[];
  traction_signals: string[];
  discovery_scores: ProductDiscoveryScore[];
  recent_timeline: FeedItem[];
  activity_timeline: TopicActivityBucket[];
};

type ProductDiscoveryScore = {
  item_id: number;
  score: number;
  novelty_score: number;
  traction_score: number;
  importance_score: number;
  relevance_score: number;
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
  definition: string;
  item_count: number;
  high_impact_count: number;
  average_importance_score: number;
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
  raw_content_policy: string;
  failure_handling: string;
  latest_status: string;
  latest_error: string | null;
  last_started_at: string | null;
  last_finished_at: string | null;
  latest_duration_seconds: number | null;
  last_success_at: string | null;
  next_run_due_at: string | null;
  is_stale: boolean;
  items_fetched: number;
  items_stored: number;
  failure_count: number;
  needs_attention: boolean;
  recent_run_count: number;
  recent_success_rate: number | null;
  recent_store_rate: number | null;
  recent_items_fetched: number;
  recent_items_stored: number;
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
  duration_seconds: number | null;
};

type IngestionRunResponse = {
  source_name: string;
  status: string;
  items_fetched: number;
  items_stored: number;
  error_message: string | null;
  store_rate: number;
  needs_attention: boolean;
  recovery_hint: string | null;
};

type ScheduledCycleResponse = {
  started_at: string;
  finished_at: string;
  duration_seconds: number;
  seeded_stock_count: number;
  seeded_company_count: number;
  seeded_topic_count: number;
  seeded_product_count: number;
  generated_alert_count: number;
  saved_digest_date: string | null;
  digest_snapshot_status: string;
  digest_snapshot_message: string | null;
  successful_source_count: number;
  failed_source_count: number;
  skipped_source_count: number;
  ingestion_results: IngestionRunResponse[];
};

type ScheduledJobPlan = {
  name: string;
  limit: number | null;
  source_type: string;
  due: boolean;
};

type IngestionScheduleStatus = {
  mode: string;
  interval_minutes: number;
  digest_target_hour_utc: number;
  now: string;
  next_cycle_at: string | null;
  next_digest_target_at: string;
  latest_source_run_at: string | null;
  latest_source_run_status: string | null;
  latest_digest_snapshot_date: string | null;
  digest_snapshot_fresh: boolean;
  built_in_jobs: ScheduledJobPlan[];
  due_custom_sources: ScheduledJobPlan[];
  due_custom_source_count: number;
  command_hint: string;
};

type FeedProcessingResponse = {
  requested_limit: number;
  dry_run: boolean;
  candidates_seen: number;
  planned_model_calls: number;
  summarized_count: number;
  classified_count: number;
  skipped_count: number;
  model_call_budget: number;
  model_calls_attempted: number;
  model_calls_succeeded: number;
  model_calls_failed: number;
  model_calls_skipped: number;
  model_calls_unused: number;
  item_ids: number[];
  candidate_previews: {
    item_id: number;
    title: string;
    source_name: string;
    category: string | null;
    planned_operations: string[];
    skipped_operations: string[];
  }[];
  errors: { item_id: number; stage: string; error: string }[];
};

type SearchIntent = {
  query: string | null;
  source: string | null;
  category: string | null;
  subcategory: string | null;
  ticker: string | null;
  company: string | null;
  topic: string | null;
  manual_tag: string | null;
  language: string | null;
  date_from: string | null;
  date_to: string | null;
  min_importance_score: number | null;
  min_social_signal_score: number | null;
  ai_related: boolean | null;
  saved_only: boolean;
  read_status: "read" | "unread" | null;
};

type NaturalLanguageSearchResponse = {
  intent: SearchIntent;
  items: FeedItem[];
  summary: string | null;
};

type IntegrationStatus = {
  kimi_coding_api: boolean;
  github_api: boolean;
  product_hunt_api: boolean;
  alpha_vantage_api: boolean;
  sec_user_agent: boolean;
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

type SetupSummary = {
  total: number;
  configured: number;
  missing: number;
  core_missing: number;
  recommended_missing: number;
  optional_missing: number;
  core_ready: boolean;
};

type SystemStatus = {
  status: string;
  service: string;
  environment: string;
  llm_provider: string;
  llm_base_url: string;
  llm_model: string;
  llm_api_format: string;
  llm_configured: boolean;
  integrations: IntegrationStatus;
  setup_items: SetupItem[];
  setup_summary: SetupSummary;
  missing_env_template: string;
};

type QualityMetrics = {
  generated_at: string;
  window_days: number;
  total_item_count: number;
  recent_item_count: number;
  recent_module_counts: Record<string, number>;
  covered_module_count: number;
  recent_source_count: number;
  dominant_source_share: number;
  trusted_source_coverage: number;
  low_quality_item_count: number;
  search_facet_coverage: number;
  unfaceted_item_count: number;
  high_value_item_count: number;
  high_value_items_per_day: number;
  high_value_unsummarized_count: number;
  classification_coverage: number;
  low_confidence_item_count: number;
  relevance_precision_proxy: number;
  duplicate_rate: number;
  summary_coverage: number;
  summary_quality_proxy: number;
  thin_summary_count: number;
  source_failure_rate: number;
  save_count: number;
  hide_count: number;
  feedback_action_count: number;
  item_feedback_count: number;
  item_useful_feedback_count: number;
  item_not_useful_feedback_count: number;
  item_feedback_usefulness_rate: number | null;
  manual_submission_count: number;
  manual_enrichment_gap_count: number;
  stock_watchlist_count: number;
  company_watchlist_count: number;
  topic_watchlist_count: number;
  product_watchlist_count: number;
  watchlist_area_count: number;
  saved_read_count: number;
  saved_read_later_count: number;
  save_hide_ratio: number | null;
  active_alert_count: number;
  dismissed_alert_count: number;
  alert_dismissal_rate: number;
  alert_feedback_count: number;
  alert_useful_feedback_count: number;
  alert_not_useful_feedback_count: number;
  alert_feedback_usefulness_rate: number | null;
  alert_usefulness_proxy: number | null;
  digest_snapshot_count: number;
  digest_feedback_count: number;
  digest_useful_feedback_count: number;
  digest_not_useful_feedback_count: number;
  digest_feedback_usefulness_rate: number | null;
  digest_usefulness_proxy: number;
  latest_digest_snapshot_date: string | null;
  latest_digest_age_days: number | null;
  latest_digest_snapshot_item_count: number | null;
  latest_stock_price_date: string | null;
  latest_stock_price_age_days: number | null;
  llm_call_count: number;
  llm_input_tokens: number;
  llm_output_tokens: number;
  llm_total_tokens: number;
  llm_calls_per_recent_item: number;
  llm_pricing_configured: boolean;
  llm_estimated_cost_usd: number;
  llm_projected_monthly_cost_usd: number;
  llm_monthly_budget_usd: number;
  llm_monthly_budget_usage: number | null;
  llm_estimated_cost_per_recent_item_usd: number | null;
  llm_estimated_cost_per_digest_usd: number | null;
  llm_estimated_cost_per_active_alert_usd: number | null;
  llm_operation_usage: LlmOperationUsage[];
  source_api_call_count: number;
  source_api_calls_per_recent_item: number;
  source_api_pricing_configured: boolean;
  source_api_estimated_cost_usd: number;
  source_api_projected_monthly_cost_usd: number;
  source_api_monthly_budget_usd: number;
  source_api_monthly_budget_usage: number | null;
  source_api_estimated_cost_per_recent_item_usd: number | null;
  source_api_estimated_cost_per_digest_usd: number | null;
  source_api_estimated_cost_per_active_alert_usd: number | null;
  quality_findings: QualityFinding[];
};

type QualityFinding = {
  severity: "info" | "warning" | "critical";
  title: string;
  metric: string;
  recommendation: string;
  action_label: string | null;
  action_module: Extract<
    ModuleKey,
    "alerts" | "dashboard" | "digest" | "sources" | "settings" | "stocks" | "submit"
  > | null;
  action_operation: Extract<
    DashboardOperation,
    | "cycle"
    | "digest:save-snapshot"
    | "llm:preview"
    | "llm:classify"
    | "llm:summarize"
    | "stock-prices:refresh"
    | "alerts:generate"
    | "demo-data:seed"
  > | null;
  action_source_filter: SourceHealthFilter | null;
};

type MvpChecklistItem = {
  key: string;
  label: string;
  status: "ready" | "partial" | "needs_action";
  metric: string;
  note: string;
  actionLabel?: string;
  actionModule?: ModuleKey;
  actionOperation?: DashboardOperation;
  actionSourceFilter?: SourceHealthFilter;
  actionTargetId?: string;
};

type MvpChecklistApiItem = {
  key: string;
  label: string;
  status: "ready" | "partial" | "needs_action";
  metric: string;
  note: string;
  action_label: string | null;
  action_module: Extract<
    ModuleKey,
    "alerts" | "dashboard" | "digest" | "sources" | "settings" | "stocks" | "submit"
  > | null;
  action_operation: Extract<
    DashboardOperation,
    | "cycle"
    | "digest:save-snapshot"
    | "llm:preview"
    | "llm:classify"
    | "llm:summarize"
    | "stock-prices:refresh"
    | "alerts:generate"
    | "demo-data:seed"
  > | null;
  action_source_filter: SourceHealthFilter | null;
  action_target_id: string | null;
};

type MvpChecklistResponse = {
  generated_at: string;
  total_count: number;
  ready_count: number;
  partial_count: number;
  needs_action_count: number;
  items: MvpChecklistApiItem[];
};

type DemoDataSeedResponse = {
  seeded_stock_watchlist_count: number;
  seeded_company_watchlist_count: number;
  seeded_topic_watchlist_count: number;
  seeded_product_watchlist_count: number;
  seeded_demo_item_count: number;
  seeded_demo_manual_submission_count: number;
  seeded_demo_price_count: number;
  seeded_demo_alert_count: number;
  seeded_demo_alert_rule_count: number;
  seeded_demo_digest_snapshot_count: number;
  seeded_demo_digest_item_count: number;
};

type LlmOperationUsage = {
  operation: string;
  call_count: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
};

type SourceUpdatePayload = {
  name?: string;
  type?: string;
  access_method?: string;
  base_url?: string | null;
  auth_required?: boolean;
  enabled?: boolean;
  priority?: number;
  rate_limit?: string | null;
  polling_interval?: string | null;
  terms_notes?: string | null;
  raw_content_policy?: string | null;
};

type SourceCreatePayload = {
  name: string;
  type: string;
  access_method: string;
  base_url: string | null;
  enabled: boolean;
  priority: number;
  rate_limit: string | null;
  polling_interval: string | null;
  terms_notes: string | null;
  raw_content_policy: string | null;
};

type SourceFollowTemplate = {
  key: string;
  label: string;
  type: string;
  accessMethod: string;
  namePlaceholder: string;
  urlPlaceholder: string;
  pollingInterval: string;
  rateLimit: string;
  termsNotes: string;
  termsPlaceholder: string;
  rawContentPolicy: string;
  policyPlaceholder: string;
};

type SourceDraft = {
  name: string;
  type: string;
  access_method: string;
  base_url: string;
  auth_required: boolean;
  priority: string;
  polling_interval: string;
  rate_limit: string;
  terms_notes: string;
  raw_content_policy: string;
};

type SourceHealthFilter =
  | "all"
  | "attention"
  | "failed"
  | "stale"
  | "never_run"
  | "disabled"
  | "blocked";

type DigestSourceCoverage = {
  source_name: string;
  item_count: number;
};

type DigestSection = {
  key: string;
  title: string;
  focus: string;
  items: FeedItem[];
  metrics: {
    item_count: number;
    high_impact_count: number;
    stock_signal_count: number;
    read_later_count: number;
    source_count: number;
  };
};

type DigestAlertItem = {
  id: number;
  title: string;
  reason: string;
  severity: string;
  rule_name: string;
  created_at: string;
  item: FeedItem;
};

type DailyDigest = {
  digest_date: string;
  generated_at: string;
  headline: string;
  total_items: number;
  high_impact_count: number;
  stock_signal_count: number;
  read_later_count: number;
  active_alert_count: number;
  source_count: number;
  sections?: DigestSection[];
  active_alerts?: DigestAlertItem[];
  source_coverage?: DigestSourceCoverage[];
  watchlist_tickers?: string[];
  watchlist_companies?: string[];
  watchlist_topics?: string[];
  watchlist_products?: string[];
  disclaimer: string;
};

type DailyDigestMarkdown = {
  digest_date: string;
  generated_at: string;
  markdown: string;
};

type SavedItemsMarkdownExport = {
  generated_at: string;
  item_count: number;
  markdown: string;
};

type DailyDigestSnapshot = {
  id: number;
  digest_date: string;
  generated_at: string;
  headline: string;
  total_items: number;
  limit_per_section: number;
  usefulness_feedback: "useful" | "not_useful" | null;
  digest: DailyDigest;
  markdown: string;
  created_at: string;
  updated_at: string;
};

type EventCluster = {
  cluster_key: string;
  title: string;
  main_summary: string;
  explanation: string;
  uncertainty_notes: string[];
  category: string;
  topics: string[];
  tickers: string[];
  sources: string[];
  item_count: number;
  source_count: number;
  duplicate_item_count: number;
  confirmation_level: string;
  top_score: number;
  importance_score: number;
  confidence: number;
  earliest_source: string | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
  latest_update_at: string | null;
  related_market_ticker: string | null;
  related_market: StockMarketSnapshot | null;
  timeline: EventClusterTimelineItem[];
  representative_item: FeedItem;
  items: FeedItem[];
};

type EventClusterLlmExplanation = {
  cluster_key: string;
  model: string;
  explanation: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
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
  usefulness_feedback: "useful" | "not_useful" | null;
  usefulness_feedback_at: string | null;
  rule: AlertRule;
  item: FeedItem;
  disclaimer: string;
};

type AlertGenerationResult = {
  rules_seeded: number;
  alerts_created: number;
  active_alerts: number;
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
  snoozed_until: string | null;
};

type AlertRuleDraft = {
  name: string;
  description: string;
  category: string;
  severity: string;
  min_importance_score: string;
  min_stock_impact_score: string;
  tickers: string;
  topics: string;
};

type RankingWeights = {
  relevance: number;
  importance: number;
  novelty: number;
  source_quality: number;
  social_signal: number;
  stock_impact: number;
  freshness: number;
};

type UserPreferences = {
  user_id: string;
  ranking_weights: RankingWeights;
  preferred_sources: string[];
  blocked_sources: string[];
  language_preferences: string[];
};

type PersonalSettingsRestoreResult = {
  version: number;
  restored_at: string;
  preferences_updated: boolean;
  sources_upserted: number;
  alert_rules_upserted: number;
  stock_watchlist_upserted: number;
  company_watchlist_upserted: number;
  topic_watchlist_upserted: number;
  product_watchlist_upserted: number;
  skipped_sections: string[];
};

type IngestionSource =
  | "hacker-news"
  | "alpha-vantage-news"
  | "alpha-vantage-prices"
  | "arxiv"
  | "chinese-rss"
  | "sec-filings"
  | "github"
  | "hugging-face"
  | "product-hunt"
  | "rss";
type IngestionSourceAction = {
  source: IngestionSource;
  label: string;
  shortLabel: string;
  title: string;
  icon: typeof Activity;
};

type LoadState = "idle" | "loading" | "running";
type DashboardOperation =
  | "refresh"
  | "cycle"
  | "digest:save-snapshot"
  | "stock-prices:refresh"
  | "alerts:generate"
  | "demo-data:seed"
  | "llm:preview"
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
  | "clusters"
  | "submit"
  | "alerts"
  | "digest"
  | "sources"
  | "settings";
type FeedModuleKey = Extract<
  ModuleKey,
  "trends" | "research" | "products" | "stocks" | "chinese"
>;

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const STOCK_DISCLAIMER =
  "SignalLens links AI-related items to watched stocks for research only and does not provide investment advice.";

const DEFAULT_RANKING_WEIGHTS: RankingWeights = {
  relevance: 0.25,
  importance: 0.2,
  novelty: 0.15,
  source_quality: 0.15,
  social_signal: 0.1,
  stock_impact: 0.1,
  freshness: 0.05,
};

const rankingWeightFields: { key: keyof RankingWeights; label: string }[] = [
  { key: "relevance", label: "Relevance" },
  { key: "importance", label: "Importance" },
  { key: "novelty", label: "Novelty" },
  { key: "source_quality", label: "Source" },
  { key: "social_signal", label: "Social" },
  { key: "stock_impact", label: "Stock" },
  { key: "freshness", label: "Freshness" },
];

const emptyManualEngagementDraft: ManualEngagementDraft = {
  likes: "",
  comments_count: "",
  collects: "",
  reposts: "",
  views: "",
};

const MANUAL_TITLE_MAX_LENGTH = 500;
const MANUAL_SOURCE_NAME_MAX_LENGTH = 120;
const MANUAL_TEXT_MAX_LENGTH = 12000;
const MANUAL_PERSONAL_NOTE_MAX_LENGTH = 4000;
const MANUAL_TAG_LIMIT = 12;

const manualEngagementFields: { key: keyof ManualEngagementDraft; label: string }[] = [
  { key: "likes", label: "Likes" },
  { key: "comments_count", label: "Comments" },
  { key: "collects", label: "Collects" },
  { key: "reposts", label: "Reposts" },
  { key: "views", label: "Views" },
];

const sourceHealthFilterOptions: { key: SourceHealthFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "attention", label: "Attention" },
  { key: "failed", label: "Failed" },
  { key: "stale", label: "Stale" },
  { key: "never_run", label: "Never Run" },
  { key: "disabled", label: "Disabled" },
  { key: "blocked", label: "Blocked" },
];

const ingestionSourceActions: IngestionSourceAction[] = [
  {
    source: "hacker-news",
    label: "Hacker News",
    shortLabel: "HN",
    title: "Run Hacker News ingestion",
    icon: Newspaper,
  },
  {
    source: "alpha-vantage-news",
    label: "Stock News",
    shortLabel: "Stocks",
    title: "Run Alpha Vantage stock news ingestion",
    icon: BarChart3,
  },
  {
    source: "alpha-vantage-prices",
    label: "Stock Prices",
    shortLabel: "Prices",
    title: "Run Alpha Vantage daily price ingestion",
    icon: TrendingUp,
  },
  {
    source: "sec-filings",
    label: "SEC Filings",
    shortLabel: "SEC",
    title: "Run SEC filings ingestion",
    icon: FileText,
  },
  {
    source: "arxiv",
    label: "arXiv",
    shortLabel: "arXiv",
    title: "Run arXiv ingestion",
    icon: FlaskConical,
  },
  {
    source: "chinese-rss",
    label: "Chinese RSS",
    shortLabel: "CN",
    title: "Run configured Chinese RSS ingestion",
    icon: Newspaper,
  },
  {
    source: "github",
    label: "GitHub",
    shortLabel: "GitHub",
    title: "Run GitHub repository ingestion",
    icon: Github,
  },
  {
    source: "hugging-face",
    label: "Hugging Face",
    shortLabel: "HF",
    title: "Run Hugging Face model ingestion",
    icon: Bot,
  },
  {
    source: "product-hunt",
    label: "Product Hunt",
    shortLabel: "PH",
    title: "Run Product Hunt launch ingestion",
    icon: Rocket,
  },
  {
    source: "rss",
    label: "RSS",
    shortLabel: "RSS",
    title: "Run selected RSS feed ingestion",
    icon: Newspaper,
  },
];

const sourceTypeOptions: { value: string; label: string }[] = [
  { value: "blog", label: "Blog" },
  { value: "company", label: "Company" },
  { value: "community", label: "Community" },
  { value: "developer", label: "Developer" },
  { value: "research", label: "Research" },
  { value: "model_hub", label: "Model hub" },
  { value: "rss", label: "RSS" },
  { value: "github_repository", label: "GitHub repository" },
  { value: "product_launch", label: "Product launch" },
  { value: "product_topic", label: "Product topic" },
  { value: "social_keyword", label: "Social keyword" },
  { value: "chinese_social", label: "Chinese social" },
  { value: "finance_news", label: "Finance news" },
  { value: "stock_prices", label: "Stock prices" },
  { value: "finance_filings", label: "Finance filings" },
];

const sourceFollowTemplates: SourceFollowTemplate[] = [
  {
    key: "blog_rss",
    label: "Blog RSS",
    type: "blog",
    accessMethod: "rss",
    namePlaceholder: "Latent Space",
    urlPlaceholder: "https://www.latent.space/feed",
    pollingInterval: "6 hours",
    rateLimit: "Public RSS/Atom feed; keep polling conservative.",
    termsNotes: "Public blog RSS/Atom feed only.",
    termsPlaceholder: "Public blog RSS/Atom feed only.",
    rawContentPolicy: "Store public feed metadata, title, excerpt, URL, and publication time.",
    policyPlaceholder: "Store title, URL, source time, and short excerpt only.",
  },
  {
    key: "company_blog",
    label: "Company Blog",
    type: "company",
    accessMethod: "rss",
    namePlaceholder: "OpenAI Blog",
    urlPlaceholder: "https://openai.com/news/rss.xml",
    pollingInterval: "6 hours",
    rateLimit: "Public company RSS/Atom feed; keep polling conservative.",
    termsNotes: "Public company announcements and blog posts.",
    termsPlaceholder: "Public company announcements and blog posts.",
    rawContentPolicy: "Store public company post metadata, title, excerpt, URL, and publication time.",
    policyPlaceholder: "Store public announcement metadata and short excerpts only.",
  },
  {
    key: "github_repository",
    label: "GitHub Repo",
    type: "github_repository",
    accessMethod: "official_api",
    namePlaceholder: "LangChain Repo",
    urlPlaceholder: "https://github.com/langchain-ai/langchain",
    pollingInterval: "12 hours",
    rateLimit: "GitHub public API; set GITHUB_TOKEN for higher rate limits.",
    termsNotes: "Track public repository releases, stars, and README metadata.",
    termsPlaceholder: "Track public repository releases, stars, and README metadata.",
    rawContentPolicy: "Store public repository metadata and summaries; do not clone repository contents.",
    policyPlaceholder: "Store public repo metadata and summaries only.",
  },
  {
    key: "product_hunt_topic",
    label: "Product Hunt Topic",
    type: "product_topic",
    accessMethod: "official_graphql_api",
    namePlaceholder: "Product Hunt AI Coding",
    urlPlaceholder: "https://www.producthunt.com/topics/artificial-intelligence",
    pollingInterval: "6 hours",
    rateLimit: "Product Hunt API token required; keep topic polling conservative.",
    termsNotes: "AI products, developer tools, and launch metadata.",
    termsPlaceholder: "AI products, developer tools, and launch metadata.",
    rawContentPolicy: "Store Product Hunt launch metadata returned by the official GraphQL API.",
    policyPlaceholder: "Store launch metadata from the official API only.",
  },
  {
    key: "chinese_social_feed",
    label: "Chinese/XHS RSS",
    type: "social_keyword",
    accessMethod: "rss",
    namePlaceholder: "Chinese AI Apps Feed",
    urlPlaceholder: "https://example.com/chinese-ai/rss.xml",
    pollingInterval: "6 hours",
    rateLimit: "Public RSS/Atom metadata only; no login-protected social scraping.",
    termsNotes: "Chinese AI product keywords from public RSS/Atom feeds only.",
    termsPlaceholder: "AI photo, AI video, agent apps, public feed scope.",
    rawContentPolicy: "Store public RSS/Atom metadata and snippets only; avoid login-protected content.",
    policyPlaceholder: "Store public feed metadata and snippets only.",
  },
  {
    key: "xiaohongshu_manual_watch",
    label: "XHS Manual Watch",
    type: "social_keyword",
    accessMethod: "manual_watch",
    namePlaceholder: "Xiaohongshu AI Photo",
    urlPlaceholder: "Leave blank; submit public post URLs manually",
    pollingInterval: "",
    rateLimit: "Manual watch only; no automated Xiaohongshu scraping in MVP.",
    termsNotes: "Track manually submitted public Xiaohongshu links and user-provided context only.",
    termsPlaceholder: "Manual public Xiaohongshu links only; no login-protected collection.",
    rawContentPolicy: "Store submitted public URLs, titles, short excerpts, and user notes only.",
    policyPlaceholder: "Store manually submitted public link metadata only.",
  },
  {
    key: "x_account_manual",
    label: "X Account Watch",
    type: "community",
    accessMethod: "manual_watch",
    namePlaceholder: "X: @sama",
    urlPlaceholder: "https://x.com/sama",
    pollingInterval: "",
    rateLimit: "Manual watch only; no automated X/Twitter API calls or scraping in MVP.",
    termsNotes: "Track manually submitted public X/Twitter links for this account.",
    termsPlaceholder: "Manual public links only; no automated scraping.",
    rawContentPolicy: "Store manually submitted public URLs, titles, excerpts, and user notes only.",
    policyPlaceholder: "Store manually submitted public link metadata only.",
  },
  {
    key: "manual_watch",
    label: "Manual Watch",
    type: "community",
    accessMethod: "manual_watch",
    namePlaceholder: "Researcher Watchlist",
    urlPlaceholder: "https://example.com",
    pollingInterval: "",
    rateLimit: "Manual watch source; no automated collection until a connector is added.",
    termsNotes: "Track manually submitted URLs for this source.",
    termsPlaceholder: "Track manually submitted URLs for this source.",
    rawContentPolicy: "Store manually submitted URLs, titles, excerpts, and optional user-provided text.",
    policyPlaceholder: "Store submitted URL metadata and user-provided text only.",
  },
];

const productUseCaseOptions: { value: string; label: string }[] = [
  { value: "product_coding", label: "Coding" },
  { value: "product_media", label: "Media" },
  { value: "product_search", label: "Search" },
  { value: "product_education", label: "Education" },
  { value: "product_business", label: "Business" },
  { value: "product_productivity", label: "Productivity" },
  { value: "product_entertainment", label: "Entertainment" },
  { value: "product_general", label: "General" },
];

const categoryOptions: { value: string; label: string }[] = [
  { value: "technical_trend", label: "Technical trend" },
  { value: "research", label: "Research" },
  { value: "product", label: "Product" },
  { value: "stock_company_event", label: "Stock/company" },
  { value: "manual_submission", label: "Manual submission" },
  { value: "social_trend", label: "Social trend" },
  { value: "policy_regulation", label: "Policy/regulation" },
  { value: "infrastructure", label: "Infrastructure" },
  { value: "funding_mna", label: "Funding/M&A" },
  { value: "benchmark_evaluation", label: "Benchmark/evaluation" },
  { value: "open_source_release", label: "Open-source release" },
  { value: "tutorial_opinion", label: "Tutorial/opinion" },
  { value: "noise_irrelevant", label: "Noise/irrelevant" },
];

const alertCategoryOptions: { value: string; label: string }[] = [
  { value: "all", label: "Any" },
  { value: "technical_trend", label: "Trend" },
  { value: "research", label: "Research" },
  { value: "product", label: "Product" },
  { value: "stock_company_event", label: "Stock" },
  { value: "stock_price_move", label: "Price move" },
  { value: "earnings_guidance", label: "Earnings/guidance" },
  { value: "analyst_action", label: "Analyst action" },
  { value: "supply_chain_signal", label: "Supply chain" },
  { value: "theme_breakout", label: "Theme breakout" },
  { value: "social_trend", label: "Social" },
  { value: "policy_regulation", label: "Policy/regulation" },
  { value: "infrastructure", label: "Infrastructure" },
  { value: "funding_mna", label: "Funding/M&A" },
  { value: "benchmark_evaluation", label: "Benchmark/evaluation" },
  { value: "open_source_release", label: "Open-source release" },
  { value: "tutorial_opinion", label: "Tutorial/opinion" },
  { value: "noise_irrelevant", label: "Noise/irrelevant" },
  { value: "cross_source_cluster", label: "Cross-source" },
];

const alertSeverityOptions: { value: string; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

const moduleNavItems: { key: ModuleKey; label: string; icon: typeof Activity }[] = [
  { key: "dashboard", label: "Dashboard", icon: Activity },
  { key: "trends", label: "AI Trends", icon: TrendingUp },
  { key: "research", label: "Research", icon: FlaskConical },
  { key: "products", label: "Products", icon: Bot },
  { key: "stocks", label: "AI Stocks", icon: BarChart3 },
  { key: "chinese", label: "Chinese Social", icon: Newspaper },
  { key: "saved", label: "Saved Items", icon: Bookmark },
  { key: "clusters", label: "Clusters", icon: Flag },
  { key: "submit", label: "Submit URL", icon: Send },
  { key: "alerts", label: "Alerts", icon: BellRing },
  { key: "digest", label: "Daily Digest", icon: CalendarDays },
  { key: "sources", label: "Source Health", icon: DatabaseZap },
  { key: "settings", label: "Settings", icon: SlidersHorizontal },
];

const feedModuleKeys = new Set<ModuleKey>([
  "trends",
  "research",
  "products",
  "stocks",
  "chinese",
]);

export function Dashboard() {
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [moduleFeedOverrides, setModuleFeedOverrides] = useState<
    Partial<Record<FeedModuleKey, FeedItem[]>>
  >({});
  const [selectedFeedDetail, setSelectedFeedDetail] = useState<FeedItemDetail | null>(null);
  const [savedItems, setSavedItems] = useState<FeedItem[]>([]);
  const [hiddenItems, setHiddenItems] = useState<FeedItem[]>([]);
  const [stocks, setStocks] = useState<StockWatchlistItem[]>([]);
  const [stockSignals, setStockSignals] = useState<StockSignalSummary[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [stockBriefing, setStockBriefing] = useState<StockBriefing | null>(null);
  const [stockPriceSnapshot, setStockPriceSnapshot] = useState<StockMarketSnapshot | null>(null);
  const [stockLlmSummaries, setStockLlmSummaries] = useState<
    Record<string, StockBriefingLlmSummary>
  >({});
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
  const [sourceHealthFilter, setSourceHealthFilter] = useState<SourceHealthFilter>("all");
  const [sourceRunStatusFilter, setSourceRunStatusFilter] = useState<"all" | "failed">("all");
  const [sourceRunSourceFilter, setSourceRunSourceFilter] = useState<SourceHealth | null>(null);
  const [lastCycleResult, setLastCycleResult] = useState<ScheduledCycleResponse | null>(null);
  const [scheduleStatus, setScheduleStatus] = useState<IngestionScheduleStatus | null>(null);
  const [digest, setDigest] = useState<DailyDigest | null>(null);
  const [digestSnapshots, setDigestSnapshots] = useState<DailyDigestSnapshot[]>([]);
  const [activeDigestSnapshot, setActiveDigestSnapshot] = useState<DailyDigestSnapshot | null>(null);
  const [eventClusters, setEventClusters] = useState<EventCluster[]>([]);
  const [selectedEventCluster, setSelectedEventCluster] = useState<EventCluster | null>(null);
  const [clusterExplanations, setClusterExplanations] = useState<
    Record<string, EventClusterLlmExplanation>
  >({});
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [alertIncludeDismissed, setAlertIncludeDismissed] = useState(false);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [qualityMetrics, setQualityMetrics] = useState<QualityMetrics | null>(null);
  const [mvpChecklist, setMvpChecklist] = useState<MvpChecklistItem[] | null>(null);
  const [rankingDraft, setRankingDraft] = useState<RankingWeights>(DEFAULT_RANKING_WEIGHTS);
  const [preferredSourcesDraft, setPreferredSourcesDraft] = useState("");
  const [blockedSourcesDraft, setBlockedSourcesDraft] = useState("");
  const [languagePreferencesDraft, setLanguagePreferencesDraft] = useState("");
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [activeOperation, setActiveOperation] = useState<DashboardOperation | null>(null);
  const [status, setStatus] = useState("Ready");
  const [error, setError] = useState<string | null>(null);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [activeModule, setActiveModule] = useState<ModuleKey>("dashboard");
  const [busyItemId, setBusyItemId] = useState<number | null>(null);
  const [busyDetailItemId, setBusyDetailItemId] = useState<number | null>(null);
  const [busyMetadataItemId, setBusyMetadataItemId] = useState<number | null>(null);
  const [busyAlertId, setBusyAlertId] = useState<number | null>(null);
  const [busyAlertRuleId, setBusyAlertRuleId] = useState<number | null>(null);
  const [busyAlertGenerate, setBusyAlertGenerate] = useState(false);
  const [busyClusterKey, setBusyClusterKey] = useState<string | null>(null);
  const [busyClusterExplanationKey, setBusyClusterExplanationKey] = useState<string | null>(null);
  const [busySourceId, setBusySourceId] = useState<number | null>(null);
  const [busyStockTicker, setBusyStockTicker] = useState<string | null>(null);
  const [busyStockSummaryTicker, setBusyStockSummaryTicker] = useState<string | null>(null);
  const [busyCompanyBriefing, setBusyCompanyBriefing] = useState<string | null>(null);
  const [busyProductBriefing, setBusyProductBriefing] = useState<string | null>(null);
  const [busyTopicBriefing, setBusyTopicBriefing] = useState<string | null>(null);
  const [busyWatchlistKey, setBusyWatchlistKey] = useState<string | null>(null);
  const [busyPreferences, setBusyPreferences] = useState(false);
  const [busySettingsBackup, setBusySettingsBackup] = useState(false);
  const [busySettingsRestore, setBusySettingsRestore] = useState(false);
  const [busyDigestGenerate, setBusyDigestGenerate] = useState(false);
  const [busyDigestCopy, setBusyDigestCopy] = useState(false);
  const [busyDigestDownload, setBusyDigestDownload] = useState(false);
  const [busyDigestEmail, setBusyDigestEmail] = useState(false);
  const [busyDigestSave, setBusyDigestSave] = useState(false);
  const [busyDigestSnapshotId, setBusyDigestSnapshotId] = useState<number | null>(null);
  const [lastDigestGenerationMs, setLastDigestGenerationMs] = useState<number | null>(null);
  const [busySavedExport, setBusySavedExport] = useState(false);
  const [busySavedDownload, setBusySavedDownload] = useState(false);
  const [digestDateDraft, setDigestDateDraft] = useState("");
  const digestDateDraftRef = useRef("");
  const previousActiveModuleRef = useRef<ModuleKey>("dashboard");
  const [busySetupCopy, setBusySetupCopy] = useState(false);
  const [manualTitle, setManualTitle] = useState("");
  const [manualSourceName, setManualSourceName] = useState("Manual Submission");
  const [manualUrl, setManualUrl] = useState("");
  const [manualText, setManualText] = useState("");
  const [manualEngagement, setManualEngagement] = useState<ManualEngagementDraft>({
    ...emptyManualEngagementDraft,
  });
  const [manualPersonalNote, setManualPersonalNote] = useState("");
  const [manualTags, setManualTags] = useState("");
  const [manualSaveItem, setManualSaveItem] = useState(true);
  const [manualClassifyWithLlm, setManualClassifyWithLlm] = useState(false);
  const [manualSummarizeWithLlm, setManualSummarizeWithLlm] = useState(false);
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
  const [sourceTemplate, setSourceTemplate] = useState("blog_rss");
  const [sourceName, setSourceName] = useState("");
  const [sourceType, setSourceType] = useState("blog");
  const [sourceAccessMethod, setSourceAccessMethod] = useState("rss");
  const [sourceBaseUrl, setSourceBaseUrl] = useState("");
  const [sourcePollingInterval, setSourcePollingInterval] = useState("");
  const [sourceRateLimit, setSourceRateLimit] = useState("");
  const [sourceTermsNotes, setSourceTermsNotes] = useState("");
  const [sourceRawContentPolicy, setSourceRawContentPolicy] = useState("");
  const [alertRuleName, setAlertRuleName] = useState("");
  const [alertRuleCategory, setAlertRuleCategory] = useState("all");
  const [alertRuleTickers, setAlertRuleTickers] = useState("");
  const [alertRuleTopics, setAlertRuleTopics] = useState("");
  const [alertRuleImportance, setAlertRuleImportance] = useState("0.75");
  const [alertRuleStockImpact, setAlertRuleStockImpact] = useState("0");
  const [alertRuleSeverity, setAlertRuleSeverity] = useState("medium");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchSource, setSearchSource] = useState("");
  const [searchCategory, setSearchCategory] = useState("");
  const [searchSubcategory, setSearchSubcategory] = useState("");
  const [searchTicker, setSearchTicker] = useState("");
  const [searchCompany, setSearchCompany] = useState("");
  const [searchTopic, setSearchTopic] = useState("");
  const [searchManualTag, setSearchManualTag] = useState("");
  const [searchLanguage, setSearchLanguage] = useState("");
  const [searchDateFrom, setSearchDateFrom] = useState("");
  const [searchDateTo, setSearchDateTo] = useState("");
  const [searchMinImportance, setSearchMinImportance] = useState("");
  const [searchMinSocialSignal, setSearchMinSocialSignal] = useState("");
  const [searchReadStatus, setSearchReadStatus] = useState("");
  const [searchAiRelated, setSearchAiRelated] = useState("");
  const [searchIntent, setSearchIntent] = useState<SearchIntent | null>(null);
  const [searchSummary, setSearchSummary] = useState<string | null>(null);
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

  const refreshReadinessState = useCallback(async () => {
    const [nextQualityMetrics, nextMvpChecklist] = await Promise.all([
      fetchJson<QualityMetrics>("/api/quality-metrics").catch(() => null),
      fetchJson<MvpChecklistResponse>("/api/mvp-checklist")
        .then(mapMvpChecklistResponse)
        .catch(() => null),
    ]);
    setQualityMetrics(nextQualityMetrics);
    setMvpChecklist(nextMvpChecklist);
  }, [fetchJson]);

  const refreshAll = useCallback(async (operation?: DashboardOperation) => {
    if (operation) {
      setActiveOperation(operation);
    }
    const startedAt = performance.now();
    setLoadState("loading");
    setError(null);
    try {
      const digestDateQuery = buildDigestDateQuery(digestDateDraftRef.current);
      const sourceRunQuery = buildSourceRunQuery(sourceRunStatusFilter, sourceRunSourceFilter?.id);
      const [
        nextFeed,
        nextSavedItems,
        nextHiddenItems,
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
        nextScheduleStatus,
        nextQualityMetrics,
        nextMvpChecklist,
      ] =
        await Promise.all([
          fetchJson<FeedItem[]>("/api/feed?limit=30"),
          fetchJson<FeedItem[]>("/api/feed?limit=30&saved_only=true"),
          fetchJson<FeedItem[]>("/api/feed?limit=30&hidden_only=true"),
          fetchJson<StockWatchlistItem[]>("/api/watchlist/stocks"),
          fetchJson<StockSignalSummary[]>("/api/watchlist/stocks/signals/summary"),
          fetchJson<CompanyWatchlistItem[]>("/api/watchlist/companies"),
          fetchJson<ProductWatchlistItem[]>("/api/watchlist/products"),
          fetchJson<TopicWatchlistItem[]>("/api/watchlist/topics"),
          fetchJson<SourceHealth[]>("/api/sources/health"),
          fetchJson<SourceRunHistoryItem[]>(`/api/sources/runs${sourceRunQuery}`),
          fetchJson<DailyDigest>(`/api/digest/daily${digestDateQuery}`),
          fetchJson<DailyDigestSnapshot[]>("/api/digest/daily/snapshots?limit=5"),
          fetchJson<EventCluster[]>("/api/events/clusters?limit=8&min_items=2"),
          fetchJson<AlertItem[]>(
            `/api/alerts?limit=8${alertIncludeDismissed ? "&include_dismissed=true" : ""}`,
          ),
          fetchJson<AlertRule[]>("/api/alerts/rules"),
          fetchJson<UserPreferences>("/api/preferences"),
          fetchJson<SystemStatus>("/api/health"),
          fetchJson<IngestionScheduleStatus>("/api/ingestion/schedule"),
          fetchJson<QualityMetrics>("/api/quality-metrics").catch(() => null),
          fetchJson<MvpChecklistResponse>("/api/mvp-checklist")
            .then(mapMvpChecklistResponse)
            .catch(() => null),
        ]);
      setFeed(nextFeed);
      setSavedItems(nextSavedItems);
      setHiddenItems(nextHiddenItems);
      setStocks(nextStocks);
      setStockSignals(nextStockSignals);
      setCompanies(nextCompanies);
      setProductWatchlist(nextProductWatchlist);
      setTopics(nextTopics);
      setSources(nextSources);
      setSourceRuns(nextSourceRuns);
      setDigest(nextDigest);
      setLastDigestGenerationMs(null);
      setDigestSnapshots(nextDigestSnapshots);
      setEventClusters(nextEventClusters);
      setAlerts(nextAlerts);
      setAlertRules(nextAlertRules);
      setPreferences(nextPreferences);
      setSystemStatus(nextSystemStatus);
      setScheduleStatus(nextScheduleStatus);
      setQualityMetrics(nextQualityMetrics);
      setMvpChecklist(nextMvpChecklist);
      setModuleFeedOverrides({});
      setRankingDraft(nextPreferences.ranking_weights);
      setPreferredSourcesDraft(nextPreferences.preferred_sources.join(", "));
      setBlockedSourcesDraft(nextPreferences.blocked_sources.join(", "));
      setLanguagePreferencesDraft(nextPreferences.language_preferences.join(", "));
      setSelectedFeedDetail((detail) => reconcileFeedDetailAfterRefresh(detail, nextFeed));
      setSelectedEventCluster((cluster) =>
        reconcileEventClusterAfterRefresh(cluster, nextEventClusters),
      );
      setRefreshVersion((value) => value + 1);
      setStatus(
        `Loaded ${nextFeed.length} feed items in ${formatElapsedMs(
          performance.now() - startedAt,
        )}`,
      );
    } catch (err) {
      setError(readError(err));
      setStatus("Backend unavailable");
    } finally {
      setLoadState("idle");
      if (operation) {
        setActiveOperation(null);
      }
    }
  }, [alertIncludeDismissed, fetchJson, sourceRunSourceFilter, sourceRunStatusFilter]);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    const previousActiveModule = previousActiveModuleRef.current;
    previousActiveModuleRef.current = activeModule;
    if (!isFeedModuleKey(activeModule)) {
      return;
    }

    let cancelled = false;
    const shouldReportStatus = previousActiveModule !== activeModule;
    const moduleLabel =
      moduleNavItems.find((item) => item.key === activeModule)?.label ?? "Module";
    if (shouldReportStatus) {
      setError(null);
      setStatus(`Loading ${moduleLabel} feed`);
    }
    fetchJson<FeedItem[]>(`/api/feed?limit=30&module=${activeModule}`)
      .then((results) => {
        if (cancelled) {
          return;
        }
        setModuleFeedOverrides((current) => ({ ...current, [activeModule]: results }));
        setSelectedFeedDetail((detail) => reconcileFeedDetailAfterRefresh(detail, results));
        if (shouldReportStatus) {
          setStatus(`Loaded ${results.length} ${moduleLabel} items`);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(readError(err));
          if (shouldReportStatus) {
            setStatus(`${moduleLabel} feed failed`);
          }
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeModule, fetchJson, refreshVersion]);

  useEffect(() => {
    digestDateDraftRef.current = digestDateDraft;
  }, [digestDateDraft]);

  const refreshAllWithStatus = async (nextStatus: string) => {
    await refreshAll();
    setStatus(nextStatus);
  };

  const updateDigestDateDraft = (value: string) => {
    setDigestDateDraft(value);
    setActiveDigestSnapshot(null);
    setLastDigestGenerationMs(null);
  };

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
      setStockPriceSnapshot(null);
      return;
    }

    let cancelled = false;
    setBusyStockTicker(selectedTicker);
    Promise.allSettled([
      fetchJson<StockBriefing>(`/api/watchlist/stocks/${selectedTicker}/briefing?limit=8`),
      fetchJson<StockMarketSnapshot | null>(
        `/api/watchlist/stocks/${selectedTicker}/prices?limit=260`,
      ),
    ])
      .then(([briefingResult, pricesResult]) => {
        if (cancelled) {
          return;
        }
        if (briefingResult.status === "fulfilled") {
          setStockBriefing(briefingResult.value);
        } else {
          setError(readError(briefingResult.reason));
        }
        setStockPriceSnapshot(pricesResult.status === "fulfilled" ? pricesResult.value : null);
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
  }, [fetchJson, refreshVersion, selectedTicker]);

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
  }, [fetchJson, refreshVersion, selectedProductCategory]);

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
  }, [fetchJson, refreshVersion, selectedCompanyKey]);

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
  }, [fetchJson, refreshVersion, selectedTopic]);

  const runIngestion = async (source: IngestionSource) => {
    setActiveOperation(`ingest:${source}`);
    setLoadState("running");
    setError(null);
    try {
      const limit = source === "arxiv" ? 15 : source === "github" ? 20 : 25;
      const result = await fetchJson<IngestionRunResponse>(`/api/ingestion/${source}?limit=${limit}`, {
        method: "POST",
      });
      const hint = result.recovery_hint ? ` · ${result.recovery_hint}` : "";
      await refreshAllWithStatus(
        `${result.source_name}: ${result.items_fetched} fetched, ${result.items_stored} stored${hint}`,
      );
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
        `Cycle completed in ${formatDuration(result.duration_seconds)}: ${storedCount} stored, ${result.failed_source_count} failed, ${result.skipped_source_count} skipped, ${result.generated_alert_count} alerts, digest ${result.saved_digest_date ?? "not saved"}`,
      );
    } catch (err) {
      setError(readError(err));
      setStatus("Full ingestion cycle failed");
    } finally {
      setLoadState("idle");
      setActiveOperation(null);
    }
  };

  const seedDemoDataFromDashboard = async () => {
    setActiveOperation("demo-data:seed");
    setLoadState("running");
    setError(null);
    try {
      const result = await fetchJson<DemoDataSeedResponse>("/api/ingestion/demo-data", {
        method: "POST",
      });
      await refreshAll();
      const watchlistRows =
        result.seeded_stock_watchlist_count +
        result.seeded_company_watchlist_count +
        result.seeded_topic_watchlist_count +
        result.seeded_product_watchlist_count;
      setStatus(
        `Demo data ready: ${result.seeded_demo_item_count} items, ${result.seeded_demo_manual_submission_count} manual, ${result.seeded_demo_price_count} prices, ${result.seeded_demo_alert_count} alerts, ${result.seeded_demo_digest_snapshot_count} digest snapshot, ${watchlistRows} watchlist rows`,
      );
    } catch (err) {
      setError(readError(err));
      setStatus("Demo data seed failed");
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
    moduleOverride,
    dryRun = false,
  }: {
    summarize: boolean;
    classify: boolean;
    label: string;
    operation: DashboardOperation;
    moduleOverride?: FeedModuleKey | null;
    dryRun?: boolean;
  }) => {
    setActiveOperation(operation);
    setLoadState("running");
    setError(null);
    try {
      const activeFeedModule =
        moduleOverride !== undefined
          ? moduleOverride
          : isFeedModuleKey(activeModule)
            ? activeModule
            : null;
      const result = await fetchJson<FeedProcessingResponse>("/api/llm/process-feed", {
        method: "POST",
        body: JSON.stringify({
          limit: 3,
          summarize,
          classify,
          dry_run: dryRun,
          skip_summarized: true,
          skip_classified: true,
          min_classification_confidence: 0.7,
          module: activeFeedModule,
        }),
      });
      const callText = result.model_call_budget
        ? `, ${result.model_calls_attempted}/${result.model_call_budget} LLM calls attempted`
        : "";
      const moduleText = activeFeedModule
        ? ` for ${formatModuleLabel(activeFeedModule)}`
        : "";
      const nextStatus = result.dry_run
        ? `${label}${moduleText}: ${result.candidates_seen} candidates, ${result.planned_model_calls}/${result.model_call_budget} LLM calls would be attempted, ${result.skipped_count} skipped${formatLlmCandidatePreview(result.candidate_previews)}`
        : `${label}${moduleText}: ${result.classified_count} classified, ${result.summarized_count} summarized, ${result.skipped_count} skipped${callText}`;
      if (result.errors.length) {
        setError(`${result.errors.length} LLM item errors; see API response logs.`);
      }
      await refreshAllWithStatus(nextStatus);
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
          language_preferences: splitTerms(languagePreferencesDraft),
        }),
      });
      setPreferences(updated);
      setRankingDraft(updated.ranking_weights);
      setPreferredSourcesDraft(updated.preferred_sources.join(", "));
      setBlockedSourcesDraft(updated.blocked_sources.join(", "));
      setLanguagePreferencesDraft(updated.language_preferences.join(", "));
      await refreshAllWithStatus("Updated ranking preferences");
    } catch (err) {
      setError(readError(err));
      setStatus("Ranking preference update failed");
    } finally {
      setBusyPreferences(false);
    }
  };

  const downloadSettingsBackup = async () => {
    setBusySettingsBackup(true);
    setError(null);
    try {
      const backup = await fetchJson<Record<string, unknown>>("/api/settings/backup");
      const exportedAt =
        typeof backup.exported_at === "string" ? backup.exported_at : new Date().toISOString();
      downloadJsonFile(
        `signallens-settings-${safeFilenamePart(exportedAt.slice(0, 10))}.json`,
        backup,
      );
      setStatus("Downloaded settings backup");
    } catch (err) {
      setError(readError(err));
      setStatus("Settings backup download failed");
    } finally {
      setBusySettingsBackup(false);
    }
  };

  const restoreSettingsBackup = async (file: File | null) => {
    if (!file) {
      return;
    }
    setBusySettingsRestore(true);
    setError(null);
    try {
      const payload = JSON.parse(await file.text()) as Record<string, unknown>;
      const result = await fetchJson<PersonalSettingsRestoreResult>("/api/settings/restore", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const watchlistCount =
        result.stock_watchlist_upserted +
        result.company_watchlist_upserted +
        result.topic_watchlist_upserted +
        result.product_watchlist_upserted;
      const skippedText = result.skipped_sections.length
        ? `; skipped ${result.skipped_sections.join(", ")}`
        : "";
      const restoreStatus =
        `Restored settings: ${result.sources_upserted} sources, ` +
        `${watchlistCount} watchlist rows, ` +
        `${result.alert_rules_upserted} alert rules${skippedText}`;
      await refreshAllWithStatus(restoreStatus);
    } catch (err) {
      setError(readError(err));
      setStatus("Settings restore failed");
    } finally {
      setBusySettingsRestore(false);
    }
  };

  const toggleSourceBlockFromHealth = async (source: SourceHealth) => {
    setBusySourceId(source.id);
    setError(null);
    try {
      const currentBlockedSources = preferences?.blocked_sources ?? splitTerms(blockedSourcesDraft);
      const alreadyBlocked = currentBlockedSources.some(
        (name) => name.toLowerCase() === source.name.toLowerCase(),
      );
      const nextBlockedSources = alreadyBlocked
        ? currentBlockedSources.filter((name) => name.toLowerCase() !== source.name.toLowerCase())
        : [...currentBlockedSources, source.name];
      const updated = await fetchJson<UserPreferences>("/api/preferences", {
        method: "PATCH",
        body: JSON.stringify({ blocked_sources: nextBlockedSources }),
      });
      setPreferences(updated);
      setRankingDraft(updated.ranking_weights);
      setPreferredSourcesDraft(updated.preferred_sources.join(", "));
      setBlockedSourcesDraft(updated.blocked_sources.join(", "));
      setLanguagePreferencesDraft(updated.language_preferences.join(", "));
      await refreshAllWithStatus(
        alreadyBlocked ? `Unblocked source ${source.name}` : `Blocked source ${source.name}`,
      );
    } catch (err) {
      setError(readError(err));
      setStatus("Source block update failed");
    } finally {
      setBusySourceId(null);
    }
  };

  const runSearch = async () => {
    setLoadState("loading");
    setError(null);
    const startedAt = performance.now();
    try {
      const activeFeedModule = isFeedModuleKey(activeModule) ? activeModule : null;
      const hasManualFilters = [
        searchSource,
        searchCategory,
        searchSubcategory,
        searchTicker,
        searchCompany,
        searchTopic,
        searchManualTag,
        searchLanguage,
        searchDateFrom,
        searchDateTo,
        searchMinImportance,
        searchMinSocialSignal,
        searchReadStatus,
        searchAiRelated,
      ].some((value) => value.trim()) || savedOnly;

      if (searchQuery.trim() && !hasManualFilters) {
        const result = await fetchJson<NaturalLanguageSearchResponse>(
          "/api/search/natural-language",
          {
            method: "POST",
            body: JSON.stringify({
              query: searchQuery.trim(),
              limit: 30,
              module: activeFeedModule,
            }),
          },
        );
        applySearchResults(result.items, activeFeedModule);
        setSearchIntent(result.intent);
        setSearchSummary(result.summary);
        setStatus(searchStatusText(result.items.length, activeFeedModule, startedAt));
        return;
      }

      const params = new URLSearchParams();
      if (searchQuery.trim()) params.set("q", searchQuery.trim());
      if (searchSource.trim()) params.set("source", searchSource.trim());
      if (searchCategory.trim()) params.set("category", searchCategory.trim());
      if (searchSubcategory.trim()) params.set("subcategory", searchSubcategory.trim());
      if (searchTicker.trim()) params.set("ticker", searchTicker.trim().toUpperCase());
      if (searchCompany.trim()) params.set("company", searchCompany.trim());
      if (searchTopic.trim()) params.set("topic", searchTopic.trim());
      if (searchManualTag.trim()) params.set("manual_tag", searchManualTag.trim());
      if (searchLanguage.trim()) params.set("language", searchLanguage.trim().toLowerCase());
      if (searchDateFrom.trim()) params.set("date_from", searchDateFrom.trim());
      if (searchDateTo.trim()) params.set("date_to", searchDateTo.trim());
      if (searchMinImportance.trim()) {
        params.set("min_importance_score", searchMinImportance.trim());
      }
      if (searchMinSocialSignal.trim()) {
        params.set("min_social_signal_score", searchMinSocialSignal.trim());
      }
      if (searchReadStatus.trim()) params.set("read_status", searchReadStatus.trim());
      if (searchAiRelated.trim()) params.set("ai_related", searchAiRelated.trim());
      if (savedOnly) params.set("saved_only", "true");
      if (activeFeedModule) params.set("module", activeFeedModule);
      params.set("limit", "30");

      const results = await fetchJson<FeedItem[]>(`/api/search?${params.toString()}`);
      applySearchResults(results, activeFeedModule);
      setSearchIntent(null);
      setSearchSummary(null);
      setStatus(searchStatusText(results.length, activeFeedModule, startedAt));
    } catch (err) {
      setError(readError(err));
      setStatus("Search failed");
    } finally {
      setLoadState("idle");
    }
  };

  const applySearchResults = (results: FeedItem[], activeFeedModule: FeedModuleKey | null) => {
    if (activeFeedModule) {
      setModuleFeedOverrides((current) => ({ ...current, [activeFeedModule]: results }));
    } else {
      setFeed(results);
      if (activeModule !== "dashboard") {
        setActiveModule("dashboard");
      }
    }
    setSelectedFeedDetail((detail) => reconcileFeedDetailAfterRefresh(detail, results));
  };

  const clearSearch = async () => {
    const activeFeedModule = isFeedModuleKey(activeModule) ? activeModule : null;
    setSearchQuery("");
    setSearchSource("");
    setSearchCategory("");
    setSearchSubcategory("");
    setSearchTicker("");
    setSearchCompany("");
    setSearchTopic("");
    setSearchManualTag("");
    setSearchLanguage("");
    setSearchDateFrom("");
    setSearchDateTo("");
    setSearchMinImportance("");
    setSearchMinSocialSignal("");
    setSearchReadStatus("");
    setSearchAiRelated("");
    setSearchIntent(null);
    setSearchSummary(null);
    setSavedOnly(false);
    if (activeFeedModule) {
      setLoadState("loading");
      setError(null);
      try {
        const results = await fetchJson<FeedItem[]>(
          `/api/feed?limit=30&module=${activeFeedModule}`,
        );
        setModuleFeedOverrides((current) => ({ ...current, [activeFeedModule]: results }));
        setSelectedFeedDetail((detail) => reconcileFeedDetailAfterRefresh(detail, results));
        setStatus(`Cleared search in ${formatModuleLabel(activeFeedModule)}`);
      } catch (err) {
        setError(readError(err));
        setStatus("Clear search failed");
      } finally {
        setLoadState("idle");
      }
      return;
    }
    await refreshAll();
  };

  const updateSearchField = (setter: (value: string) => void, value: string) => {
    setter(value);
    setSearchIntent(null);
    setSearchSummary(null);
  };

  const updateSavedOnlySearchFilter = (value: boolean) => {
    setSavedOnly(value);
    setSearchIntent(null);
    setSearchSummary(null);
  };

  const applyTopicFeedFilter = async (topic: TopicWatchlistItem) => {
    setLoadState("loading");
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("limit", "30");
      params.set("topic", topic.topic);
      const results = await fetchJson<FeedItem[]>(`/api/feed?${params.toString()}`);
      setFeed(results);
      setActiveModule("dashboard");
      setSearchQuery("");
      setSearchSource("");
      setSearchCategory("");
      setSearchSubcategory("");
      setSearchTicker("");
      setSearchCompany("");
      setSearchTopic(topic.topic);
      setSearchManualTag("");
      setSearchLanguage("");
      setSearchDateFrom("");
      setSearchDateTo("");
      setSearchMinImportance("");
      setSearchMinSocialSignal("");
      setSearchReadStatus("");
      setSearchAiRelated("");
      setSavedOnly(false);
      setSearchIntent(null);
      setSearchSummary(null);
      setSelectedFeedDetail((detail) => reconcileFeedDetailAfterRefresh(detail, results));
      setStatus(`Filtered feed by topic ${topic.label}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Topic filter failed");
    } finally {
      setLoadState("idle");
    }
  };

  const applyTickerFeedFilter = async (stock: StockWatchlistItem) => {
    setLoadState("loading");
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("limit", "30");
      params.set("ticker", stock.ticker);
      const results = await fetchJson<FeedItem[]>(`/api/search?${params.toString()}`);
      setFeed(results);
      setActiveModule("dashboard");
      setSearchQuery("");
      setSearchSource("");
      setSearchCategory("");
      setSearchSubcategory("");
      setSearchTicker(stock.ticker);
      setSearchCompany("");
      setSearchTopic("");
      setSearchManualTag("");
      setSearchLanguage("");
      setSearchDateFrom("");
      setSearchDateTo("");
      setSearchMinImportance("");
      setSearchMinSocialSignal("");
      setSearchReadStatus("");
      setSearchAiRelated("");
      setSavedOnly(false);
      setSearchIntent(null);
      setSearchSummary(null);
      setSelectedFeedDetail((detail) => reconcileFeedDetailAfterRefresh(detail, results));
      setStatus(`Filtered feed by ticker ${stock.ticker}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Ticker filter failed");
    } finally {
      setLoadState("idle");
    }
  };

  const applySavedManualTagFilter = async (tag: string) => {
    setLoadState("loading");
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("limit", "30");
      params.set("manual_tag", tag);
      params.set("saved_only", "true");
      const results = await fetchJson<FeedItem[]>(`/api/search?${params.toString()}`);
      setFeed(results);
      setActiveModule("dashboard");
      setSearchQuery("");
      setSearchSource("");
      setSearchCategory("");
      setSearchSubcategory("");
      setSearchTicker("");
      setSearchCompany("");
      setSearchTopic("");
      setSearchManualTag(tag);
      setSearchLanguage("");
      setSearchDateFrom("");
      setSearchDateTo("");
      setSearchMinImportance("");
      setSearchMinSocialSignal("");
      setSearchReadStatus("");
      setSearchAiRelated("");
      setSavedOnly(true);
      setSearchIntent(null);
      setSearchSummary(null);
      setSelectedFeedDetail((detail) => reconcileFeedDetailAfterRefresh(detail, results));
      setStatus(`Filtered saved items by tag ${tag}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Saved tag filter failed");
    } finally {
      setLoadState("idle");
    }
  };

  const generateDailyDigest = async () => {
    setBusyDigestGenerate(true);
    setError(null);
    const startedAt = performance.now();
    try {
      const query = buildDigestDateQuery(digestDateDraft);
      const generated = await fetchJson<DailyDigest>(`/api/digest/daily/generate${query}`, {
        method: "POST",
      });
      const elapsedMs = performance.now() - startedAt;
      setDigest(generated);
      setDigestDateDraft(generated.digest_date);
      setActiveDigestSnapshot(null);
      setLastDigestGenerationMs(elapsedMs);
      setStatus(`Generated digest ${generated.digest_date} in ${formatElapsedMs(elapsedMs)}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Digest generation failed");
    } finally {
      setBusyDigestGenerate(false);
    }
  };

  const copyDailyDigest = async () => {
    setBusyDigestCopy(true);
    setError(null);
    try {
      const targetDigestDate = digestDateDraft || digest?.digest_date || "";
      const query = buildDigestDateQuery(targetDigestDate);
      if (activeDigestSnapshot?.digest_date === targetDigestDate) {
        if (!navigator.clipboard?.writeText) {
          throw new Error("Clipboard API unavailable.");
        }
        await navigator.clipboard.writeText(activeDigestSnapshot.markdown);
        setStatus(`Copied saved digest snapshot ${activeDigestSnapshot.digest_date}`);
        return;
      }
      const result = await fetchJson<DailyDigestMarkdown>(`/api/digest/daily/markdown${query}`);
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

  const copySavedItemsExport = async () => {
    setBusySavedExport(true);
    setError(null);
    try {
      const result = await fetchJson<SavedItemsMarkdownExport>(
        "/api/feed/saved/export/markdown?limit=100",
      );
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard API unavailable.");
      }
      await navigator.clipboard.writeText(result.markdown);
      setStatus(`Copied ${result.item_count} saved items`);
    } catch (err) {
      setError(readError(err));
      setStatus("Saved items export failed");
    } finally {
      setBusySavedExport(false);
    }
  };

  const downloadDailyDigest = async () => {
    setBusyDigestDownload(true);
    setError(null);
    try {
      const targetDigestDate = digestDateDraft || digest?.digest_date || "";
      const query = buildDigestDateQuery(targetDigestDate);
      const result =
        activeDigestSnapshot?.digest_date === targetDigestDate
          ? {
              digest_date: activeDigestSnapshot.digest_date,
              markdown: activeDigestSnapshot.markdown,
            }
          : await fetchJson<DailyDigestMarkdown>(`/api/digest/daily/markdown${query}`);
      downloadMarkdownFile(
        `signallens-daily-digest-${safeFilenamePart(result.digest_date || "latest")}.md`,
        result.markdown,
      );
      setStatus(`Downloaded digest ${result.digest_date || "latest"}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Digest download failed");
    } finally {
      setBusyDigestDownload(false);
    }
  };

  const downloadSavedItemsExport = async () => {
    setBusySavedDownload(true);
    setError(null);
    try {
      const result = await fetchJson<SavedItemsMarkdownExport>(
        "/api/feed/saved/export/markdown?limit=100",
      );
      downloadMarkdownFile("signallens-saved-items.md", result.markdown);
      setStatus(`Downloaded ${result.item_count} saved items`);
    } catch (err) {
      setError(readError(err));
      setStatus("Saved items download failed");
    } finally {
      setBusySavedDownload(false);
    }
  };

  const emailDailyDigest = async () => {
    setBusyDigestEmail(true);
    setError(null);
    try {
      const targetDigestDate = digestDateDraft || digest?.digest_date || "";
      const query = buildDigestDateQuery(targetDigestDate);
      const emailDateLabel = targetDigestDate || digest?.digest_date || "latest";
      const markdown =
        activeDigestSnapshot?.digest_date === targetDigestDate
          ? activeDigestSnapshot.markdown
          : (await fetchJson<DailyDigestMarkdown>(`/api/digest/daily/markdown${query}`)).markdown;
      window.location.href = buildDigestEmailHref(
        `SignalLens Daily Digest ${emailDateLabel}`,
        markdown,
      );
      setStatus(`Opened email draft for digest ${emailDateLabel}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Digest email draft failed");
    } finally {
      setBusyDigestEmail(false);
    }
  };

  const copyMissingEnvTemplate = async () => {
    setBusySetupCopy(true);
    setError(null);
    try {
      if (!systemStatus?.missing_env_template) {
        throw new Error("No missing setup values.");
      }
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard API unavailable.");
      }
      await navigator.clipboard.writeText(systemStatus.missing_env_template);
      setStatus("Copied missing .env template");
    } catch (err) {
      setError(readError(err));
      setStatus("Setup template copy failed");
    } finally {
      setBusySetupCopy(false);
    }
  };

  const saveDailyDigestSnapshot = async (targetDate?: string) => {
    setBusyDigestSave(true);
    setError(null);
    const startedAt = performance.now();
    try {
      const snapshotDate = targetDate ?? (digestDateDraft || digest?.digest_date || "");
      const query = buildDigestDateQuery(snapshotDate);
      const snapshot = await fetchJson<DailyDigestSnapshot>(`/api/digest/daily/snapshots${query}`, {
        method: "POST",
      });
      const elapsedMs = performance.now() - startedAt;
      setDigest(snapshot.digest);
      setDigestDateDraft(snapshot.digest_date);
      setActiveDigestSnapshot(snapshot);
      setLastDigestGenerationMs(elapsedMs);
      setDigestSnapshots((items) => [
        snapshot,
        ...items.filter((item) => item.digest_date !== snapshot.digest_date),
      ].slice(0, 5));
      await refreshReadinessState();
      setStatus(`Saved digest snapshot ${snapshot.digest_date} in ${formatElapsedMs(elapsedMs)}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Digest snapshot failed");
    } finally {
      setBusyDigestSave(false);
    }
  };

  const loadDigestSnapshot = (snapshot: DailyDigestSnapshot) => {
    setDigest(snapshot.digest);
    setDigestDateDraft(snapshot.digest_date);
    setActiveDigestSnapshot(snapshot);
    setLastDigestGenerationMs(null);
    setStatus(`Loaded digest snapshot ${snapshot.digest_date}`);
  };

  const deleteDailyDigestSnapshot = async (snapshot: DailyDigestSnapshot) => {
    setBusyDigestSnapshotId(snapshot.id);
    setError(null);
    try {
      await sendRequest(`/api/digest/daily/snapshots/${snapshot.id}`, { method: "DELETE" });
      setDigestSnapshots((items) => items.filter((item) => item.id !== snapshot.id));
      if (activeDigestSnapshot?.id === snapshot.id) {
        setActiveDigestSnapshot(null);
      }
      await refreshReadinessState();
      setStatus(`Deleted digest snapshot ${snapshot.digest_date}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Digest snapshot delete failed");
    } finally {
      setBusyDigestSnapshotId(null);
    }
  };

  const updateDailyDigestSnapshotFeedback = async (
    snapshot: DailyDigestSnapshot,
    usefulnessFeedback: "useful" | "not_useful",
  ) => {
    setBusyDigestSnapshotId(snapshot.id);
    setError(null);
    try {
      const nextFeedback =
        snapshot.usefulness_feedback === usefulnessFeedback ? null : usefulnessFeedback;
      const updated = await fetchJson<DailyDigestSnapshot>(
        `/api/digest/daily/snapshots/${snapshot.id}/feedback`,
        {
          method: "PATCH",
          body: JSON.stringify({ usefulness_feedback: nextFeedback }),
        },
      );
      setDigestSnapshots((items) =>
        items.map((item) => (item.id === updated.id ? updated : item)),
      );
      if (activeDigestSnapshot?.id === updated.id) {
        setActiveDigestSnapshot(updated);
        setDigest(updated.digest);
      }
      await refreshReadinessState();
      setStatus(
        nextFeedback
          ? `Marked digest snapshot ${updated.digest_date} ${formatDigestFeedback(nextFeedback)}`
          : `Cleared digest feedback ${updated.digest_date}`,
      );
    } catch (err) {
      setError(readError(err));
      setStatus("Digest feedback failed");
    } finally {
      setBusyDigestSnapshotId(null);
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
      setModuleFeedOverrides((items) => syncModuleFeedItem(items, summarized));
      setSavedItems((items) => syncSavedFeedItem(items, summarized));
      setSelectedFeedDetail((detail) => updateSelectedFeedDetail(detail, summarized));
      await refreshAllWithStatus(`Summarized item ${itemId}`);
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
      setModuleFeedOverrides((items) => syncModuleFeedItem(items, classified));
      setSavedItems((items) => syncSavedFeedItem(items, classified));
      setSelectedFeedDetail((detail) => updateSelectedFeedDetail(detail, classified));
      await refreshAllWithStatus(`Classified item ${itemId}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Classification failed");
    } finally {
      setBusyItemId(null);
    }
  };

  const saveFeedItemPersonalMetadata = async (
    itemId: number,
    personalNote: string,
    manualTags: string,
  ) => {
    setBusyMetadataItemId(itemId);
    setError(null);
    try {
      const updated = await fetchJson<FeedItemDetail>(
        `/api/feed/${itemId}/personal-metadata`,
        {
          method: "PATCH",
          body: JSON.stringify({
            personal_note: personalNote.trim() || null,
            manual_tags: splitTerms(manualTags),
          }),
        },
      );
      setSelectedFeedDetail(updated);
      setFeed((items) => items.map((item) => (item.id === itemId ? updated : item)));
      setModuleFeedOverrides((items) => syncModuleFeedItem(items, updated));
      setSavedItems((items) => syncSavedFeedItem(items, updated));
      setStatus(`Saved note for item ${itemId}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Saving item note failed");
    } finally {
      setBusyMetadataItemId(null);
    }
  };

  const submitManualItem = async () => {
    if (!manualUrl.trim()) {
      setError("Manual submissions need a URL.");
      return;
    }

    setLoadState("running");
    setError(null);
    try {
      const result = await fetchJson<ManualSubmissionResponse>("/api/manual-submissions", {
        method: "POST",
        body: JSON.stringify({
          title: manualTitle.trim() || null,
          url: manualUrl.trim(),
          text: manualText.trim() || null,
          source_name: manualSourceName.trim() || "Manual Submission",
          public_engagement: buildManualEngagementPayload(manualEngagement),
          save_item: manualSaveItem,
          personal_note: manualPersonalNote.trim() || null,
          manual_tags: splitTerms(manualTags),
          classify_with_llm: manualClassifyWithLlm,
          summarize_with_llm: manualSummarizeWithLlm,
        }),
      });
      setFeed((items) => [result.item, ...items.filter((item) => item.id !== result.item.id)]);
      setModuleFeedOverrides((items) => syncModuleFeedItem(items, result.item));
      setSavedItems((items) => syncSavedFeedItem(items, result.item));
      setSelectedFeedDetail((detail) => updateSelectedFeedDetail(detail, result.item));
      setManualTitle("");
      setManualUrl("");
      setManualText("");
      setManualEngagement({ ...emptyManualEngagementDraft });
      setManualPersonalNote("");
      setManualTags("");
      const completedSteps = [
        result.item.is_saved ? "saved" : null,
        result.classification_status === "succeeded" ? "classified" : null,
        result.summary_status === "succeeded" ? "summarized" : null,
      ].filter((value): value is string => Boolean(value));
      const submissionVerb = result.updated_existing ? "Updated" : "Submitted";
      let statusMessage = `${submissionVerb} item ${result.item.id}`;
      if (completedSteps.length > 0) {
        statusMessage = `${submissionVerb} item ${result.item.id} (${completedSteps.join(", ")})`;
      }
      await refreshAllWithStatus(statusMessage);
      const llmErrors = [
        result.classification_status === "failed"
          ? `classification failed: ${result.classification_error ?? "unknown error"}`
          : null,
        result.summary_status === "failed"
          ? `summary failed: ${result.summary_error ?? "unknown error"}`
          : null,
      ].filter((value): value is string => Boolean(value));
      if (llmErrors.length) {
        setError(`Manual item saved, but Kimi ${llmErrors.join("; ")}`);
      }
    } catch (err) {
      setError(readError(err));
      setStatus("Manual submission failed");
    } finally {
      setLoadState("idle");
    }
  };

  const submitStock = async () => {
    if (!stockTicker.trim() && !stockCompany.trim()) {
      setError("Stock watchlist entries need a ticker or company name.");
      return;
    }

    setLoadState("running");
    setError(null);
    try {
      const created = await fetchJson<StockWatchlistItem>("/api/watchlist/stocks", {
        method: "POST",
        body: JSON.stringify({
          ticker: stockTicker.trim() ? stockTicker.trim().toUpperCase() : null,
          company_name: stockCompany.trim() || null,
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
      await refreshAllWithStatus(`Added ${created.ticker}`);
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
      await refreshAllWithStatus(`Removed ${ticker}`);
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
      await refreshAllWithStatus(`Updated ${updated.ticker}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Stock update failed");
    } finally {
      setBusyWatchlistKey(null);
    }
  };

  const moveStock = async (ticker: string, direction: "up" | "down") => {
    const key = `stock:${ticker}`;
    setBusyWatchlistKey(key);
    setError(null);
    try {
      const updatedStocks = await fetchJson<StockWatchlistItem[]>(
        `/api/watchlist/stocks/${encodeURIComponent(ticker)}/move`,
        {
          method: "POST",
          body: JSON.stringify({ direction }),
        },
      );
      const updatedMap = new Map(updatedStocks.map((stock) => [stock.ticker, stock]));
      setStocks(updatedStocks);
      setStockSignals((items) =>
        items.map((item) => ({
          ...item,
          stock: updatedMap.get(item.stock.ticker) ?? item.stock,
        })),
      );
      if (stockBriefing?.stock.ticker) {
        const updatedBriefingStock = updatedMap.get(stockBriefing.stock.ticker);
        if (updatedBriefingStock) {
          setStockBriefing({ ...stockBriefing, stock: updatedBriefingStock });
        }
      }
      setStatus(`Moved ${ticker} ${direction}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Stock move failed");
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
      await refreshAllWithStatus(`Added company ${created.company_name}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Company add failed");
    } finally {
      setLoadState("idle");
    }
  };

  const updateCompany = async (
    companyKey: string,
    payload: Partial<Omit<CompanyWatchlistItem, "company_key">>,
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
      await refreshAllWithStatus(`Updated company ${updated.company_name}`);
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
      await refreshAllWithStatus(`Removed company ${companyKey}`);
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
      await refreshAllWithStatus(`Added topic ${created.label}`);
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
      await refreshAllWithStatus(`Removed topic ${topic}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Topic remove failed");
    } finally {
      setBusyWatchlistKey(null);
    }
  };

  const updateTopic = async (
    topic: string,
    payload: Partial<Omit<TopicWatchlistItem, "topic">>,
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
      await refreshAllWithStatus(`Updated topic ${updated.label}`);
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
      await refreshAllWithStatus(`Added product category ${created.label}`);
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
      await refreshAllWithStatus(`Updated product category ${updated.label}`);
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
      await refreshAllWithStatus(`Removed product category ${category}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Product category remove failed");
    } finally {
      setBusyWatchlistKey(null);
    }
  };

  const updateFeedAction = async (
    itemId: number,
    action:
      | "save"
      | "unsave"
      | "hide"
      | "unhide"
      | "mark-important"
      | "unmark-important"
      | "mark-read"
      | "mark-unread"
      | "mark-useful"
      | "mark-not-useful"
      | "clear-feedback",
  ) => {
    setBusyItemId(itemId);
    setError(null);
    try {
      const updated = await fetchJson<FeedItem>(`/api/feed/${itemId}/${action}`, {
        method: "POST",
      });
      if (action === "hide") {
        setFeed((items) => items.filter((item) => item.id !== itemId));
        setModuleFeedOverrides((items) => removeModuleFeedItem(items, itemId));
        setSavedItems((items) => items.filter((item) => item.id !== itemId));
        setSelectedFeedDetail((detail) => (detail?.id === itemId ? null : detail));
        await refreshAllWithStatus(`Hidden item ${itemId}`);
      } else if (action === "unhide") {
        setHiddenItems((items) => items.filter((item) => item.id !== itemId));
        await refreshAllWithStatus(`Restored hidden item ${itemId}`);
      } else if (action === "unsave") {
        setFeed((items) => items.map((item) => (item.id === itemId ? updated : item)));
        setModuleFeedOverrides((items) => syncModuleFeedItem(items, updated));
        setSavedItems((items) => syncSavedFeedItem(items, updated));
        setSelectedFeedDetail((detail) => updateSelectedFeedDetail(detail, updated));
        await refreshAllWithStatus(`Removed saved item ${itemId}`);
      } else if (action === "mark-read" || action === "mark-unread") {
        setFeed((items) => items.map((item) => (item.id === itemId ? updated : item)));
        setModuleFeedOverrides((items) => syncModuleFeedItem(items, updated));
        setSavedItems((items) => syncSavedFeedItem(items, updated));
        setSelectedFeedDetail((detail) => updateSelectedFeedDetail(detail, updated));
        await refreshAllWithStatus(
          action === "mark-read"
            ? `Marked item ${itemId} read`
            : `Marked item ${itemId} unread`,
        );
      } else {
        setFeed((items) => items.map((item) => (item.id === itemId ? updated : item)));
        setModuleFeedOverrides((items) => syncModuleFeedItem(items, updated));
        setSavedItems((items) => syncSavedFeedItem(items, updated));
        setSelectedFeedDetail((detail) => updateSelectedFeedDetail(detail, updated));
        await refreshAllWithStatus(feedActionStatus(action, itemId));
      }
    } catch (err) {
      setError(readError(err));
      setStatus("Item action failed");
    } finally {
      setBusyItemId(null);
    }
  };

  const removeFeedItemFromLocalState = (itemId: number) => {
    setFeed((items) => items.filter((item) => item.id !== itemId));
    setModuleFeedOverrides((items) => removeModuleFeedItem(items, itemId));
    setSavedItems((items) => items.filter((item) => item.id !== itemId));
    setHiddenItems((items) => items.filter((item) => item.id !== itemId));
    setSelectedFeedDetail((detail) => (detail?.id === itemId ? null : detail));
    setAlerts((items) => items.filter((alert) => alert.item.id !== itemId));
    setEventClusters((clusters) =>
      clusters.filter((cluster) => cluster.items.every((item) => item.id !== itemId)),
    );
    setSelectedEventCluster((cluster) =>
      cluster?.items.some((item) => item.id === itemId) ? null : cluster,
    );
  };

  const deleteFeedItem = async (itemId: number) => {
    if (!window.confirm("Permanently delete this item and stored source text?")) {
      return;
    }
    setBusyItemId(itemId);
    setError(null);
    try {
      await sendRequest(`/api/feed/${itemId}`, { method: "DELETE" });
      removeFeedItemFromLocalState(itemId);
      await refreshAllWithStatus(`Deleted item ${itemId}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Item delete failed");
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
      await refreshAllWithStatus(`Dismissed alert ${alertId}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Alert action failed");
    } finally {
      setBusyAlertId(null);
    }
  };

  const updateAlertFeedback = async (
    alert: AlertItem,
    usefulnessFeedback: "useful" | "not_useful",
  ) => {
    setBusyAlertId(alert.id);
    setError(null);
    try {
      const nextFeedback =
        alert.usefulness_feedback === usefulnessFeedback ? null : usefulnessFeedback;
      const updated = await fetchJson<AlertItem>(`/api/alerts/${alert.id}/feedback`, {
        method: "PATCH",
        body: JSON.stringify({ usefulness_feedback: nextFeedback }),
      });
      setAlerts((items) => items.map((item) => (item.id === alert.id ? updated : item)));
      await refreshQualityMetrics();
      setStatus(
        nextFeedback
          ? `Marked alert ${alert.id} ${nextFeedback === "useful" ? "useful" : "not useful"}`
          : `Cleared alert ${alert.id} feedback`,
      );
    } catch (err) {
      setError(readError(err));
      setStatus("Alert feedback failed");
    } finally {
      setBusyAlertId(null);
    }
  };

  const generateDashboardAlerts = async () => {
    setBusyAlertGenerate(true);
    setError(null);
    try {
      const result = await fetchJson<AlertGenerationResult>("/api/alerts/generate", {
        method: "POST",
      });
      await refreshAllWithStatus(
        `Generated alerts: ${result.alerts_created} new, ${result.active_alerts} active`,
      );
    } catch (err) {
      setError(readError(err));
      setStatus("Alert generation failed");
    } finally {
      setBusyAlertGenerate(false);
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
      await refreshAllWithStatus(
        `${updated.enabled ? "Enabled" : "Disabled"} alert rule ${updated.name}`,
      );
    } catch (err) {
      setError(readError(err));
      setStatus("Alert rule update failed");
    } finally {
      setBusyAlertRuleId(null);
    }
  };

  const snoozeAlertRule = async (rule: AlertRule) => {
    setBusyAlertRuleId(rule.id);
    setError(null);
    const snoozedUntil = isAlertRuleSnoozed(rule)
      ? null
      : new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    try {
      const updated = await fetchJson<AlertRule>(`/api/alerts/rules/${rule.id}`, {
        method: "PATCH",
        body: JSON.stringify({ snoozed_until: snoozedUntil }),
      });
      setAlertRules((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      await refreshAllWithStatus(
        snoozedUntil
          ? `Snoozed alert rule ${updated.name} until ${formatDate(snoozedUntil)}`
          : `Resumed alert rule ${updated.name}`,
      );
    } catch (err) {
      setError(readError(err));
      setStatus("Alert rule snooze failed");
    } finally {
      setBusyAlertRuleId(null);
    }
  };

  const updateAlertRuleDetails = async (
    rule: AlertRule,
    payload: Partial<Omit<AlertRule, "id">>,
  ) => {
    setBusyAlertRuleId(rule.id);
    setError(null);
    try {
      const updated = await fetchJson<AlertRule>(`/api/alerts/rules/${rule.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setAlertRules((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setAlerts((items) =>
        items.map((item) =>
          item.rule.id === updated.id ? { ...item, rule: updated } : item,
        ),
      );
      await refreshAllWithStatus(`Updated alert rule ${updated.name}`);
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
      await refreshAllWithStatus(`Deleted alert rule ${ruleId}`);
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

  const explainEventCluster = async (cluster: EventCluster) => {
    setBusyClusterExplanationKey(cluster.cluster_key);
    setError(null);
    try {
      const result = await fetchJson<EventClusterLlmExplanation>(
        `/api/events/clusters/${encodeURIComponent(cluster.cluster_key)}/llm-explanation`,
        { method: "POST" },
      );
      setClusterExplanations((items) => ({
        ...items,
        [cluster.cluster_key]: result,
      }));
      setStatus(`Explained cluster with ${result.model}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Cluster explanation failed");
    } finally {
      setBusyClusterExplanationKey(null);
    }
  };

  const explainStockBriefing = async (ticker: string) => {
    setBusyStockSummaryTicker(ticker);
    setError(null);
    try {
      const result = await fetchJson<StockBriefingLlmSummary>(
        `/api/watchlist/stocks/${encodeURIComponent(ticker)}/briefing/llm-summary?limit=8`,
        { method: "POST" },
      );
      setStockLlmSummaries((items) => ({
        ...items,
        [result.ticker]: result,
      }));
      setStatus(`Explained ${result.ticker} briefing with ${result.model}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Stock briefing explanation failed");
    } finally {
      setBusyStockSummaryTicker(null);
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
          severity: alertRuleSeverity,
          min_importance_score: Number(alertRuleImportance) || 0.75,
          min_stock_impact_score: Number(alertRuleStockImpact) || 0,
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
      setAlertRuleStockImpact("0");
      setAlertRuleSeverity("medium");
      await refreshAllWithStatus(`Added alert rule ${created.name}`);
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

  const selectSourceTemplate = (templateKey: string) => {
    const template =
      sourceFollowTemplates.find((item) => item.key === templateKey) ?? sourceFollowTemplates[0];
    setSourceTemplate(template.key);
    setSourceType(template.type);
    setSourceAccessMethod(template.accessMethod);
    setSourcePollingInterval(template.pollingInterval);
    setSourceRateLimit(template.rateLimit);
    setSourceTermsNotes((current) =>
      !current || sourceFollowTemplates.some((item) => item.termsNotes === current)
        ? template.termsNotes
        : current,
    );
    setSourceRawContentPolicy((current) =>
      !current || sourceFollowTemplates.some((item) => item.rawContentPolicy === current)
        ? template.rawContentPolicy
        : current,
    );
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
          rate_limit: sourceRateLimit.trim() || null,
          polling_interval: sourcePollingInterval.trim() || null,
          terms_notes: sourceTermsNotes.trim() || null,
          raw_content_policy: sourceRawContentPolicy.trim() || null,
        } satisfies SourceCreatePayload),
      });
      setSourceName("");
      setSourceTemplate("blog_rss");
      setSourceType("blog");
      setSourceAccessMethod("rss");
      setSourceBaseUrl("");
      setSourcePollingInterval("");
      setSourceRateLimit("");
      setSourceTermsNotes("");
      setSourceRawContentPolicy("");
      setSources((items) => [...items, created].sort((a, b) => a.priority - b.priority));
      await refreshAllWithStatus(`Following source ${created.name}`);
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
      const result = await fetchJson<IngestionRunResponse>(`/api/sources/${source.id}/run`, {
        method: "POST",
      });
      const hint = result.recovery_hint ? ` · ${result.recovery_hint}` : "";
      await refreshAllWithStatus(
        `${result.source_name}: ${result.status}, ${result.items_fetched} fetched, ${result.items_stored} stored, ${Math.round(result.store_rate * 100)}% stored${hint}`,
      );
    } catch (err) {
      setError(readError(err));
      setStatus("Source run failed");
    } finally {
      setBusySourceId(null);
    }
  };

  const deleteSource = async (source: SourceHealth) => {
    setBusySourceId(source.id);
    setError(null);
    try {
      await sendRequest(`/api/sources/${source.id}`, { method: "DELETE" });
      setSources((items) => items.filter((item) => item.id !== source.id));
      setSourceRuns((items) => items.filter((item) => item.source_id !== source.id));
      if (sourceRunSourceFilter?.id === source.id) {
        setSourceRunSourceFilter(null);
      }
      setStatus(`Removed source ${source.name}`);
    } catch (err) {
      setError(readError(err));
      setStatus("Source remove failed");
    } finally {
      setBusySourceId(null);
    }
  };

  const openQualityFindingAction = async (finding: QualityFinding) => {
    if (!finding.action_module) {
      return;
    }
    if (finding.action_module === "sources") {
      setSourceRunSourceFilter(null);
      setSourceHealthFilter(finding.action_source_filter ?? "all");
      setSourceRunStatusFilter(finding.action_source_filter === "failed" ? "failed" : "all");
    }
    setActiveModule(finding.action_module);
    scrollToDashboardTarget(qualityFindingTargetId(finding));
    if (finding.action_operation === "cycle") {
      await runFullCycle();
      return;
    }
    if (finding.action_operation === "llm:preview") {
      await processTopItemsWithLlm({
        summarize: true,
        classify: true,
        label: finding.title,
        operation: "llm:preview",
        moduleOverride: finding.action_module === "dashboard" ? null : undefined,
        dryRun: true,
      });
      return;
    }
    if (finding.action_operation === "llm:summarize") {
      await processTopItemsWithLlm({
        summarize: true,
        classify: false,
        label: finding.title,
        operation: "llm:summarize",
        moduleOverride: finding.action_module === "dashboard" ? null : undefined,
      });
      return;
    }
    if (finding.action_operation === "llm:classify") {
      await processTopItemsWithLlm({
        summarize: false,
        classify: true,
        label: finding.title,
        operation: "llm:classify",
        moduleOverride: finding.action_module === "dashboard" ? null : undefined,
      });
      return;
    }
    if (finding.action_operation === "digest:save-snapshot") {
      setActiveOperation("digest:save-snapshot");
      await saveDailyDigestSnapshot("");
      setActiveOperation(null);
      return;
    }
    if (finding.action_operation === "stock-prices:refresh") {
      await runIngestion("alpha-vantage-prices");
      return;
    }
    if (finding.action_operation === "alerts:generate") {
      await generateDashboardAlerts();
      return;
    }
    if (finding.action_operation === "demo-data:seed") {
      await seedDemoDataFromDashboard();
      return;
    }
    setStatus(`${finding.action_label ?? "Opened"}: ${finding.title}`);
  };

  const openMvpChecklistAction = async (item: MvpChecklistItem) => {
    if (item.actionModule) {
      if (item.actionModule === "sources" && item.actionSourceFilter) {
        setSourceHealthFilter(item.actionSourceFilter);
        setSourceRunStatusFilter(item.actionSourceFilter === "failed" ? "failed" : "all");
      }
      setActiveModule(item.actionModule);
    }
    scrollToDashboardTarget(item.actionTargetId);
    if (item.actionOperation === "demo-data:seed") {
      await seedDemoDataFromDashboard();
      return;
    }
    if (item.actionOperation === "cycle") {
      await runFullCycle();
      return;
    }
    if (item.actionOperation === "llm:preview") {
      await processTopItemsWithLlm({
        summarize: true,
        classify: true,
        label: item.label,
        operation: "llm:preview",
        moduleOverride: null,
        dryRun: true,
      });
      return;
    }
    if (item.actionOperation === "llm:classify") {
      await processTopItemsWithLlm({
        summarize: false,
        classify: true,
        label: item.label,
        operation: "llm:classify",
        moduleOverride: null,
      });
      return;
    }
    if (item.actionOperation === "digest:save-snapshot") {
      setActiveOperation("digest:save-snapshot");
      await saveDailyDigestSnapshot("");
      setActiveOperation(null);
      return;
    }
    if (item.actionOperation === "alerts:generate") {
      await generateDashboardAlerts();
      return;
    }
    if (item.actionOperation === "stock-prices:refresh") {
      await runIngestion("alpha-vantage-prices");
      return;
    }
    setStatus(`${item.actionLabel ?? "Opened"}: ${item.label}`);
  };

  const scrollToDashboardTarget = (targetId?: string, attempt = 0) => {
    if (!targetId) {
      return;
    }
    window.requestAnimationFrame(() => {
      const target = document.getElementById(targetId);
      if (target) {
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
        return;
      }
      if (attempt < 4) {
        window.setTimeout(() => scrollToDashboardTarget(targetId, attempt + 1), 50);
      }
    });
  };

  const moduleCounts = useMemo(
    () =>
      buildModuleCounts(
        feed,
        digest,
        savedItems,
        eventClusters,
        sources,
        preferences,
        moduleFeedOverrides,
        alerts,
        stocks,
        companies,
        topics,
        productWatchlist,
      ),
    [
      alerts,
      companies,
      digest,
      eventClusters,
      feed,
      moduleFeedOverrides,
      preferences,
      productWatchlist,
      savedItems,
      sources,
      stocks,
      topics,
    ],
  );
  const moduleFeed = useMemo(
    () => filterFeedByModule(feed, activeModule, digest, savedItems, moduleFeedOverrides),
    [activeModule, digest, feed, moduleFeedOverrides, savedItems],
  );
  const activeAlerts = useMemo(
    () => alerts.filter((alert) => alert.status === "active"),
    [alerts],
  );
  const activeModuleLabel =
    moduleNavItems.find((item) => item.key === activeModule)?.label ?? "Dashboard";

  const metrics = useMemo(() => {
    const isClusterView = activeModule === "clusters";
    const isAlertView = activeModule === "alerts";
    const isStockView = activeModule === "stocks";
    const isProductView = activeModule === "products";
    const isChineseView = activeModule === "chinese";
    const isTrendView = activeModule === "trends";
    const isResearchView = activeModule === "research";
    const isSubmitView = activeModule === "submit";
    if (isAlertView) {
      return [
        { label: "Feed", value: feed.length },
        { label: "View", value: alerts.length },
        { label: "Active", value: activeAlerts.length },
        { label: "Rules", value: alertRules.length },
        { label: "Dismissed", value: alerts.filter((alert) => alert.status !== "active").length },
      ];
    }
    if (isStockView) {
      return [
        { label: "Feed", value: feed.length },
        { label: "Watchlist", value: stocks.length },
        { label: "Companies", value: companies.length },
        {
          label: "Signals",
          value: stockSignals.reduce((total, summary) => total + summary.signal_count, 0),
        },
        {
          label: "High",
          value: stockSignals.reduce((total, summary) => total + summary.high_impact_count, 0),
        },
      ];
    }
    if (isProductView) {
      return [
        { label: "Feed", value: feed.length },
        { label: "View", value: moduleFeed.length },
        { label: "Categories", value: productWatchlist.length },
        {
          label: "High",
          value: moduleFeed.filter((item) => item.importance_score >= 0.75).length,
        },
        {
          label: "Digest",
          value: productWatchlist.filter((item) => item.include_in_digest).length,
        },
      ];
    }
    if (isChineseView) {
      const chineseSources = new Set(moduleFeed.map((item) => item.source_name));
      const chineseProducts = new Set(moduleFeed.flatMap((item) => item.products));
      return [
        { label: "Feed", value: feed.length },
        { label: "View", value: moduleFeed.length },
        { label: "Sources", value: chineseSources.size },
        { label: "Products", value: chineseProducts.size },
        {
          label: "Experimental",
          value: moduleFeed.filter((item) => item.subcategory?.includes("social_keyword")).length,
        },
      ];
    }
    if (isTrendView) {
      return [
        { label: "Feed", value: feed.length },
        { label: "View", value: moduleFeed.length },
        { label: "Topics", value: topics.length },
        {
          label: "Trend Topics",
          value: topics.filter((topic) => topic.category === "technical_trend").length,
        },
        {
          label: "Digest",
          value: topics.filter((topic) => topic.include_in_digest).length,
        },
      ];
    }
    if (isResearchView) {
      const researchSources = new Set(moduleFeed.map((item) => item.source_name));
      return [
        { label: "Feed", value: feed.length },
        { label: "View", value: moduleFeed.length },
        { label: "Papers", value: moduleFeed.filter((item) => item.category === "research").length },
        {
          label: "Benchmarks",
          value: moduleFeed.filter((item) => item.category === "benchmark_evaluation").length,
        },
        { label: "Sources", value: researchSources.size },
      ];
    }
    if (isSubmitView) {
      const manualItems = feed.filter((item) => item.category === "manual_submission");
      return [
        { label: "Feed", value: feed.length },
        { label: "Manual", value: manualItems.length },
        { label: "Saved", value: manualItems.filter((item) => item.is_saved).length },
        { label: "Unread", value: manualItems.filter((item) => !item.is_read).length },
        { label: "Tagged", value: manualItems.filter((item) => item.manual_tags.length).length },
      ];
    }
    const viewCount = isClusterView ? eventClusters.length : moduleFeed.length;
    const highImportance = isClusterView
      ? eventClusters.filter((cluster) => cluster.importance_score >= 0.75).length
      : moduleFeed.filter((item) => item.importance_score >= 0.75).length;
    const summarized = isClusterView
      ? eventClusters.filter((cluster) => cluster.main_summary).length
      : moduleFeed.filter((item) => item.summary_detailed).length;
    return [
      { label: "Feed", value: feed.length },
      { label: "View", value: viewCount },
      { label: "High", value: highImportance },
      { label: "Alerts", value: activeAlerts.length },
      { label: "Summaries", value: summarized },
    ];
  }, [
    activeAlerts.length,
    activeModule,
    alertRules.length,
    alerts,
    companies.length,
    eventClusters,
    feed,
    feed.length,
    moduleFeed,
    productWatchlist,
    stockSignals,
    stocks,
    topics,
  ]);

  const systemStatusPanel = (
    <div id="system-readiness-workflow">
      <SystemStatusPanel
        status={systemStatus}
        itemCount={feed.length}
        sourceCount={sources.length}
        enabledSourceCount={sources.filter((source) => source.enabled).length}
        alertCount={activeAlerts.length}
        watchlistCount={stocks.length + companies.length + topics.length + productWatchlist.length}
        qualityMetrics={qualityMetrics}
        mvpChecklist={mvpChecklist}
        busyCopy={busySetupCopy}
        disabled={loadState !== "idle"}
        onCopyMissingEnv={copyMissingEnvTemplate}
        onQualityFindingAction={openQualityFindingAction}
        onMvpChecklistAction={openMvpChecklistAction}
      />
    </div>
  );
  const rankingPreferencesPanel = (
    <div id="settings-workflow">
      <RankingPreferencesPanel
        preferences={preferences}
        draft={rankingDraft}
        preferredSources={preferredSourcesDraft}
        blockedSources={blockedSourcesDraft}
        languagePreferences={languagePreferencesDraft}
        disabled={loadState !== "idle"}
        busy={busyPreferences}
        onDraftChange={updateRankingDraft}
        onPreferredSourcesChange={setPreferredSourcesDraft}
        onBlockedSourcesChange={setBlockedSourcesDraft}
        onLanguagePreferencesChange={setLanguagePreferencesDraft}
        onReset={() => setRankingDraft(DEFAULT_RANKING_WEIGHTS)}
        onSave={saveRankingPreferences}
      />
    </div>
  );
  const stockWatchlistPanel = (
    <div id="stock-watchlist-workflow">
      <StockTable
        stocks={stocks}
        signalSummaries={stockSignals}
        stockBriefing={stockBriefing}
        stockPriceSnapshot={stockPriceSnapshot}
        stockLlmSummary={selectedTicker ? stockLlmSummaries[selectedTicker] ?? null : null}
        eventClusters={eventClusters}
        selectedTicker={selectedTicker}
        busyStockTicker={busyStockTicker}
        busyStockSummaryTicker={busyStockSummaryTicker}
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
        onExplainStock={explainStockBriefing}
        onUpdateStock={updateStock}
        onMoveStock={moveStock}
        onDeleteStock={deleteStock}
        onSubmit={submitStock}
      />
    </div>
  );
  const companyWatchlistPanel = (
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
  );
  const productWatchlistPanel = (
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
  );
  const topicWatchlistPanel = (
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
  );
  const chineseSocialPanel = (
    <ChineseSocialPanel
      items={activeModule === "chinese" ? moduleFeed : feed}
      limit={activeModule === "chinese" ? undefined : 5}
    />
  );
  const researchReviewPanel = <ResearchReviewPanel items={moduleFeed} />;
  const manualSubmissionPanel = (
    <div id="manual-submission-workflow">
      <ManualSubmissionPanel
        title={manualTitle}
        sourceName={manualSourceName}
        url={manualUrl}
        text={manualText}
        engagement={manualEngagement}
        personalNote={manualPersonalNote}
        manualTags={manualTags}
        saveItem={manualSaveItem}
        classifyWithLlm={manualClassifyWithLlm}
        summarizeWithLlm={manualSummarizeWithLlm}
        disabled={loadState !== "idle"}
        onTitleChange={setManualTitle}
        onSourceNameChange={setManualSourceName}
        onUrlChange={setManualUrl}
        onTextChange={setManualText}
        onEngagementChange={(key, value) =>
          setManualEngagement((current) => ({ ...current, [key]: value }))
        }
        onPersonalNoteChange={setManualPersonalNote}
        onManualTagsChange={setManualTags}
        onSaveItemChange={setManualSaveItem}
        onClassifyWithLlmChange={setManualClassifyWithLlm}
        onSummarizeWithLlmChange={setManualSummarizeWithLlm}
        onSubmit={submitManualItem}
      />
    </div>
  );
  const rankedFeedPanel = (
    <section className="section" id="ranked-feed-workflow">
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
        subcategory={searchSubcategory}
        ticker={searchTicker}
        company={searchCompany}
        topic={searchTopic}
        manualTag={searchManualTag}
        stockOptions={stocks}
        topicOptions={topics}
        language={searchLanguage}
        dateFrom={searchDateFrom}
        dateTo={searchDateTo}
        minImportance={searchMinImportance}
        minSocialSignal={searchMinSocialSignal}
        readStatus={searchReadStatus}
        aiRelated={searchAiRelated}
        intent={searchIntent}
        summary={searchSummary}
        savedOnly={savedOnly}
        disabled={loadState !== "idle"}
        onQueryChange={(value) => updateSearchField(setSearchQuery, value)}
        onSourceChange={(value) => updateSearchField(setSearchSource, value)}
        onCategoryChange={(value) => updateSearchField(setSearchCategory, value)}
        onSubcategoryChange={(value) => updateSearchField(setSearchSubcategory, value)}
        onTickerChange={(value) => updateSearchField(setSearchTicker, value)}
        onCompanyChange={(value) => updateSearchField(setSearchCompany, value)}
        onTopicChange={(value) => updateSearchField(setSearchTopic, value)}
        onManualTagChange={(value) => updateSearchField(setSearchManualTag, value)}
        onTickerFilter={applyTickerFeedFilter}
        onTopicFilter={applyTopicFeedFilter}
        onLanguageChange={(value) => updateSearchField(setSearchLanguage, value)}
        onDateFromChange={(value) => updateSearchField(setSearchDateFrom, value)}
        onDateToChange={(value) => updateSearchField(setSearchDateTo, value)}
        onMinImportanceChange={(value) => updateSearchField(setSearchMinImportance, value)}
        onMinSocialSignalChange={(value) =>
          updateSearchField(setSearchMinSocialSignal, value)
        }
        onReadStatusChange={(value) => updateSearchField(setSearchReadStatus, value)}
        onAiRelatedChange={(value) => updateSearchField(setSearchAiRelated, value)}
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
              busyMetadata={busyMetadataItemId === item.id}
              onSummarize={summarizeItem}
              onClassify={classifyItem}
              onDetail={loadFeedDetail}
              onAction={updateFeedAction}
              onDelete={deleteFeedItem}
              onPersonalMetadataSave={saveFeedItemPersonalMetadata}
            />
          ))
        ) : (
          <div className="empty-state">No items for this module.</div>
        )}
      </div>
    </section>
  );
  const schedulerStatusPanel = (
    <SchedulerStatusPanel
      schedule={scheduleStatus}
      disabled={loadState !== "idle"}
      busy={activeOperation === "cycle"}
      onRunCycle={runFullCycle}
    />
  );
  const settingsBackupPanel = (
    <SettingsBackupPanel
      disabled={loadState !== "idle"}
      busyBackup={busySettingsBackup}
      busyRestore={busySettingsRestore}
      onDownload={downloadSettingsBackup}
      onRestore={restoreSettingsBackup}
    />
  );
  const sourceHealthPanel = (
    <div id="source-health-workflow">
      <SourceTable
        sources={sources}
        runs={sourceRuns}
        sourceFilter={sourceHealthFilter}
        runStatusFilter={sourceRunStatusFilter}
        runSourceFilter={sourceRunSourceFilter}
        lastCycleResult={lastCycleResult}
        blockedSources={preferences?.blocked_sources ?? []}
        sourceTemplate={sourceTemplate}
        name={sourceName}
        type={sourceType}
        accessMethod={sourceAccessMethod}
        baseUrl={sourceBaseUrl}
        termsNotes={sourceTermsNotes}
        rawContentPolicy={sourceRawContentPolicy}
        pollingInterval={sourcePollingInterval}
        rateLimit={sourceRateLimit}
        disabled={loadState !== "idle"}
        busySourceId={busySourceId}
        onSourceTemplateChange={selectSourceTemplate}
        onNameChange={setSourceName}
        onTypeChange={setSourceType}
        onAccessMethodChange={setSourceAccessMethod}
        onBaseUrlChange={setSourceBaseUrl}
        onPollingIntervalChange={setSourcePollingInterval}
        onRateLimitChange={setSourceRateLimit}
        onTermsNotesChange={setSourceTermsNotes}
        onRawContentPolicyChange={setSourceRawContentPolicy}
        onSourceFilterChange={setSourceHealthFilter}
        onRunStatusFilterChange={setSourceRunStatusFilter}
        onRunSourceFilterChange={setSourceRunSourceFilter}
        onSubmit={submitSource}
        onRunSource={runSourceNow}
        activeOperation={activeOperation}
        onRunBuiltInSource={runIngestion}
        onToggleSource={toggleSource}
        onUpdateSource={updateSource}
        onToggleSourceBlock={toggleSourceBlockFromHealth}
        onDeleteSource={deleteSource}
      />
    </div>
  );

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
            <IngestionActionButtons
              activeOperation={activeOperation}
              disabled={loadState !== "idle"}
              onRunSource={runIngestion}
              labelMode="short"
            />
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
                  summarize: true,
                  classify: true,
                  label: "LLM preview",
                  operation: "llm:preview",
                  dryRun: true,
                })
              }
              disabled={loadState !== "idle"}
              title="Preview capped Kimi calls for top feed items"
            >
              {activeOperation === "llm:preview" ? (
                <Loader2 className="spin" size={16} />
              ) : (
                <Bot size={16} />
              )}
              Preview
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
          {activeModule === "sources" ? (
            sourceHealthPanel
          ) : activeModule === "settings" ? (
            <section className="module-stack">
              {systemStatusPanel}
              {schedulerStatusPanel}
              {rankingPreferencesPanel}
              {settingsBackupPanel}
            </section>
          ) : activeModule === "alerts" ? (
            <AlertPanel
              alerts={alerts}
              rules={alertRules}
              includeDismissed={alertIncludeDismissed}
              busyAlertId={busyAlertId}
              busyAlertRuleId={busyAlertRuleId}
              busyGenerate={busyAlertGenerate}
              ruleName={alertRuleName}
              ruleCategory={alertRuleCategory}
              ruleTickers={alertRuleTickers}
              ruleTopics={alertRuleTopics}
              ruleImportance={alertRuleImportance}
              ruleStockImpact={alertRuleStockImpact}
              ruleSeverity={alertRuleSeverity}
              disabled={loadState !== "idle"}
              onDismiss={dismissAlert}
              onFeedback={updateAlertFeedback}
              onGenerate={generateDashboardAlerts}
              onIncludeDismissedChange={setAlertIncludeDismissed}
              onRuleToggle={toggleAlertRule}
              onRuleSnooze={snoozeAlertRule}
              onRuleUpdate={updateAlertRuleDetails}
              onRuleDelete={deleteAlertRule}
              onRuleNameChange={setAlertRuleName}
              onRuleCategoryChange={setAlertRuleCategory}
              onRuleTickersChange={setAlertRuleTickers}
              onRuleTopicsChange={setAlertRuleTopics}
              onRuleImportanceChange={setAlertRuleImportance}
              onRuleStockImpactChange={setAlertRuleStockImpact}
              onRuleSeverityChange={setAlertRuleSeverity}
              onRuleSubmit={submitAlertRule}
            />
          ) : activeModule === "saved" ? (
            <SavedItemsPanel
              items={savedItems}
              busyItemId={busyItemId}
              busyDetailItemId={busyDetailItemId}
              busyMetadataItemId={busyMetadataItemId}
              busyExport={busySavedExport}
              busyDownload={busySavedDownload}
              selectedDetail={selectedFeedDetail}
              onCopyExport={copySavedItemsExport}
              onDownloadExport={downloadSavedItemsExport}
              onDetail={loadFeedDetail}
              onManualTagFilter={applySavedManualTagFilter}
              onPersonalMetadataSave={saveFeedItemPersonalMetadata}
              onReadToggle={(item) =>
                updateFeedAction(item.id, item.is_read ? "mark-unread" : "mark-read")
              }
              onUnsave={(itemId) => updateFeedAction(itemId, "unsave")}
            />
          ) : activeModule === "clusters" ? (
            <EventClusterPanel
              clusters={eventClusters}
              selectedCluster={selectedEventCluster}
              busyClusterKey={busyClusterKey}
              busyClusterExplanationKey={busyClusterExplanationKey}
              explanations={clusterExplanations}
              onSelectCluster={loadEventCluster}
              onExplainCluster={explainEventCluster}
            />
          ) : activeModule === "digest" ? (
            <DailyDigestPanel
              digest={digest}
              snapshots={digestSnapshots}
              digestDate={digestDateDraft}
              activeSnapshotId={activeDigestSnapshot?.id ?? null}
              generationElapsedMs={lastDigestGenerationMs}
              busySnapshotId={busyDigestSnapshotId}
              busyGenerate={busyDigestGenerate}
              busyCopy={busyDigestCopy}
              busyDownload={busyDigestDownload}
              busyEmail={busyDigestEmail}
              busySave={busyDigestSave}
              onDigestDateChange={updateDigestDateDraft}
              onGenerate={generateDailyDigest}
              onCopy={copyDailyDigest}
              onDownload={downloadDailyDigest}
              onEmail={emailDailyDigest}
              onSave={saveDailyDigestSnapshot}
              onSnapshotOpen={loadDigestSnapshot}
              onSnapshotDelete={deleteDailyDigestSnapshot}
              onSnapshotFeedback={updateDailyDigestSnapshotFeedback}
            />
          ) : activeModule === "stocks" ? (
            <section className="module-stack">
              {stockWatchlistPanel}
              {companyWatchlistPanel}
              {rankedFeedPanel}
            </section>
          ) : activeModule === "products" ? (
            <section className="module-stack">
              {productWatchlistPanel}
              {rankedFeedPanel}
            </section>
          ) : activeModule === "chinese" ? (
            <section className="module-stack">
              {chineseSocialPanel}
              {rankedFeedPanel}
            </section>
          ) : activeModule === "trends" ? (
            <section className="module-stack">
              {topicWatchlistPanel}
              {rankedFeedPanel}
            </section>
          ) : activeModule === "research" ? (
            <section className="module-stack">
              {researchReviewPanel}
              {rankedFeedPanel}
            </section>
          ) : activeModule === "submit" ? (
            <section className="module-stack">{manualSubmissionPanel}</section>
          ) : (
            rankedFeedPanel
          )}

          <aside className="stack">
            {activeModule === "settings" ? null : systemStatusPanel}
            {activeModule === "settings" ? null : rankingPreferencesPanel}
            {activeModule === "alerts" ? null : (
              <div id="alerts-workflow">
                <AlertPanel
                  alerts={alerts}
                  rules={alertRules}
                  includeDismissed={alertIncludeDismissed}
                  busyAlertId={busyAlertId}
                  busyAlertRuleId={busyAlertRuleId}
                  busyGenerate={busyAlertGenerate}
                  ruleName={alertRuleName}
                  ruleCategory={alertRuleCategory}
                  ruleTickers={alertRuleTickers}
                  ruleTopics={alertRuleTopics}
                  ruleImportance={alertRuleImportance}
                  ruleStockImpact={alertRuleStockImpact}
                  ruleSeverity={alertRuleSeverity}
                  disabled={loadState !== "idle"}
                  onDismiss={dismissAlert}
                  onFeedback={updateAlertFeedback}
                  onGenerate={generateDashboardAlerts}
                  onIncludeDismissedChange={setAlertIncludeDismissed}
                  onRuleToggle={toggleAlertRule}
                  onRuleSnooze={snoozeAlertRule}
                  onRuleUpdate={updateAlertRuleDetails}
                  onRuleDelete={deleteAlertRule}
                  onRuleNameChange={setAlertRuleName}
                  onRuleCategoryChange={setAlertRuleCategory}
                  onRuleTickersChange={setAlertRuleTickers}
                  onRuleTopicsChange={setAlertRuleTopics}
                  onRuleImportanceChange={setAlertRuleImportance}
                  onRuleStockImpactChange={setAlertRuleStockImpact}
                  onRuleSeverityChange={setAlertRuleSeverity}
                  onRuleSubmit={submitAlertRule}
                />
              </div>
            )}
            {activeModule === "digest" ? null : (
              <div id="digest-workflow">
                <DailyDigestPanel
                  digest={digest}
                  snapshots={digestSnapshots}
                  digestDate={digestDateDraft}
                  activeSnapshotId={activeDigestSnapshot?.id ?? null}
                  generationElapsedMs={lastDigestGenerationMs}
                  busySnapshotId={busyDigestSnapshotId}
                  busyGenerate={busyDigestGenerate}
                  busyCopy={busyDigestCopy}
                  busyDownload={busyDigestDownload}
                  busyEmail={busyDigestEmail}
                  busySave={busyDigestSave}
                  onDigestDateChange={updateDigestDateDraft}
                  onGenerate={generateDailyDigest}
                  onCopy={copyDailyDigest}
                  onDownload={downloadDailyDigest}
                  onEmail={emailDailyDigest}
                  onSave={saveDailyDigestSnapshot}
                  onSnapshotOpen={loadDigestSnapshot}
                  onSnapshotDelete={deleteDailyDigestSnapshot}
                  onSnapshotFeedback={updateDailyDigestSnapshotFeedback}
                />
              </div>
            )}
            {activeModule === "saved" ? null : (
              <SavedItemsPanel
                items={savedItems.slice(0, 8)}
                busyItemId={busyItemId}
                busyDetailItemId={busyDetailItemId}
                busyMetadataItemId={busyMetadataItemId}
                busyExport={busySavedExport}
                busyDownload={busySavedDownload}
                selectedDetail={selectedFeedDetail}
                onCopyExport={copySavedItemsExport}
                onDownloadExport={downloadSavedItemsExport}
                onDetail={loadFeedDetail}
                onManualTagFilter={applySavedManualTagFilter}
                onPersonalMetadataSave={saveFeedItemPersonalMetadata}
                onReadToggle={(item) =>
                  updateFeedAction(item.id, item.is_read ? "mark-unread" : "mark-read")
                }
                onUnsave={(itemId) => updateFeedAction(itemId, "unsave")}
              />
            )}
            <HiddenItemsPanel
              items={hiddenItems.slice(0, 8)}
              busyItemId={busyItemId}
              onUnhide={(itemId) => updateFeedAction(itemId, "unhide")}
              onDelete={deleteFeedItem}
            />
            {activeModule === "chinese" ? null : chineseSocialPanel}
            {activeModule === "clusters" ? null : (
              <EventClusterPanel
                clusters={eventClusters}
                selectedCluster={selectedEventCluster}
                busyClusterKey={busyClusterKey}
                busyClusterExplanationKey={busyClusterExplanationKey}
                explanations={clusterExplanations}
                limit={5}
                onSelectCluster={loadEventCluster}
                onExplainCluster={explainEventCluster}
              />
            )}
            {activeModule === "submit" ? null : manualSubmissionPanel}
            {activeModule === "stocks" ? null : stockWatchlistPanel}
            {activeModule === "stocks" ? null : companyWatchlistPanel}
            {activeModule === "trends" ? null : topicWatchlistPanel}
            {activeModule === "products" ? null : productWatchlistPanel}
            {activeModule === "sources" ? null : sourceHealthPanel}
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
  languagePreferences,
  disabled,
  busy,
  onDraftChange,
  onPreferredSourcesChange,
  onBlockedSourcesChange,
  onLanguagePreferencesChange,
  onReset,
  onSave,
}: {
  preferences: UserPreferences | null;
  draft: RankingWeights;
  preferredSources: string;
  blockedSources: string;
  languagePreferences: string;
  disabled: boolean;
  busy: boolean;
  onDraftChange: (key: keyof RankingWeights, value: number) => void;
  onPreferredSourcesChange: (value: string) => void;
  onBlockedSourcesChange: (value: string) => void;
  onLanguagePreferencesChange: (value: string) => void;
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
          <label className="weight-field">
            <span className="field-label">Languages</span>
            <input
              className="field"
              value={languagePreferences}
              onChange={(event) => onLanguagePreferencesChange(event.target.value)}
              placeholder="en, zh"
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

function SchedulerStatusPanel({
  schedule,
  disabled,
  busy,
  onRunCycle,
}: {
  schedule: IngestionScheduleStatus | null;
  disabled: boolean;
  busy: boolean;
  onRunCycle: () => void;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Scheduler</h2>
        <CalendarDays size={16} aria-hidden="true" />
      </div>
      <div className="digest-panel">
        {schedule ? (
          <>
            <div className="readiness-grid setup-summary-grid">
              <ReadinessMetric
                label="Mode"
                value={schedule.mode === "forever" ? "automatic" : "manual"}
              />
              <ReadinessMetric label="Interval" value={`${schedule.interval_minutes}m`} />
              <ReadinessMetric
                label="Next Cycle"
                value={schedule.next_cycle_at ? formatDate(schedule.next_cycle_at) : "manual"}
              />
              <ReadinessMetric
                label="Digest"
                value={schedule.digest_snapshot_fresh ? "fresh" : "needs save"}
              />
            </div>
            <div className="readiness-grid setup-summary-grid">
              <ReadinessMetric
                label="Digest Target"
                value={`${schedule.digest_target_hour_utc}:00 UTC`}
              />
              <ReadinessMetric
                label="Next Target"
                value={formatDate(schedule.next_digest_target_at)}
              />
              <ReadinessMetric
                label="Latest Run"
                value={
                  schedule.latest_source_run_at
                    ? formatDate(schedule.latest_source_run_at)
                    : "none"
                }
              />
              <ReadinessMetric label="Due Custom" value={schedule.due_custom_source_count} />
            </div>
            <div className="badges">
              {schedule.built_in_jobs.slice(0, 6).map((job) => (
                <span className="badge" key={job.name}>
                  {job.name}
                </span>
              ))}
              {schedule.due_custom_sources.slice(0, 4).map((source) => (
                <span className="badge stock" key={source.name}>
                  {source.name}
                </span>
              ))}
            </div>
            <div className="summary scheduler-command">{schedule.command_hint}</div>
            <div className="toolbar">
              <button
                className="button primary"
                onClick={onRunCycle}
                disabled={disabled || busy}
                type="button"
                title="Run full ingestion cycle and save a digest snapshot now"
              >
                {busy ? <Loader2 className="spin" size={16} /> : <DatabaseZap size={16} />}
                Run Cycle
              </button>
            </div>
          </>
        ) : (
          <div className="empty-state">Scheduler status is loading.</div>
        )}
      </div>
    </section>
  );
}

function SettingsBackupPanel({
  disabled,
  busyBackup,
  busyRestore,
  onDownload,
  onRestore,
}: {
  disabled: boolean;
  busyBackup: boolean;
  busyRestore: boolean;
  onDownload: () => void;
  onRestore: (file: File | null) => void;
}) {
  const inputId = "settings-backup-file";
  const busy = busyBackup || busyRestore;
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Settings Backup</h2>
        <FileText size={16} aria-hidden="true" />
      </div>
      <div className="digest-panel">
        <div className="digest-meta">
          <span>Preferences, watchlists, sources, alert rules</span>
          <span>JSON</span>
        </div>
        <div className="toolbar">
          <button
            className="button"
            onClick={onDownload}
            disabled={disabled || busy}
            type="button"
            title="Download local SignalLens settings as JSON"
          >
            {busyBackup ? <Loader2 className="spin" size={16} /> : <Download size={16} />}
            Download Backup
          </button>
          <label
            className={`button ${disabled || busy ? "disabled" : ""}`}
            htmlFor={inputId}
            title="Restore SignalLens settings from a JSON backup"
          >
            {busyRestore ? <Loader2 className="spin" size={16} /> : <FileText size={16} />}
            Restore Backup
          </label>
          <input
            id={inputId}
            type="file"
            accept="application/json,.json"
            disabled={disabled || busy}
            style={{ display: "none" }}
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              onRestore(file);
              event.target.value = "";
            }}
          />
        </div>
      </div>
    </section>
  );
}

function ResearchReviewPanel({ items }: { items: FeedItem[] }) {
  const researchItems = items.filter((item) =>
    ["research", "benchmark_evaluation"].includes(item.category),
  );
  const sourceCount = new Set(researchItems.map((item) => item.source_name)).size;
  const benchmarkCount = researchItems.filter((item) => item.category === "benchmark_evaluation")
    .length;
  const insightCount = researchItems.filter((item) => parseResearchInsights(item)).length;
  const technologies = uniqueLabels(researchItems.flatMap((item) => item.technologies)).slice(0, 10);
  const topics = uniqueLabels(researchItems.flatMap((item) => item.topics)).slice(0, 10);
  const topItems = [...researchItems]
    .sort(
      (left, right) =>
        right.importance_score + right.novelty_score - (left.importance_score + left.novelty_score),
    )
    .slice(0, 6);

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Research Review</h2>
        <span className="small-muted">{researchItems.length} items</span>
      </div>

      <div className="score-grid">
        <div className="score-cell">
          <span className="score-label">Papers</span>
          <span className="score-value">
            {researchItems.filter((item) => item.category === "research").length}
          </span>
        </div>
        <div className="score-cell">
          <span className="score-label">Benchmarks</span>
          <span className="score-value">{benchmarkCount}</span>
        </div>
        <div className="score-cell">
          <span className="score-label">Sources</span>
          <span className="score-value">{sourceCount}</span>
        </div>
        <div className="score-cell">
          <span className="score-label">Structured</span>
          <span className="score-value">{insightCount}</span>
        </div>
      </div>

      <div className="badges">
        {technologies.map((technology) => (
          <span className="badge" key={`research-technology:${technology}`}>
            {technology}
          </span>
        ))}
        {topics.map((topic) => (
          <span className="badge" key={`research-topic:${topic}`}>
            {topic}
          </span>
        ))}
      </div>

      <div className="digest-panel">
        {topItems.length ? (
          topItems.map((item) => {
            const insights = parseResearchInsights(item);
            return (
              <div className="digest-section" key={item.id}>
                <div className="digest-section-title">
                  {item.source_name}
                  {item.published_at ? ` · ${formatDate(item.published_at)}` : ""}
                </div>
                <a className="digest-link" href={item.url} target="_blank" rel="noreferrer">
                  {item.title}
                </a>
                <div className="badges">
                  <span className={`badge ${item.category === "research" ? "research" : ""}`}>
                    {formatCategoryLabel(item.category)}
                  </span>
                  {item.technologies.slice(0, 4).map((technology) => (
                    <span className="badge" key={`${item.id}:technology:${technology}`}>
                      {technology}
                    </span>
                  ))}
                </div>
                {insights ? (
                  <ResearchInsightsPanel insights={insights} compact />
                ) : item.summary_short || item.summary_detailed ? (
                  <div className="summary">{item.summary_short ?? item.summary_detailed}</div>
                ) : null}
                <div className="toolbar">
                  <a className="button secondary" href={item.url} target="_blank" rel="noreferrer">
                    <ExternalLink size={16} />
                    Open
                  </a>
                </div>
              </div>
            );
          })
        ) : (
          <div className="empty-state">No research signals loaded.</div>
        )}
      </div>
    </section>
  );
}

function ChineseSocialPanel({ items, limit }: { items: FeedItem[]; limit?: number }) {
  const chineseItems = items.filter(
    (item) => item.category === "social_trend" || item.language === "zh",
  );
  const visibleItems = limit ? chineseItems.slice(0, limit) : chineseItems;
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Chinese Social Trends</h2>
        <span className="small-muted">{chineseItems.length} items</span>
      </div>
      <div className="digest-panel">
        {visibleItems.length ? (
          visibleItems.map((item) => (
            <div className="digest-section" key={item.id}>
              <div className="digest-section-title">
                {item.source_name} {item.published_at ? `· ${formatDate(item.published_at)}` : ""}
              </div>
              <a className="digest-link" href={item.url} target="_blank" rel="noreferrer">
                {item.title}
              </a>
              <div className="badges">
                {item.subcategory?.includes("social_keyword") ? (
                  <span className="badge muted-badge">experimental</span>
                ) : null}
                {item.products.slice(0, 3).map((product) => (
                  <span className="badge" key={product}>
                    {product}
                  </span>
                ))}
                {item.topics.slice(0, 4).map((topic) => (
                  <span className="badge" key={topic}>
                    {topic}
                  </span>
                ))}
              </div>
              {item.summary_detailed ? <div className="summary">{item.summary_detailed}</div> : null}
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
  qualityMetrics,
  mvpChecklist,
  busyCopy,
  disabled,
  onCopyMissingEnv,
  onQualityFindingAction,
  onMvpChecklistAction,
}: {
  status: SystemStatus | null;
  itemCount: number;
  sourceCount: number;
  enabledSourceCount: number;
  alertCount: number;
  watchlistCount: number;
  qualityMetrics: QualityMetrics | null;
  mvpChecklist: MvpChecklistItem[] | null;
  busyCopy: boolean;
  disabled: boolean;
  onCopyMissingEnv: () => void;
  onQualityFindingAction: (finding: QualityFinding) => void;
  onMvpChecklistAction: (item: MvpChecklistItem) => void;
}) {
  const integrationRows: Array<[string, boolean]> = status
    ? [
        ["Kimi", status.integrations.kimi_coding_api],
        ["GitHub", status.integrations.github_api],
        ["Alpha Vantage", status.integrations.alpha_vantage_api],
        ["SEC", status.integrations.sec_user_agent],
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
                <div className="small-muted">
                  {status.llm_base_url || "no endpoint"} ·{" "}
                  {formatLlmApiFormat(status.llm_api_format)}
                </div>
              </div>
              <div className="readiness-actions">
                {status.missing_env_template ? (
                  <button
                    className="button"
                    onClick={onCopyMissingEnv}
                    disabled={busyCopy}
                    type="button"
                  >
                    {busyCopy ? <Loader2 className="spin" size={16} /> : <FileText size={16} />}
                    Copy .env
                  </button>
                ) : null}
                <span className={`badge ${status.llm_configured ? "" : "muted-badge"}`}>
                  {status.llm_configured ? "LLM ready" : "LLM key missing"}
                </span>
              </div>
            </div>
            <div className="readiness-grid">
              <ReadinessMetric label="Items" value={itemCount} />
              <ReadinessMetric label="Sources" value={`${enabledSourceCount}/${sourceCount}`} />
              <ReadinessMetric label="Alerts" value={alertCount} />
              <ReadinessMetric label="Watchlist" value={watchlistCount} />
            </div>
            <div className="readiness-grid setup-summary-grid">
              <ReadinessMetric
                label="Core"
                value={
                  status.setup_summary.core_ready
                    ? "ready"
                    : `${status.setup_summary.core_missing} missing`
                }
              />
              <ReadinessMetric
                label="Recommended"
                value={`${status.setup_summary.recommended_missing} missing`}
              />
              <ReadinessMetric
                label="Optional"
                value={`${status.setup_summary.optional_missing} missing`}
              />
              <ReadinessMetric
                label="Setup"
                value={`${status.setup_summary.configured}/${status.setup_summary.total}`}
              />
            </div>
            <PrdMvpChecklist
              items={
                mvpChecklist ??
                buildPrdMvpChecklist({
                  status,
                  qualityMetrics,
                  itemCount,
                  sourceCount,
                  enabledSourceCount,
                  alertCount,
                  watchlistCount,
                })
              }
              disabled={disabled}
              onAction={onMvpChecklistAction}
            />
            {qualityMetrics ? (
              <>
                <div className="digest-section-title">
                  Quality Metrics · {qualityMetrics.window_days}d
                </div>
                <div className="readiness-grid setup-summary-grid">
                  <ReadinessMetric
                    label="Relevant"
                    value={formatQualityPercent(qualityMetrics.relevance_precision_proxy)}
                  />
                  <ReadinessMetric
                    label="Duplicates"
                    value={formatQualityPercent(qualityMetrics.duplicate_rate)}
                  />
                  <ReadinessMetric
                    label="Summaries"
                    value={formatQualityPercent(qualityMetrics.summary_coverage)}
                  />
                  <ReadinessMetric
                    label="Summary Quality"
                    value={formatQualityPercent(qualityMetrics.summary_quality_proxy)}
                  />
                  <ReadinessMetric
                    label="Modules"
                    value={`${qualityMetrics.covered_module_count}/5`}
                  />
                  <ReadinessMetric
                    label="Classified"
                    value={formatQualityPercent(qualityMetrics.classification_coverage)}
                  />
                  <ReadinessMetric
                    label="Recent Src"
                    value={`${qualityMetrics.recent_source_count} · ${formatQualityPercent(qualityMetrics.dominant_source_share)}`}
                  />
                  <ReadinessMetric
                    label="Trusted"
                    value={formatQualityPercent(qualityMetrics.trusted_source_coverage)}
                  />
                  <ReadinessMetric
                    label="Facets"
                    value={formatQualityPercent(qualityMetrics.search_facet_coverage)}
                  />
                  <ReadinessMetric
                    label="Source Fail"
                    value={formatQualityPercent(qualityMetrics.source_failure_rate)}
                  />
                </div>
                <div className="readiness-grid setup-summary-grid">
                  <ReadinessMetric label="High Value" value={qualityMetrics.high_value_item_count} />
                  <ReadinessMetric
                    label="High Value/Day"
                    value={qualityMetrics.high_value_items_per_day.toFixed(2)}
                  />
                  <ReadinessMetric
                    label="Needs Summary"
                    value={qualityMetrics.high_value_unsummarized_count}
                  />
                  <ReadinessMetric label="Thin Summaries" value={qualityMetrics.thin_summary_count} />
                  <ReadinessMetric
                    label="Save/Hide"
                    value={
                      qualityMetrics.save_hide_ratio === null
                        ? `${qualityMetrics.save_count}/0`
                        : qualityMetrics.save_hide_ratio.toFixed(2)
                    }
                  />
                  <ReadinessMetric
                    label="Feedback"
                    value={qualityMetrics.feedback_action_count}
                  />
                  <ReadinessMetric
                    label="Item Useful"
                    value={
                      qualityMetrics.item_feedback_usefulness_rate === null
                        ? `${qualityMetrics.item_feedback_count} samples`
                        : `${formatQualityPercent(
                            qualityMetrics.item_feedback_usefulness_rate,
                          )} · ${qualityMetrics.item_feedback_count}`
                    }
                  />
                  <ReadinessMetric
                    label="Manual"
                    value={`${qualityMetrics.manual_submission_count} · ${qualityMetrics.manual_enrichment_gap_count} gap`}
                  />
                  <ReadinessMetric
                    label="Watchlists"
                    value={`${qualityMetrics.watchlist_area_count}/4`}
                  />
                  <ReadinessMetric
                    label="Read Later"
                    value={qualityMetrics.saved_read_later_count}
                  />
                  <ReadinessMetric
                    label="Alert Dismiss"
                    value={formatQualityPercent(qualityMetrics.alert_dismissal_rate)}
                  />
                  <ReadinessMetric
                    label="Alert Use"
                    value={
                      qualityMetrics.alert_usefulness_proxy === null
                        ? "none"
                        : formatQualityPercent(qualityMetrics.alert_usefulness_proxy)
                    }
                  />
                  <ReadinessMetric
                    label="Alert Feedback"
                    value={
                      qualityMetrics.alert_feedback_usefulness_rate === null
                        ? `${qualityMetrics.alert_feedback_count} samples`
                        : `${formatQualityPercent(
                            qualityMetrics.alert_feedback_usefulness_rate,
                          )} · ${qualityMetrics.alert_feedback_count}`
                    }
                  />
                  <ReadinessMetric label="Digests" value={qualityMetrics.digest_snapshot_count} />
                  <ReadinessMetric
                    label="Digest Use"
                    value={formatQualityPercent(qualityMetrics.digest_usefulness_proxy)}
                  />
                  <ReadinessMetric
                    label="Digest Feedback"
                    value={
                      qualityMetrics.digest_feedback_usefulness_rate === null
                        ? `${qualityMetrics.digest_feedback_count} samples`
                        : `${formatQualityPercent(
                            qualityMetrics.digest_feedback_usefulness_rate,
                          )} · ${qualityMetrics.digest_feedback_count}`
                    }
                  />
                  <ReadinessMetric
                    label="Latest Digest"
                    value={qualityMetrics.latest_digest_snapshot_date ?? "none"}
                  />
                  <ReadinessMetric
                    label="Digest Age"
                    value={
                      qualityMetrics.latest_digest_age_days === null
                        ? "none"
                        : `${qualityMetrics.latest_digest_age_days}d`
                    }
                  />
                  <ReadinessMetric
                    label="Digest Items"
                    value={qualityMetrics.latest_digest_snapshot_item_count ?? "none"}
                  />
                  <ReadinessMetric
                    label="Latest Price"
                    value={qualityMetrics.latest_stock_price_date ?? "none"}
                  />
                  <ReadinessMetric
                    label="Price Age"
                    value={
                      qualityMetrics.latest_stock_price_age_days === null
                        ? "none"
                        : `${qualityMetrics.latest_stock_price_age_days}d`
                    }
                  />
                </div>
                <div className="readiness-grid setup-summary-grid">
                  <ReadinessMetric label="LLM Calls" value={qualityMetrics.llm_call_count} />
                  <ReadinessMetric
                    label="Calls/Item"
                    value={qualityMetrics.llm_calls_per_recent_item.toFixed(2)}
                  />
                  <ReadinessMetric
                    label="Input Tok"
                    value={formatCompactNumber(qualityMetrics.llm_input_tokens)}
                  />
                  <ReadinessMetric
                    label="Total Tok"
                    value={formatCompactNumber(qualityMetrics.llm_total_tokens)}
                  />
                  <ReadinessMetric
                    label="LLM Cost"
                    value={
                      qualityMetrics.llm_pricing_configured
                        ? formatUsd(qualityMetrics.llm_estimated_cost_usd)
                        : "pricing off"
                    }
                  />
                  <ReadinessMetric
                    label="Monthly Est"
                    value={
                      qualityMetrics.llm_pricing_configured
                        ? formatUsd(qualityMetrics.llm_projected_monthly_cost_usd)
                        : "pricing off"
                    }
                  />
                  <ReadinessMetric
                    label="Budget"
                    value={
                      qualityMetrics.llm_monthly_budget_usd > 0 &&
                      qualityMetrics.llm_monthly_budget_usage !== null
                        ? formatQualityPercent(qualityMetrics.llm_monthly_budget_usage)
                        : "not set"
                    }
                  />
                  <ReadinessMetric
                    label="Cost/Item"
                    value={
                      qualityMetrics.llm_pricing_configured &&
                      qualityMetrics.llm_estimated_cost_per_recent_item_usd !== null
                        ? formatUsd(qualityMetrics.llm_estimated_cost_per_recent_item_usd)
                        : "none"
                    }
                  />
                  <ReadinessMetric
                    label="Cost/Digest"
                    value={
                      qualityMetrics.llm_pricing_configured &&
                      qualityMetrics.llm_estimated_cost_per_digest_usd !== null
                        ? formatUsd(qualityMetrics.llm_estimated_cost_per_digest_usd)
                        : "none"
                    }
                  />
                  <ReadinessMetric
                    label="Cost/Alert"
                    value={
                      qualityMetrics.llm_pricing_configured &&
                      qualityMetrics.llm_estimated_cost_per_active_alert_usd !== null
                        ? formatUsd(qualityMetrics.llm_estimated_cost_per_active_alert_usd)
                        : "none"
                    }
                  />
                </div>
                <div className="readiness-grid setup-summary-grid">
                  <ReadinessMetric
                    label="API Calls"
                    value={qualityMetrics.source_api_call_count}
                  />
                  <ReadinessMetric
                    label="API/Item"
                    value={qualityMetrics.source_api_calls_per_recent_item.toFixed(2)}
                  />
                  <ReadinessMetric
                    label="API Cost"
                    value={
                      qualityMetrics.source_api_pricing_configured
                        ? formatUsd(qualityMetrics.source_api_estimated_cost_usd)
                        : "free/default"
                    }
                  />
                  <ReadinessMetric
                    label="API Monthly"
                    value={
                      qualityMetrics.source_api_pricing_configured
                        ? formatUsd(qualityMetrics.source_api_projected_monthly_cost_usd)
                        : "free/default"
                    }
                  />
                  <ReadinessMetric
                    label="API Budget"
                    value={
                      qualityMetrics.source_api_monthly_budget_usd > 0 &&
                      qualityMetrics.source_api_monthly_budget_usage !== null
                        ? formatQualityPercent(qualityMetrics.source_api_monthly_budget_usage)
                        : "not set"
                    }
                  />
                  <ReadinessMetric
                    label="API/Item Cost"
                    value={
                      qualityMetrics.source_api_pricing_configured &&
                      qualityMetrics.source_api_estimated_cost_per_recent_item_usd !== null
                        ? formatUsd(qualityMetrics.source_api_estimated_cost_per_recent_item_usd)
                        : "none"
                    }
                  />
                  <ReadinessMetric
                    label="API/Digest"
                    value={
                      qualityMetrics.source_api_pricing_configured &&
                      qualityMetrics.source_api_estimated_cost_per_digest_usd !== null
                        ? formatUsd(qualityMetrics.source_api_estimated_cost_per_digest_usd)
                        : "none"
                    }
                  />
                  <ReadinessMetric
                    label="API/Alert"
                    value={
                      qualityMetrics.source_api_pricing_configured &&
                      qualityMetrics.source_api_estimated_cost_per_active_alert_usd !== null
                        ? formatUsd(qualityMetrics.source_api_estimated_cost_per_active_alert_usd)
                        : "none"
                    }
                  />
                </div>
                {qualityMetrics.quality_findings.length ? (
                  <div className="setup-list">
                    {qualityMetrics.quality_findings.slice(0, 5).map((finding) => (
                      <div className="setup-row" key={`${finding.title}:${finding.metric}`}>
                        <div>
                          <div className="setup-title-row">
                            <div className="digest-section-title">{finding.title}</div>
                            <span
                              className={`badge ${qualityFindingBadgeClass(finding.severity)}`}
                            >
                              {finding.severity}
                            </span>
                          </div>
                          <div className="small-muted">{finding.recommendation}</div>
                          {finding.action_label && finding.action_module ? (
                            <button
                              className="button"
                              onClick={() => onQualityFindingAction(finding)}
                              disabled={disabled}
                              type="button"
                            >
                              {finding.action_label}
                            </button>
                          ) : null}
                        </div>
                        <span className="badge muted-badge">{finding.metric}</span>
                      </div>
                    ))}
                  </div>
                ) : null}
                {qualityMetrics.llm_operation_usage.length ? (
                  <div className="setup-list">
                    {qualityMetrics.llm_operation_usage.slice(0, 4).map((operation) => (
                      <div className="setup-row" key={operation.operation}>
                        <div>
                          <div className="digest-section-title">
                            {formatLlmOperationLabel(operation.operation)}
                          </div>
                          <div className="small-muted">
                            {operation.call_count} calls | {formatCompactNumber(operation.input_tokens)} in |{" "}
                            {formatCompactNumber(operation.output_tokens)} out
                          </div>
                        </div>
                        <span className="badge">
                          {qualityMetrics.llm_pricing_configured
                            ? `${formatUsd(operation.estimated_cost_usd)} · `
                            : ""}
                          {formatCompactNumber(operation.total_tokens)} tok
                        </span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </>
            ) : null}
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

function PrdMvpChecklist({
  items,
  disabled,
  onAction,
}: {
  items: MvpChecklistItem[];
  disabled: boolean;
  onAction: (item: MvpChecklistItem) => void;
}) {
  return (
    <div className="mvp-checklist">
      <div className="digest-section-title">PRD MVP Checklist</div>
      <div className="mvp-checklist-grid">
        {items.map((item) => (
          <div className="mvp-checklist-row" key={item.key}>
            <div>
              <div className="setup-title-row">
                <div className="digest-section-title">{item.label}</div>
                <span className={`badge ${mvpChecklistBadgeClass(item.status)}`}>
                  {formatMvpChecklistStatus(item.status)}
                </span>
              </div>
              <div className="small-muted">{item.note}</div>
              {item.actionLabel ? (
                <button
                  className="button mvp-checklist-action"
                  disabled={disabled}
                  onClick={() => onAction(item)}
                  type="button"
                >
                  {item.actionLabel}
                </button>
              ) : null}
            </div>
            <span className="badge muted-badge">{item.metric}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatQualityPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatUsd(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return "$0";
  }
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: value < 0.01 ? 4 : 2,
    maximumFractionDigits: value < 0.01 ? 4 : 2,
  }).format(value);
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return "0s";
  }
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return remainingSeconds ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
}

function formatDigestSnapshotStatus(result: ScheduledCycleResponse): string {
  if (result.saved_digest_date) return result.saved_digest_date;
  return result.digest_snapshot_status.replaceAll("_", " ");
}

function formatLlmOperationLabel(operation: string): string {
  return operation
    .split("_")
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function formatLlmApiFormat(format: string): string {
  return format
    .split(/[_-]/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function qualityFindingBadgeClass(severity: QualityFinding["severity"]): string {
  if (severity === "critical" || severity === "warning") {
    return "alert-badge";
  }
  return "muted-badge";
}

function qualityFindingTargetId(finding: QualityFinding): string | undefined {
  if (finding.action_operation === "cycle") {
    return "source-health-workflow";
  }
  if (
    finding.action_operation === "llm:preview" ||
    finding.action_operation === "llm:classify" ||
    finding.action_operation === "llm:summarize" ||
    finding.action_operation === "demo-data:seed"
  ) {
    return "ranked-feed-workflow";
  }
  if (finding.action_operation === "digest:save-snapshot") {
    return "digest-workflow";
  }
  if (finding.action_operation === "stock-prices:refresh") {
    return "stock-watchlist-workflow";
  }
  if (finding.action_operation === "alerts:generate") {
    return "alerts-workflow";
  }
  if (finding.action_module === "sources") {
    return "source-health-workflow";
  }
  if (finding.action_module === "digest") {
    return "digest-workflow";
  }
  if (finding.action_module === "stocks") {
    return "stock-watchlist-workflow";
  }
  if (finding.action_module === "settings") {
    return "settings-workflow";
  }
  if (finding.action_module === "dashboard") {
    return "system-readiness-workflow";
  }
  return undefined;
}

function mapMvpChecklistResponse(response: MvpChecklistResponse): MvpChecklistItem[] {
  return response.items.map((item) => ({
    key: item.key,
    label: item.label,
    status: item.status,
    metric: item.metric,
    note: item.note,
    actionLabel: item.action_label ?? undefined,
    actionModule: item.action_module ?? undefined,
    actionOperation: item.action_operation ?? undefined,
    actionSourceFilter: item.action_source_filter ?? undefined,
    actionTargetId: item.action_target_id ?? undefined,
  }));
}

function mvpChecklistBadgeClass(status: MvpChecklistItem["status"]): string {
  if (status === "ready") {
    return "success-badge";
  }
  if (status === "partial") {
    return "warning-badge";
  }
  return "alert-badge";
}

function formatMvpChecklistStatus(status: MvpChecklistItem["status"]): string {
  if (status === "ready") {
    return "ready";
  }
  if (status === "partial") {
    return "partial";
  }
  return "needs action";
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

function buildPrdMvpChecklist({
  status,
  qualityMetrics,
  itemCount,
  sourceCount,
  enabledSourceCount,
  alertCount,
  watchlistCount,
}: {
  status: SystemStatus;
  qualityMetrics: QualityMetrics | null;
  itemCount: number;
  sourceCount: number;
  enabledSourceCount: number;
  alertCount: number;
  watchlistCount: number;
}): MvpChecklistItem[] {
  const recentItems = qualityMetrics?.recent_item_count ?? itemCount;
  const coveredModules = qualityMetrics?.covered_module_count ?? 0;
  const recentSourceCount = qualityMetrics?.recent_source_count ?? 0;
  const classificationCoverage = qualityMetrics?.classification_coverage ?? 0;
  const summaryCoverage = qualityMetrics?.summary_coverage ?? 0;
  const watchlistAreaCount = qualityMetrics?.watchlist_area_count ?? 0;
  const stockWatchlistCount = qualityMetrics?.stock_watchlist_count ?? 0;
  const latestStockPriceDate = qualityMetrics?.latest_stock_price_date ?? null;
  const latestDigestAgeDays = qualityMetrics?.latest_digest_age_days ?? null;
  const digestSnapshotCount = qualityMetrics?.digest_snapshot_count ?? 0;
  const manualSubmissionCount = qualityMetrics?.manual_submission_count ?? 0;
  const searchFacetCoverage = qualityMetrics?.search_facet_coverage ?? 0;
  const llmCallCount = qualityMetrics?.llm_call_count ?? 0;
  const dismissedAlertCount = qualityMetrics?.dismissed_alert_count ?? 0;

  return [
    {
      key: "dashboard-feed",
      label: "Ranked Dashboard",
      status:
        recentItems > 0 && coveredModules >= 3
          ? "ready"
          : recentItems > 0
            ? "partial"
            : "needs_action",
      metric: `${recentItems} recent · ${coveredModules}/5 modules`,
      note:
        recentItems > 0
          ? "Feed data is available across the first-class PRD modules."
          : "Run a source cycle or seed demo data to populate the ranked feed.",
      actionLabel: recentItems > 0 ? "Open Dashboard" : "Seed Demo Data",
      actionModule: "dashboard",
      actionOperation: recentItems > 0 ? undefined : "demo-data:seed",
      actionTargetId: "ranked-feed-workflow",
    },
    {
      key: "source-ingestion",
      label: "Source Ingestion",
      status:
        enabledSourceCount >= 5 && recentSourceCount >= 3
          ? "ready"
          : enabledSourceCount > 0
            ? "partial"
            : "needs_action",
      metric: `${enabledSourceCount}/${sourceCount} enabled · ${recentSourceCount} recent`,
      note:
        enabledSourceCount > 0
          ? "Connectors are configured; recent diversity shows whether collection is broad enough."
          : "Enable followed sources before relying on daily collection.",
      actionLabel:
        enabledSourceCount > 0 && recentSourceCount < 3 ? "Run Full Cycle" : "Open Sources",
      actionModule: "sources",
      actionOperation:
        enabledSourceCount > 0 && recentSourceCount < 3 ? "cycle" : undefined,
      actionTargetId: "source-health-workflow",
    },
    {
      key: "llm-processing",
      label: "LLM Processing",
      status:
        status.llm_configured && classificationCoverage >= 0.7 && summaryCoverage >= 0.5
          ? "ready"
          : status.llm_configured || llmCallCount > 0
            ? "partial"
            : "needs_action",
      metric: `${formatQualityPercent(classificationCoverage)} classified · ${formatQualityPercent(summaryCoverage)} summarized`,
      note: status.llm_configured
        ? "Kimi is configured; coverage depends on running capped classify/summarize batches."
        : "Preview candidates without a key; add an LLM key before model-generated summaries.",
      actionLabel: "Preview LLM Batch",
      actionModule: "dashboard",
      actionOperation: "llm:preview",
      actionTargetId: "ranked-feed-workflow",
    },
    {
      key: "watchlists",
      label: "Personal Watchlists",
      status:
        watchlistAreaCount >= 4
          ? "ready"
          : watchlistCount > 0
            ? "partial"
            : "needs_action",
      metric: `${watchlistAreaCount}/4 areas · ${watchlistCount} rows`,
      note:
        watchlistCount > 0
          ? "Stock, company, topic, and product watchlists shape ranking and digest context."
          : "Seed or create watchlists so personalization has a profile to use.",
      actionLabel: "Open Watchlists",
      actionModule: "stocks",
      actionTargetId: "stock-watchlist-workflow",
    },
    {
      key: "stock-watchlist",
      label: "AI Stock Watchlist",
      status:
        stockWatchlistCount > 0 && latestStockPriceDate
          ? "ready"
          : stockWatchlistCount > 0
            ? "partial"
            : "needs_action",
      metric: `${stockWatchlistCount} tickers · ${latestStockPriceDate ?? "no price"}`,
      note:
        stockWatchlistCount > 0
          ? "Ticker monitoring is available; fresh prices improve market-context checks."
          : "Add or seed watched tickers before relying on stock signals.",
      actionLabel:
        stockWatchlistCount > 0 && !latestStockPriceDate ? "Refresh Prices" : "Open Stocks",
      actionModule: "stocks",
      actionOperation:
        stockWatchlistCount > 0 && !latestStockPriceDate ? "stock-prices:refresh" : undefined,
      actionTargetId: "stock-watchlist-workflow",
    },
    {
      key: "search",
      label: "Searchable Archive",
      status:
        recentItems > 0 && searchFacetCoverage >= 0.7
          ? "ready"
          : recentItems > 0
            ? "partial"
            : "needs_action",
      metric: `${formatQualityPercent(searchFacetCoverage)} faceted`,
      note:
        recentItems > 0
          ? "Facet coverage indicates whether search can filter by topics, tickers, sources, and tags."
          : "Search becomes useful after ingestion creates normalized items.",
      actionLabel:
        recentItems > 0 && searchFacetCoverage < 0.7
          ? "Preview LLM Batch"
          : "Open Dashboard",
      actionModule: "dashboard",
      actionOperation:
        recentItems > 0 && searchFacetCoverage < 0.7 ? "llm:preview" : undefined,
      actionTargetId: "ranked-feed-workflow",
    },
    {
      key: "daily-digest",
      label: "Daily Digest",
      status:
        latestDigestAgeDays !== null && latestDigestAgeDays <= 1
          ? "ready"
          : digestSnapshotCount > 0
            ? "partial"
            : "needs_action",
      metric:
        latestDigestAgeDays === null
          ? `${digestSnapshotCount} snapshots`
          : `${digestSnapshotCount} snapshots · ${latestDigestAgeDays}d old`,
      note:
        digestSnapshotCount > 0
          ? "A saved digest exists; morning readiness depends on keeping the snapshot fresh."
          : "Generate and save a digest snapshot to lock in a daily brief.",
      actionLabel:
        latestDigestAgeDays !== null && latestDigestAgeDays <= 1 ? "Open Digest" : "Save Digest",
      actionModule: "digest",
      actionOperation:
        latestDigestAgeDays !== null && latestDigestAgeDays <= 1
          ? undefined
          : "digest:save-snapshot",
      actionTargetId: "digest-workflow",
    },
    {
      key: "alerts",
      label: "Dashboard Alerts",
      status:
        alertCount > 0
          ? "ready"
          : dismissedAlertCount > 0
            ? "partial"
            : "needs_action",
      metric: `${alertCount} active`,
      note:
        alertCount > 0
          ? "Dashboard alert rules are producing active signals."
          : "Generate alerts after ingestion to validate stock, product, and trend rules.",
      actionLabel: alertCount > 0 ? "Open Alerts" : "Generate Alerts",
      actionModule: "alerts",
      actionOperation: alertCount > 0 ? undefined : "alerts:generate",
      actionTargetId: "alerts-workflow",
    },
    {
      key: "manual-submission",
      label: "Manual URL Submission",
      status: manualSubmissionCount > 0 ? "ready" : "partial",
      metric: `${manualSubmissionCount} recent`,
      note:
        manualSubmissionCount > 0
          ? "Recent manual submissions are flowing into the same feed pipeline."
          : "The submission flow is available; paste a URL when a source has no connector.",
      actionLabel: "Open Submission",
      actionModule: "submit",
      actionTargetId: "manual-submission-workflow",
    },
  ];
}

function AlertPanel({
  alerts,
  rules,
  includeDismissed,
  busyAlertId,
  busyAlertRuleId,
  busyGenerate,
  ruleName,
  ruleCategory,
  ruleTickers,
  ruleTopics,
  ruleImportance,
  ruleStockImpact,
  ruleSeverity,
  disabled,
  onDismiss,
  onFeedback,
  onGenerate,
  onIncludeDismissedChange,
  onRuleToggle,
  onRuleSnooze,
  onRuleUpdate,
  onRuleDelete,
  onRuleNameChange,
  onRuleCategoryChange,
  onRuleTickersChange,
  onRuleTopicsChange,
  onRuleImportanceChange,
  onRuleStockImpactChange,
  onRuleSeverityChange,
  onRuleSubmit,
}: {
  alerts: AlertItem[];
  rules: AlertRule[];
  includeDismissed: boolean;
  busyAlertId: number | null;
  busyAlertRuleId: number | null;
  busyGenerate: boolean;
  ruleName: string;
  ruleCategory: string;
  ruleTickers: string;
  ruleTopics: string;
  ruleImportance: string;
  ruleStockImpact: string;
  ruleSeverity: string;
  disabled: boolean;
  onDismiss: (alertId: number) => void;
  onFeedback: (alert: AlertItem, usefulnessFeedback: "useful" | "not_useful") => void;
  onGenerate: () => void;
  onIncludeDismissedChange: (value: boolean) => void;
  onRuleToggle: (rule: AlertRule) => void;
  onRuleSnooze: (rule: AlertRule) => void;
  onRuleUpdate: (rule: AlertRule, payload: Partial<Omit<AlertRule, "id">>) => void;
  onRuleDelete: (ruleId: number) => void;
  onRuleNameChange: (value: string) => void;
  onRuleCategoryChange: (value: string) => void;
  onRuleTickersChange: (value: string) => void;
  onRuleTopicsChange: (value: string) => void;
  onRuleImportanceChange: (value: string) => void;
  onRuleStockImpactChange: (value: string) => void;
  onRuleSeverityChange: (value: string) => void;
  onRuleSubmit: () => void;
}) {
  const [selectedRuleId, setSelectedRuleId] = useState<number | null>(null);
  const selectedRule = rules.find((rule) => rule.id === selectedRuleId) ?? rules[0] ?? null;
  const [ruleDraft, setRuleDraft] = useState<AlertRuleDraft>(() =>
    alertRuleToDraft(selectedRule),
  );

  useEffect(() => {
    setRuleDraft(alertRuleToDraft(selectedRule));
  }, [selectedRule]);

  const updateRuleDraft = (key: keyof AlertRuleDraft, value: string) => {
    setRuleDraft((current) => ({ ...current, [key]: value }));
  };

  const saveSelectedRule = () => {
    if (!selectedRule) {
      return;
    }
    onRuleUpdate(selectedRule, {
      name: ruleDraft.name.trim() || selectedRule.name,
      description: ruleDraft.description.trim() || null,
      category: ruleDraft.category.trim() || selectedRule.category,
      severity: ruleDraft.severity.trim() || selectedRule.severity,
      min_importance_score: parseBoundedScore(
        ruleDraft.min_importance_score,
        selectedRule.min_importance_score,
      ),
      min_stock_impact_score: parseBoundedScore(
        ruleDraft.min_stock_impact_score,
        selectedRule.min_stock_impact_score,
      ),
      tickers: splitTerms(ruleDraft.tickers),
      topics: splitTerms(ruleDraft.topics),
    });
  };

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Alerts</h2>
        <div className="table-actions">
          <button
            className={`button icon-button ${includeDismissed ? "active-icon-button" : ""}`}
            onClick={() => onIncludeDismissedChange(!includeDismissed)}
            disabled={disabled}
            title={includeDismissed ? "Show active alerts only" : "Show dismissed alert history"}
            aria-label={includeDismissed ? "Show active alerts only" : "Show dismissed alert history"}
            type="button"
          >
            <History size={16} />
          </button>
          <button
            className="button icon-button"
            onClick={onGenerate}
            disabled={disabled || busyGenerate}
            title="Generate alerts now"
            aria-label="Generate alerts now"
            type="button"
          >
            {busyGenerate ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
          </button>
          <BellRing size={16} aria-hidden="true" />
        </div>
      </div>
      <div className="form-panel compact-form alert-rule-form">
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
          {alertCategoryOptions.map((option) => (
            <option value={option.value} key={option.value}>
              {option.label}
            </option>
          ))}
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
          placeholder="Min importance"
          aria-label="Alert rule minimum importance"
        />
        <input
          className="field"
          value={ruleStockImpact}
          onChange={(event) => onRuleStockImpactChange(event.target.value)}
          placeholder="Stock min"
          aria-label="Alert rule minimum stock impact"
        />
        <select
          className="field"
          value={ruleSeverity}
          onChange={(event) => onRuleSeverityChange(event.target.value)}
          aria-label="Alert rule severity"
        >
          {alertSeverityOptions.map((option) => (
            <option value={option.value} key={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <button className="button primary" onClick={onRuleSubmit} disabled={disabled}>
          {disabled ? <Loader2 className="spin" size={16} /> : <Plus size={16} />}
          Add
        </button>
      </div>
      <div className="alert-rule-list">
        {rules.slice(0, 6).map((rule) => {
          const snoozed = isAlertRuleSnoozed(rule);
          return (
            <div
              className={`alert-rule-row ${rule.enabled && !snoozed ? "" : "muted"}`}
              key={rule.id}
            >
              <div>
                <button
                  className={`ticker-button ${selectedRule?.id === rule.id ? "active" : ""}`}
                  onClick={() => setSelectedRuleId(rule.id)}
                  type="button"
                >
                  {rule.name}
                </button>
                <div className="small-muted">
                  {rule.category} · {rule.severity} · min{" "}
                  {Math.round(rule.min_importance_score * 100)}
                  {rule.min_stock_impact_score > 0
                    ? ` · stock ${Math.round(rule.min_stock_impact_score * 100)}`
                    : ""}
                  {rule.tickers.length ? ` · ${rule.tickers.join(", ")}` : ""}
                  {snoozed && rule.snoozed_until
                    ? ` · snoozed until ${formatDate(rule.snoozed_until)}`
                    : ""}
                </div>
              </div>
              <div className="table-actions">
                <button
                  className={`button icon-button ${
                    rule.enabled && !snoozed ? "active-icon-button" : ""
                  }`}
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
                  className={`button icon-button ${snoozed ? "active-icon-button" : ""}`}
                  onClick={() => onRuleSnooze(rule)}
                  disabled={disabled || busyAlertRuleId === rule.id || !rule.enabled}
                  title={snoozed ? "Resume alert rule" : "Snooze alert rule for 24 hours"}
                  aria-label={snoozed ? "Resume alert rule" : "Snooze alert rule for 24 hours"}
                  type="button"
                >
                  {busyAlertRuleId === rule.id ? (
                    <Loader2 className="spin" size={16} />
                  ) : (
                    <CalendarDays size={16} />
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
          );
        })}
      </div>
      <AlertRuleDetailEditor
        rule={selectedRule}
        draft={ruleDraft}
        disabled={disabled || (selectedRule ? busyAlertRuleId === selectedRule.id : false)}
        onDraftChange={updateRuleDraft}
        onSave={saveSelectedRule}
      />
      <div className="alert-list">
        {alerts.length ? (
          alerts.map((alert) => (
            <article className={`alert-card severity-${alert.severity}`} key={alert.id}>
              <div className="alert-head">
                <div>
                  <div className="alert-title">{alert.title}</div>
                  <div className="small-muted">
                    {alert.severity} · {alert.status} · {formatDate(alert.created_at)}
                    {alert.usefulness_feedback
                      ? ` · ${formatAlertFeedback(alert.usefulness_feedback)}`
                      : ""}
                  </div>
                </div>
                <div className="table-actions">
                  <button
                    className={`button icon-button ${
                      alert.usefulness_feedback === "useful" ? "active-icon-button" : ""
                    }`}
                    onClick={() => onFeedback(alert, "useful")}
                    disabled={busyAlertId === alert.id}
                    title={
                      alert.usefulness_feedback === "useful"
                        ? "Clear useful feedback"
                        : "Mark alert useful"
                    }
                    aria-label={
                      alert.usefulness_feedback === "useful"
                        ? "Clear useful alert feedback"
                        : "Mark alert useful"
                    }
                    type="button"
                  >
                    {busyAlertId === alert.id ? (
                      <Loader2 className="spin" size={16} />
                    ) : (
                      <ThumbsUp size={16} />
                    )}
                  </button>
                  <button
                    className={`button icon-button ${
                      alert.usefulness_feedback === "not_useful" ? "active-icon-button" : ""
                    }`}
                    onClick={() => onFeedback(alert, "not_useful")}
                    disabled={busyAlertId === alert.id}
                    title={
                      alert.usefulness_feedback === "not_useful"
                        ? "Clear not useful feedback"
                        : "Mark alert not useful"
                    }
                    aria-label={
                      alert.usefulness_feedback === "not_useful"
                        ? "Clear not useful alert feedback"
                        : "Mark alert not useful"
                    }
                    type="button"
                  >
                    {busyAlertId === alert.id ? (
                      <Loader2 className="spin" size={16} />
                    ) : (
                      <ThumbsDown size={16} />
                    )}
                  </button>
                  {alert.status === "active" ? (
                  <button
                    className="button icon-button"
                    onClick={() => onDismiss(alert.id)}
                    disabled={busyAlertId === alert.id}
                    title="Dismiss alert"
                    aria-label="Dismiss alert"
                  >
                    {busyAlertId === alert.id ? (
                      <Loader2 className="spin" size={16} />
                    ) : (
                      <X size={16} />
                    )}
                  </button>
                  ) : (
                    <span className="badge muted-badge">dismissed</span>
                  )}
                </div>
              </div>
              <div className="summary">{alert.reason}</div>
              <AlertEvidenceSummary alert={alert} />
              <div className="badges">
                {alert.item.tickers.map((ticker) => (
                  <span className="badge stock" key={ticker}>
                    {ticker}
                  </span>
                ))}
                <span className="badge">{formatCategoryLabel(alert.item.category)}</span>
                {!alert.item.is_ai_related ? (
                  <span className="badge muted-badge">not AI-related</span>
                ) : null}
                {alert.item.market_impact_type !== "none" ? (
                  <span className="badge stock">
                    {formatMarketImpactLabel(alert.item.market_impact_type)}
                  </span>
                ) : null}
                {alert.item.category === "product" && alert.item.subcategory ? (
                  <span className="badge">{formatProductUseCaseLabel(alert.item.subcategory)}</span>
                ) : null}
                {alert.item.products.slice(0, 2).map((product) => (
                  <span className="badge" key={`alert-product:${alert.id}:${product}`}>
                    {product}
                  </span>
                ))}
              </div>
              <a className="digest-link" href={alert.item.url} target="_blank" rel="noreferrer">
                {alert.item.source_name}
              </a>
              <div className="small-muted">{alert.disclaimer}</div>
            </article>
          ))
        ) : (
          <div className="empty-state">
            {includeDismissed ? "No alert history." : "No active alerts."}
          </div>
        )}
      </div>
    </section>
  );
}

function AlertEvidenceSummary({ alert }: { alert: AlertItem }) {
  const item = alert.item;
  const rule = alert.rule;
  const itemSummary = item.summary_short || item.why_it_matters || item.summary_detailed;
  const matchedLabels = uniqueLabels([
    ...rule.tickers,
    ...rule.topics,
    ...item.tickers,
    ...item.topics.slice(0, 4),
    ...item.products.slice(0, 3),
  ]);

  return (
    <div className="alert-evidence-grid">
      <div className="alert-evidence-card">
        <div className="field-label">Matched Rule</div>
        <div className="alert-evidence-title">{rule.name}</div>
        <div className="small-muted">
          {formatCategoryLabel(rule.category)} · {rule.severity} · min{" "}
          {Math.round(rule.min_importance_score * 100)}
          {rule.min_stock_impact_score > 0
            ? ` · stock ${Math.round(rule.min_stock_impact_score * 100)}`
            : ""}
        </div>
      </div>
      <div className="alert-evidence-card">
        <div className="field-label">Source Evidence</div>
        <div className="alert-evidence-title">{item.source_name}</div>
        <div className="small-muted">
          {item.published_at ? formatDate(item.published_at) : "undated"} ·{" "}
          {formatCategoryLabel(item.category)}
        </div>
      </div>
      <div className="alert-evidence-card">
        <div className="field-label">Scores</div>
        <div className="alert-evidence-title">
          Importance {Math.round(item.importance_score * 100)}
        </div>
        <div className="small-muted">
          Relevance {Math.round(item.relevance_score * 100)} · Confidence{" "}
          {Math.round(item.classification_confidence * 100)} · Stock{" "}
          {Math.round(item.stock_impact_score * 100)}
        </div>
      </div>
      {itemSummary ? (
        <div className="alert-evidence-card wide">
          <div className="field-label">Item Summary</div>
          <div className="small-muted">{itemSummary}</div>
        </div>
      ) : null}
      {matchedLabels.length ? (
        <div className="alert-evidence-card wide">
          <div className="field-label">Matched Labels</div>
          <div className="badges">
            {matchedLabels.map((label) => (
              <span className="badge" key={`alert-evidence-${alert.id}-${label}`}>
                {label}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function AlertRuleDetailEditor({
  rule,
  draft,
  disabled,
  onDraftChange,
  onSave,
}: {
  rule: AlertRule | null;
  draft: AlertRuleDraft;
  disabled: boolean;
  onDraftChange: (key: keyof AlertRuleDraft, value: string) => void;
  onSave: () => void;
}) {
  if (!rule) {
    return <div className="empty-state">Select an alert rule to edit thresholds.</div>;
  }

  return (
    <div className="form-panel stock-detail-form">
      <div className="section-header">
        <div>
          <h3 className="section-title">{rule.name} details</h3>
          <div className="small-muted">
            {rule.enabled ? "enabled" : "disabled"}
            {rule.snoozed_until ? ` · snoozed until ${formatDate(rule.snoozed_until)}` : ""}
          </div>
        </div>
        <span className={`badge severity-${rule.severity}`}>{rule.severity}</span>
      </div>
      <div className="stock-detail-grid">
        <label className="weight-field">
          <span className="field-label">Name</span>
          <input
            className="field"
            value={draft.name}
            onChange={(event) => onDraftChange("name", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Category</span>
          <select
            className="field"
            value={draft.category}
            onChange={(event) => onDraftChange("category", event.target.value)}
            disabled={disabled}
          >
            {alertCategoryOptions.map((option) => (
              <option value={option.value} key={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="weight-field">
          <span className="field-label">Severity</span>
          <select
            className="field"
            value={draft.severity}
            onChange={(event) => onDraftChange("severity", event.target.value)}
            disabled={disabled}
          >
            {alertSeverityOptions.map((option) => (
              <option value={option.value} key={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="weight-field">
          <span className="field-label">Min Importance</span>
          <input
            className="field"
            value={draft.min_importance_score}
            onChange={(event) => onDraftChange("min_importance_score", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Min Stock Impact</span>
          <input
            className="field"
            value={draft.min_stock_impact_score}
            onChange={(event) => onDraftChange("min_stock_impact_score", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Tickers</span>
          <input
            className="field"
            value={draft.tickers}
            onChange={(event) => onDraftChange("tickers", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Topics</span>
          <input
            className="field"
            value={draft.topics}
            onChange={(event) => onDraftChange("topics", event.target.value)}
            disabled={disabled}
          />
        </label>
      </div>
      <label className="weight-field">
        <span className="field-label">Description</span>
        <textarea
          className="field textarea"
          value={draft.description}
          onChange={(event) => onDraftChange("description", event.target.value)}
          disabled={disabled}
        />
      </label>
      <div className="toolbar">
        <button className="button primary" onClick={onSave} disabled={disabled}>
          {disabled ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
          Save
        </button>
      </div>
    </div>
  );
}

function DailyDigestPanel({
  digest,
  snapshots,
  digestDate,
  activeSnapshotId,
  generationElapsedMs,
  busySnapshotId,
  busyGenerate,
  busyCopy,
  busyDownload,
  busyEmail,
  busySave,
  onDigestDateChange,
  onGenerate,
  onCopy,
  onDownload,
  onEmail,
  onSave,
  onSnapshotOpen,
  onSnapshotDelete,
  onSnapshotFeedback,
}: {
  digest: DailyDigest | null;
  snapshots: DailyDigestSnapshot[];
  digestDate: string;
  activeSnapshotId: number | null;
  generationElapsedMs: number | null;
  busySnapshotId: number | null;
  busyGenerate: boolean;
  busyCopy: boolean;
  busyDownload: boolean;
  busyEmail: boolean;
  busySave: boolean;
  onDigestDateChange: (value: string) => void;
  onGenerate: () => void;
  onCopy: () => void;
  onDownload: () => void;
  onEmail: () => void;
  onSave: () => void;
  onSnapshotOpen: (snapshot: DailyDigestSnapshot) => void;
  onSnapshotDelete: (snapshot: DailyDigestSnapshot) => void;
  onSnapshotFeedback: (
    snapshot: DailyDigestSnapshot,
    usefulnessFeedback: "useful" | "not_useful",
  ) => void;
}) {
  const digestSections = digest?.sections ?? [];
  const digestActiveAlerts = digest?.active_alerts ?? [];
  const digestSourceCoverage = digest?.source_coverage ?? [];
  const digestWatchlistTickers = digest?.watchlist_tickers ?? [];
  const digestWatchlistCompanies = digest?.watchlist_companies ?? [];
  const digestWatchlistTopics = digest?.watchlist_topics ?? [];
  const digestWatchlistProducts = digest?.watchlist_products ?? [];
  const sectionsWithItems = digestSections.filter((section) => section.items.length);
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Daily Digest</h2>
        <div className="table-actions">
          <button
            className="button icon-button"
            onClick={onGenerate}
            disabled={busyGenerate}
            title="Generate digest preview"
            aria-label="Generate digest preview"
          >
            {busyGenerate ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
          </button>
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
          <button
            className="button icon-button"
            onClick={onDownload}
            disabled={!digest || busyDownload}
            title="Download digest markdown"
            aria-label="Download digest markdown"
          >
            {busyDownload ? <Loader2 className="spin" size={16} /> : <Download size={16} />}
          </button>
          <button
            className="button icon-button"
            onClick={onEmail}
            disabled={!digest || busyEmail}
            title="Open email draft"
            aria-label="Open email draft"
          >
            {busyEmail ? <Loader2 className="spin" size={16} /> : <Mail size={16} />}
          </button>
        </div>
      </div>
      <div className="form-panel digest-date-form">
        <input
          className="field"
          type="date"
          value={digestDate}
          onChange={(event) => onDigestDateChange(event.target.value)}
          aria-label="Digest date"
        />
      </div>
      {digest ? (
        <div className="digest-panel">
          <div className="digest-meta">
            <span>{digest.digest_date}</span>
            <span>
              {digest.total_items} items · {snapshots.length} saved
              {generationElapsedMs !== null
                ? ` · generated in ${formatElapsedMs(generationElapsedMs)}`
                : ""}
            </span>
          </div>
          <div className="digest-headline">{digest.headline}</div>
          <div className="digest-coverage">
            <span className="badge">{digest.high_impact_count} high impact</span>
            <span className="badge stock">{digest.stock_signal_count} stock-linked</span>
            <span className="badge">{digest.read_later_count} read later</span>
            <span className="badge alert-badge">{digest.active_alert_count} active alerts</span>
            <span className="badge muted-badge">{digest.source_count} sources</span>
          </div>
          <div className="digest-coverage">
            {digestWatchlistTickers.slice(0, 4).map((ticker) => (
              <span className="badge stock" key={`ticker:${ticker}`}>
                {ticker}
              </span>
            ))}
            {digestWatchlistCompanies.slice(0, 4).map((company) => (
              <span className="badge" key={`company:${company}`}>
                {company}
              </span>
            ))}
            {digestWatchlistTopics.slice(0, 4).map((topic) => (
              <span className="badge" key={`topic:${topic}`}>
                {topic}
              </span>
            ))}
            {digestWatchlistProducts.slice(0, 4).map((product) => (
              <span className="badge" key={`product:${product}`}>
                {product}
              </span>
            ))}
          </div>
          <div className="digest-coverage">
            {digestSourceCoverage.slice(0, 4).map((source) => (
              <span className="badge" key={source.source_name}>
                {source.source_name} {source.item_count}
              </span>
            ))}
          </div>
          <div className="digest-sections">
            {digestActiveAlerts.length ? (
              <div className="digest-section">
                <div className="digest-section-title">Active Alerts</div>
                <div className="digest-list">
                  {digestActiveAlerts.slice(0, 5).map((alert) => (
                    <div className={`digest-preview-item severity-${alert.severity}`} key={alert.id}>
                      <a
                        className="digest-link"
                        href={alert.item.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {alert.title}
                      </a>
                      <div className="small-muted">
                        {alert.severity} · {alert.rule_name} · {formatDate(alert.created_at)}
                      </div>
                      <div className="digest-item-summary">{alert.reason}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            {sectionsWithItems.length ? (
              sectionsWithItems.map((section) => (
                <div className="digest-section" key={section.key}>
                  <div className="digest-section-title">{section.title}</div>
                  <div className="small-muted">{section.focus}</div>
                  <div className="digest-coverage">
                    <span className="badge">{section.items.length} shown</span>
                    {digestSectionMetricLabels(section).map((label) => (
                      <span className="badge" key={`${section.key}:${label}`}>
                        {label}
                      </span>
                    ))}
                  </div>
                  <div className="digest-list">
                    {section.items.map((item) => (
                      <div className="digest-preview-item" key={item.id}>
                        <a
                          className="digest-link"
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {item.title}
                        </a>
                        <div className="small-muted">
                          {item.source_name}
                          {item.published_at ? ` · ${formatDate(item.published_at)}` : ""}
                        </div>
                        {digestItemSummary(item) ? (
                          <div className="digest-item-summary">{digestItemSummary(item)}</div>
                        ) : null}
                        {digestItemLabels(item).length ? (
                          <div className="digest-coverage">
                            {digestItemLabels(item).map((label) => (
                              <span
                                className={`badge ${item.tickers.includes(label) ? "stock" : ""}`}
                                key={`${item.id}:${label}`}
                              >
                                {label}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">No collected items for this digest date.</div>
            )}
          </div>
          <div className="digest-section">
            <div className="digest-section-title">Saved Snapshots</div>
            {snapshots.length ? (
              <div className="digest-list">
                {snapshots.slice(0, 5).map((snapshot) => (
                  <div
                    className={`snapshot-row ${
                      activeSnapshotId === snapshot.id ? "active-snapshot-row" : ""
                    }`}
                    key={snapshot.id}
                  >
                    <button
                      className="snapshot-open-button"
                      onClick={() => onSnapshotOpen(snapshot)}
                      type="button"
                      aria-label={`Open digest snapshot ${snapshot.digest_date}`}
                    >
                      <div>
                        <div className="timeline-title">{snapshot.digest_date}</div>
                        <div className="small-muted">{snapshot.headline}</div>
                      </div>
                      <span className="small-muted">
                        {snapshot.total_items} items · {countMarkdownLines(snapshot.markdown)} lines
                        {snapshot.usefulness_feedback
                          ? ` · ${formatDigestFeedback(snapshot.usefulness_feedback)}`
                          : ""}
                        {activeSnapshotId === snapshot.id ? " · open" : ""}
                      </span>
                    </button>
                    <div className="snapshot-actions">
                      <button
                        className={`button icon-button ${
                          snapshot.usefulness_feedback === "useful" ? "active-icon-button" : ""
                        }`}
                        onClick={() => onSnapshotFeedback(snapshot, "useful")}
                        disabled={busySnapshotId === snapshot.id}
                        title="Mark digest useful"
                        aria-label={`Mark digest snapshot ${snapshot.digest_date} useful`}
                        type="button"
                      >
                        {busySnapshotId === snapshot.id ? (
                          <Loader2 className="spin" size={16} />
                        ) : (
                          <ThumbsUp size={16} />
                        )}
                      </button>
                      <button
                        className={`button icon-button ${
                          snapshot.usefulness_feedback === "not_useful" ? "active-icon-button" : ""
                        }`}
                        onClick={() => onSnapshotFeedback(snapshot, "not_useful")}
                        disabled={busySnapshotId === snapshot.id}
                        title="Mark digest not useful"
                        aria-label={`Mark digest snapshot ${snapshot.digest_date} not useful`}
                        type="button"
                      >
                        <ThumbsDown size={16} />
                      </button>
                      <button
                        className="button icon-button"
                        onClick={() => onSnapshotDelete(snapshot)}
                        disabled={busySnapshotId === snapshot.id}
                        title="Delete digest snapshot"
                        aria-label={`Delete digest snapshot ${snapshot.digest_date}`}
                        type="button"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">No saved digest snapshots yet.</div>
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

function countMarkdownLines(markdown: string): number {
  return markdown.split(/\r?\n/).filter((line) => line.trim()).length;
}

function formatDigestFeedback(feedback: "useful" | "not_useful"): string {
  return feedback === "useful" ? "useful" : "not useful";
}

function formatAlertFeedback(feedback: "useful" | "not_useful"): string {
  return feedback === "useful" ? "useful" : "not useful";
}

function digestItemSummary(item: FeedItem): string | null {
  return item.summary_short || item.why_it_matters || item.summary_detailed || null;
}

function digestItemLabels(item: FeedItem): string[] {
  const labels = [
    item.is_ai_related ? "" : "not AI-related",
    item.social_signal_score >= 0.65
      ? `social signal ${Math.round(item.social_signal_score * 100)}%`
      : "",
    ...item.tickers,
    ...item.companies,
    ...item.products,
    ...item.technologies,
    item.market_impact_type !== "none" ? formatMarketImpactLabel(item.market_impact_type) : "",
    item.category === "product" && item.subcategory
      ? formatProductUseCaseLabel(item.subcategory)
      : "",
    ...item.topics,
  ];
  return uniqueLabels(labels).slice(0, 4);
}

function digestSectionMetricLabels(section: DigestSection): string[] {
  const metrics = section.metrics;
  return [
    `${metrics.item_count} items`,
    `${metrics.source_count} sources`,
    metrics.high_impact_count ? `${metrics.high_impact_count} high-impact` : "",
    metrics.stock_signal_count ? `${metrics.stock_signal_count} stock-linked` : "",
    metrics.read_later_count ? `${metrics.read_later_count} read-later` : "",
  ].filter(Boolean);
}

function uniqueLabels(labels: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  labels.forEach((label) => {
    const normalized = label.trim();
    const key = normalized.toLowerCase();
    if (normalized && !seen.has(key)) {
      seen.add(key);
      result.push(normalized);
    }
  });
  return result;
}

function SavedItemsPanel({
  items,
  busyItemId,
  busyDetailItemId,
  busyMetadataItemId,
  busyExport,
  busyDownload,
  selectedDetail,
  onCopyExport,
  onDownloadExport,
  onDetail,
  onManualTagFilter,
  onPersonalMetadataSave,
  onReadToggle,
  onUnsave,
}: {
  items: FeedItem[];
  busyItemId: number | null;
  busyDetailItemId: number | null;
  busyMetadataItemId: number | null;
  busyExport: boolean;
  busyDownload: boolean;
  selectedDetail: FeedItemDetail | null;
  onCopyExport: () => void;
  onDownloadExport: () => void;
  onDetail: (itemId: number) => void;
  onManualTagFilter: (tag: string) => void;
  onPersonalMetadataSave: (itemId: number, personalNote: string, manualTags: string) => void;
  onReadToggle: (item: FeedItem) => void;
  onUnsave: (itemId: number) => void;
}) {
  const readLaterItems = items.filter((item) => !item.is_read);
  const readItems = items.filter((item) => item.is_read);
  const orderedItems = orderSavedItemsForReadingQueue(items);
  return (
    <section className="section">
      <div className="section-header">
        <div>
          <h2 className="section-title">Saved Items</h2>
          <div className="small-muted">
            {readLaterItems.length} read later · {readItems.length} read
          </div>
        </div>
        <div className="table-actions">
          <span className="badge">{items.length} saved</span>
          <button
            className="button icon-button"
            onClick={onCopyExport}
            disabled={!items.length || busyExport}
            title="Copy saved items markdown"
            aria-label="Copy saved items markdown"
            type="button"
          >
            {busyExport ? <Loader2 className="spin" size={16} /> : <FileText size={16} />}
          </button>
          <button
            className="button icon-button"
            onClick={onDownloadExport}
            disabled={!items.length || busyDownload}
            title="Download saved items markdown"
            aria-label="Download saved items markdown"
            type="button"
          >
            {busyDownload ? <Loader2 className="spin" size={16} /> : <Download size={16} />}
          </button>
          <Bookmark size={16} aria-hidden="true" />
        </div>
      </div>
      <div className="digest-panel">
        {items.length ? (
          <div className="digest-list">
            {orderedItems.map((item) => (
              <div className="saved-row" key={item.id}>
                <div className="saved-row-main">
                  <a className="digest-link" href={item.url} target="_blank" rel="noreferrer">
                    {item.title}
                  </a>
                  <div className="small-muted">
                    {item.source_name}
                    {item.published_at ? ` · ${formatDate(item.published_at)}` : ""}
                  </div>
                  <div className="badges">
                    {item.is_read ? <span className="badge muted-badge">read</span> : null}
                    {!item.is_read ? <span className="badge">read later</span> : null}
                    {item.read_at ? (
                      <span className="small-muted">read {formatDate(item.read_at)}</span>
                    ) : null}
                  </div>
                  {item.personal_note ? (
                    <div className="saved-note">{item.personal_note}</div>
                  ) : null}
                  {item.manual_tags.length ? (
                    <div className="saved-tag-row" aria-label={`Manual tags for ${item.title}`}>
                      {item.manual_tags.map((tag) => (
                        <button
                          className="badge-button"
                          key={`${item.id}:${tag}`}
                          onClick={() => onManualTagFilter(tag)}
                          type="button"
                        >
                          {tag}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
                <div className="table-actions">
                  <button
                    className="button icon-button"
                    onClick={() => onDetail(item.id)}
                    disabled={busyDetailItemId === item.id}
                    title="Open item details"
                    aria-label="Open item details"
                    type="button"
                  >
                    {busyDetailItemId === item.id ? (
                      <Loader2 className="spin" size={16} />
                    ) : (
                      <Search size={16} />
                    )}
                  </button>
                  <button
                    className={`button icon-button ${item.is_read ? "active-icon-button" : ""}`}
                    onClick={() => onReadToggle(item)}
                    disabled={busyItemId === item.id}
                    title={item.is_read ? "Mark unread" : "Mark read"}
                    aria-label={item.is_read ? "Mark unread" : "Mark read"}
                    type="button"
                  >
                    {busyItemId === item.id ? (
                      <Loader2 className="spin" size={16} />
                    ) : (
                      <CircleCheck size={16} />
                    )}
                  </button>
                  <button
                    className="button icon-button"
                    onClick={() => onUnsave(item.id)}
                    disabled={busyItemId === item.id}
                    title="Remove saved item"
                    aria-label="Remove saved item"
                    type="button"
                  >
                    {busyItemId === item.id ? (
                      <Loader2 className="spin" size={16} />
                    ) : (
                      <X size={16} />
                    )}
                  </button>
                </div>
                {selectedDetail?.id === item.id ? (
                  <div className="saved-row-detail">
                    <FeedDetailPanel
                      detail={selectedDetail}
                      busy={busyMetadataItemId === item.id}
                      onPersonalMetadataSave={onPersonalMetadataSave}
                    />
                  </div>
                ) : null}
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

function orderSavedItemsForReadingQueue(items: FeedItem[]): FeedItem[] {
  return [...items].sort((left, right) => {
    if (left.is_read !== right.is_read) {
      return left.is_read ? 1 : -1;
    }
    return savedItemTimestamp(right) - savedItemTimestamp(left);
  });
}

function savedItemTimestamp(item: FeedItem): number {
  const value = item.is_read
    ? item.read_at ?? item.published_at
    : item.published_at ?? item.read_at;
  return value ? new Date(value).getTime() : 0;
}

function HiddenItemsPanel({
  items,
  busyItemId,
  onUnhide,
  onDelete,
}: {
  items: FeedItem[];
  busyItemId: number | null;
  onUnhide: (itemId: number) => void;
  onDelete: (itemId: number) => void;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Hidden Items</h2>
        <EyeOff size={16} aria-hidden="true" />
      </div>
      <div className="digest-panel">
        {items.length ? (
          <div className="digest-list">
            {items.map((item) => (
              <div className="saved-row" key={item.id}>
                <div className="saved-row-main">
                  <a className="digest-link" href={item.url} target="_blank" rel="noreferrer">
                    {item.title}
                  </a>
                  <div className="small-muted">
                    {item.source_name} ·{" "}
                    {item.published_at ? formatDate(item.published_at) : "unknown date"}
                  </div>
                </div>
                <button
                  className="button icon-button"
                  onClick={() => onUnhide(item.id)}
                  disabled={busyItemId === item.id}
                  title="Restore hidden item"
                  aria-label="Restore hidden item"
                  type="button"
                >
                  {busyItemId === item.id ? (
                    <Loader2 className="spin" size={16} />
                  ) : (
                    <RefreshCw size={16} />
                  )}
                </button>
                <button
                  className="button icon-button"
                  onClick={() => onDelete(item.id)}
                  disabled={busyItemId === item.id}
                  title="Permanently delete item"
                  aria-label="Permanently delete item"
                  type="button"
                >
                  {busyItemId === item.id ? (
                    <Loader2 className="spin" size={16} />
                  ) : (
                    <Trash2 size={16} />
                  )}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">No hidden items.</div>
        )}
      </div>
    </section>
  );
}

function EventClusterPanel({
  clusters,
  selectedCluster,
  busyClusterKey,
  busyClusterExplanationKey,
  explanations,
  limit,
  onSelectCluster,
  onExplainCluster,
}: {
  clusters: EventCluster[];
  selectedCluster: EventCluster | null;
  busyClusterKey: string | null;
  busyClusterExplanationKey: string | null;
  explanations: Record<string, EventClusterLlmExplanation>;
  limit?: number;
  onSelectCluster: (cluster: EventCluster) => void;
  onExplainCluster: (cluster: EventCluster) => void;
}) {
  const visibleClusters = typeof limit === "number" ? clusters.slice(0, limit) : clusters;
  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Event Clusters</h2>
        <span className="small-muted">
          {visibleClusters.length}
          {visibleClusters.length === clusters.length ? "" : `/${clusters.length}`} clusters
        </span>
      </div>
      <div className="digest-panel">
        {clusters.length ? (
          visibleClusters.map((cluster) => {
            const expanded = selectedCluster?.cluster_key === cluster.cluster_key;
            const detail = expanded ? selectedCluster : cluster;
            const llmExplanation = explanations[cluster.cluster_key];
            return (
              <div className="digest-section" key={cluster.cluster_key}>
                <div className="cluster-head">
                  <div>
                    <div className="digest-section-title">
                      {cluster.item_count} item{cluster.item_count === 1 ? "" : "s"} ·{" "}
                      {cluster.source_count} source{cluster.source_count === 1 ? "" : "s"} ·{" "}
                      {formatConfirmationLevel(cluster.confirmation_level)}
                    </div>
                    <div className="small-muted">
                      Confidence {Math.round(cluster.confidence * 100)} · Importance{" "}
                      {Math.round(cluster.importance_score * 100)}
                      {cluster.duplicate_item_count > 0
                        ? ` · ${cluster.duplicate_item_count} repeat item${
                            cluster.duplicate_item_count === 1 ? "" : "s"
                          }`
                        : ""}
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
                  {cluster.sources.slice(0, 4).map((source) => (
                    <span
                      className="badge muted-badge"
                      key={`source-${cluster.cluster_key}-${source}`}
                    >
                      {source}
                    </span>
                  ))}
                  {[...cluster.tickers, ...cluster.topics.slice(0, 3)].map((label) => (
                    <span className="badge" key={label}>
                      {label}
                    </span>
                  ))}
                </div>
                <div className="summary">{cluster.main_summary}</div>
                <div className="small-muted">{detail.explanation}</div>
                <div className="cluster-timeline">
                  {cluster.timeline.slice(0, 4).map((event) => (
                    <div
                      className="cluster-timeline-row"
                      key={`${cluster.cluster_key}-${event.item_id}`}
                    >
                      <span>{event.published_at ? formatDate(event.published_at) : "undated"}</span>
                      <span>{event.source_name}</span>
                      <span className="cluster-timeline-title">{event.title}</span>
                      <span>{Math.round(event.importance_score * 100)}</span>
                    </div>
                  ))}
                </div>
                {expanded ? (
                  <div className="cluster-evidence-list">
                    <div className="cluster-explanation-actions">
                      <button
                        className="button"
                        onClick={() => onExplainCluster(detail)}
                        disabled={busyClusterExplanationKey === cluster.cluster_key}
                        title="Generate LLM cluster explanation"
                        type="button"
                      >
                        {busyClusterExplanationKey === cluster.cluster_key ? (
                          <Loader2 className="spin" size={16} />
                        ) : (
                          <Bot size={16} />
                        )}
                        Explain
                      </button>
                      {llmExplanation ? (
                        <span className="small-muted">
                          {llmExplanation.model} · {llmExplanation.total_tokens} tokens
                        </span>
                      ) : null}
                    </div>
                    {llmExplanation ? (
                      <div className="llm-explanation">
                        <div className="digest-section-title">LLM Explanation</div>
                        <div className="summary">{llmExplanation.explanation}</div>
                      </div>
                    ) : null}
                    <ClusterEvidenceSummary cluster={detail} />
                    <div className="digest-section-title">Uncertainty</div>
                    {detail.uncertainty_notes.map((note) => (
                      <div className="small-muted" key={note}>
                        {note}
                      </div>
                    ))}
                    {detail.related_market_ticker ? (
                      <div className="cluster-market-context">
                        <div className="digest-section-title">
                          {detail.related_market_ticker} Price Context
                        </div>
                        <StockPriceChart market={detail.related_market} />
                      </div>
                    ) : null}
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

function ClusterEvidenceSummary({ cluster }: { cluster: EventCluster }) {
  const timeRange = [
    cluster.first_seen_at ? `first seen ${formatDate(cluster.first_seen_at)}` : null,
    cluster.last_seen_at ? `last seen ${formatDate(cluster.last_seen_at)}` : null,
    cluster.latest_update_at ? `latest update ${formatDate(cluster.latest_update_at)}` : null,
  ].filter(Boolean);
  const relatedLabels = uniqueLabels([
    ...cluster.tickers,
    ...cluster.topics,
    cluster.related_market_ticker ?? "",
  ]);

  return (
    <div className="cluster-detail-grid">
      <div className="cluster-detail-card">
        <div className="field-label">Confirmation</div>
        <div className="cluster-detail-value">
          {formatConfirmationLevel(cluster.confirmation_level)}
        </div>
        <div className="small-muted">
          {cluster.source_count} source{cluster.source_count === 1 ? "" : "s"} ·{" "}
          {cluster.item_count} item{cluster.item_count === 1 ? "" : "s"}
          {cluster.duplicate_item_count
            ? ` · ${cluster.duplicate_item_count} repeated`
            : ""}
        </div>
      </div>
      <div className="cluster-detail-card">
        <div className="field-label">Scores</div>
        <div className="cluster-detail-value">
          Confidence {Math.round(cluster.confidence * 100)}
        </div>
        <div className="small-muted">
          Importance {Math.round(cluster.importance_score * 100)} · Top{" "}
          {Math.round(cluster.top_score * 100)}
        </div>
      </div>
      <div className="cluster-detail-card">
        <div className="field-label">Timing</div>
        <div className="cluster-detail-value">{cluster.earliest_source ?? "unknown source"}</div>
        <div className="small-muted">{timeRange.join(" · ") || "No dated evidence yet"}</div>
      </div>
      <div className="cluster-detail-card wide">
        <div className="field-label">All Related Sources</div>
        <div className="badges">
          {cluster.sources.map((source) => (
            <span
              className="badge muted-badge"
              key={`detail-source-${cluster.cluster_key}-${source}`}
            >
              {source}
            </span>
          ))}
        </div>
      </div>
      <div className="cluster-detail-card wide">
        <div className="field-label">Affected Tickers and Topics</div>
        <div className="badges">
          {relatedLabels.length ? (
            relatedLabels.map((label) => (
              <span className="badge" key={`detail-label-${cluster.cluster_key}-${label}`}>
                {label}
              </span>
            ))
          ) : (
            <span className="small-muted">No ticker or topic labels extracted.</span>
          )}
        </div>
      </div>
      <div className="cluster-detail-card wide full">
        <div className="field-label">Timeline</div>
        <div className="cluster-timeline">
          {cluster.timeline.map((event) => (
            <div
              className="cluster-timeline-row"
              key={`detail-timeline-${cluster.cluster_key}-${event.item_id}`}
            >
              <span>{event.published_at ? formatDate(event.published_at) : "undated"}</span>
              <span>{event.source_name}</span>
              <span className="cluster-timeline-title">{event.title}</span>
              <span>{Math.round(event.importance_score * 100)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SearchPanel({
  query,
  source,
  category,
  subcategory,
  ticker,
  company,
  topic,
  manualTag,
  stockOptions,
  topicOptions,
  language,
  dateFrom,
  dateTo,
  minImportance,
  minSocialSignal,
  readStatus,
  aiRelated,
  intent,
  summary,
  savedOnly,
  disabled,
  onQueryChange,
  onSourceChange,
  onCategoryChange,
  onSubcategoryChange,
  onTickerChange,
  onCompanyChange,
  onTopicChange,
  onManualTagChange,
  onTickerFilter,
  onTopicFilter,
  onLanguageChange,
  onDateFromChange,
  onDateToChange,
  onMinImportanceChange,
  onMinSocialSignalChange,
  onReadStatusChange,
  onAiRelatedChange,
  onSavedOnlyChange,
  onSearch,
  onClear,
}: {
  query: string;
  source: string;
  category: string;
  subcategory: string;
  ticker: string;
  company: string;
  topic: string;
  manualTag: string;
  stockOptions: StockWatchlistItem[];
  topicOptions: TopicWatchlistItem[];
  language: string;
  dateFrom: string;
  dateTo: string;
  minImportance: string;
  minSocialSignal: string;
  readStatus: string;
  aiRelated: string;
  intent: SearchIntent | null;
  summary: string | null;
  savedOnly: boolean;
  disabled: boolean;
  onQueryChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
  onSubcategoryChange: (value: string) => void;
  onTickerChange: (value: string) => void;
  onCompanyChange: (value: string) => void;
  onTopicChange: (value: string) => void;
  onManualTagChange: (value: string) => void;
  onTickerFilter: (stock: StockWatchlistItem) => void;
  onTopicFilter: (topic: TopicWatchlistItem) => void;
  onLanguageChange: (value: string) => void;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
  onMinImportanceChange: (value: string) => void;
  onMinSocialSignalChange: (value: string) => void;
  onReadStatusChange: (value: string) => void;
  onAiRelatedChange: (value: string) => void;
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
      {stockOptions.length ? (
        <div className="topic-filter-row" aria-label="Watchlist stock filters">
          {stockOptions.slice(0, 10).map((stock) => (
            <button
              className={`badge-button ${ticker.toUpperCase() === stock.ticker ? "active" : ""}`}
              key={stock.ticker}
              onClick={() => onTickerFilter(stock)}
              disabled={disabled}
              type="button"
            >
              {stock.ticker}
            </button>
          ))}
        </div>
      ) : null}
      {topicOptions.length ? (
        <div className="topic-filter-row" aria-label="Watchlist topic filters">
          {topicOptions.slice(0, 8).map((topicOption) => (
            <button
              className={`badge-button ${topic === topicOption.topic ? "active" : ""}`}
              key={topicOption.topic}
              onClick={() => onTopicFilter(topicOption)}
              disabled={disabled}
              type="button"
            >
              {topicOption.label}
            </button>
          ))}
        </div>
      ) : null}
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
          {categoryOptions.map((option) => (
            <option value={option.value} key={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          className="field"
          value={subcategory}
          onChange={(event) => onSubcategoryChange(event.target.value)}
          aria-label="Product use case filter"
        >
          <option value="">Any product use case</option>
          {productUseCaseOptions.map((option) => (
            <option value={option.value} key={option.value}>
              {option.label}
            </option>
          ))}
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
          value={manualTag}
          onChange={(event) => onManualTagChange(event.target.value)}
          placeholder="Manual tag"
        />
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
        <input
          className="field"
          type="number"
          min="0"
          max="1"
          step="0.05"
          value={minSocialSignal}
          onChange={(event) => onMinSocialSignalChange(event.target.value)}
          placeholder="Min social"
          aria-label="Minimum social signal score"
        />
        <select
          className="field"
          value={readStatus}
          onChange={(event) => onReadStatusChange(event.target.value)}
          aria-label="Read status filter"
        >
          <option value="">Any read status</option>
          <option value="unread">Unread</option>
          <option value="read">Read</option>
        </select>
        <select
          className="field"
          value={aiRelated}
          onChange={(event) => onAiRelatedChange(event.target.value)}
          aria-label="AI relevance filter"
        >
          <option value="">Any AI relevance</option>
          <option value="true">AI-related</option>
          <option value="false">Needs review</option>
        </select>
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
      {summary ? <SearchSummaryBrief summary={summary} /> : null}
    </div>
  );
}

function SearchSummaryBrief({ summary }: { summary: string }) {
  const lines = summary
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const headline = lines[0] ?? summary;
  const signalLines = lines.filter((line) => /^\d+\.\s+/.test(line));
  const trailingLines = lines.filter(
    (line, index) => index > 0 && line !== "Top signals:" && !/^\d+\.\s+/.test(line),
  );

  if (!signalLines.length) {
    return <div className="summary search-summary">{summary}</div>;
  }

  return (
    <div className="search-summary-brief" aria-label="Search summary">
      <div className="search-summary-headline">{headline}</div>
      <ol className="search-summary-list">
        {signalLines.map((line) => (
          <li key={line}>{line.replace(/^\d+\.\s+/, "")}</li>
        ))}
      </ol>
      {trailingLines.length ? (
        <div className="small-muted">{trailingLines.join(" ")}</div>
      ) : null}
    </div>
  );
}

function FeedCard({
  item,
  busy,
  detail,
  busyDetail,
  busyMetadata,
  onSummarize,
  onClassify,
  onDetail,
  onAction,
  onDelete,
  onPersonalMetadataSave,
}: {
  item: FeedItem;
  busy: boolean;
  detail: FeedItemDetail | null;
  busyDetail: boolean;
  busyMetadata: boolean;
  onSummarize: (itemId: number) => void;
  onClassify: (itemId: number) => void;
  onDetail: (itemId: number) => void;
  onAction: (
    itemId: number,
    action:
      | "save"
      | "unsave"
      | "hide"
      | "mark-important"
      | "unmark-important"
      | "mark-read"
      | "mark-unread"
      | "mark-useful"
      | "mark-not-useful"
      | "clear-feedback",
  ) => void;
  onDelete: (itemId: number) => void;
  onPersonalMetadataSave: (itemId: number, personalNote: string, manualTags: string) => void;
}) {
  const researchInsights = parseResearchInsights(item);
  const cardSummary = buildCardSummaryDisplay(item);
  const displaySummary =
    cardSummary.oneLine || cardSummary.bullets.length
      ? null
      : item.summary_short || (researchInsights ? null : item.summary_detailed);
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
          {item.is_read ? <span className="badge muted-badge">read</span> : null}
          {item.usefulness_feedback ? (
            <span className="badge">
              {item.usefulness_feedback === "useful" ? "useful" : "not useful"}
            </span>
          ) : null}
          {!item.is_ai_related ? (
            <span className="badge muted-badge">not AI-related</span>
          ) : null}
          <span className={`badge ${item.category === "research" ? "research" : ""}`}>
            {formatCategoryLabel(item.category)}
          </span>
          {item.category === "product" && item.subcategory ? (
            <span className="badge">{formatProductUseCaseLabel(item.subcategory)}</span>
          ) : null}
          {item.market_impact_type !== "none" ? (
            <span className="badge stock">{formatMarketImpactLabel(item.market_impact_type)}</span>
          ) : null}
          {item.tickers.map((ticker) => (
            <span className="badge stock" key={ticker}>
              {ticker}
            </span>
          ))}
        </div>
      </div>

      <div className="badges">
        {item.products.slice(0, 4).map((product) => (
          <span className="badge" key={`product:${product}`}>
            {product}
          </span>
        ))}
        {item.technologies.slice(0, 6).map((technology) => (
          <span className="badge" key={`technology:${technology}`}>
            {technology}
          </span>
        ))}
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
        <Score label="Social" value={item.social_signal_score} />
        <Score label="Importance" value={item.importance_score} />
        <Score label="Novelty" value={item.novelty_score} />
        <Score label="Stock" value={item.stock_impact_score} />
      </div>

      {cardSummary.oneLine || cardSummary.bullets.length ? (
        <div className="card-summary">
          {cardSummary.oneLine ? <div className="summary">{cardSummary.oneLine}</div> : null}
          {cardSummary.bullets.length ? (
            <ul>
              {cardSummary.bullets.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : displaySummary ? (
        <div className="summary">{displaySummary}</div>
      ) : null}
      {researchInsights ? <ResearchInsightsPanel insights={researchInsights} /> : null}

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
            className={`button icon-button ${item.is_important ? "active-icon-button" : ""}`}
            onClick={() =>
              onAction(item.id, item.is_important ? "unmark-important" : "mark-important")
            }
            disabled={busy}
            title={item.is_important ? "Remove important mark" : "Mark important"}
            aria-label={item.is_important ? "Remove important mark" : "Mark important"}
          >
            {busy ? (
              <Loader2 className="spin" size={16} />
            ) : (
              <Flag size={16} fill={item.is_important ? "currentColor" : "none"} />
            )}
          </button>
          <button
            className={`button icon-button ${item.is_read ? "active-icon-button" : ""}`}
            onClick={() => onAction(item.id, item.is_read ? "mark-unread" : "mark-read")}
            disabled={busy}
            title={item.is_read ? "Mark unread" : "Mark read"}
            aria-label={item.is_read ? "Mark unread" : "Mark read"}
          >
            {busy ? <Loader2 className="spin" size={16} /> : <CircleCheck size={16} />}
          </button>
          <button
            className={`button icon-button ${
              item.usefulness_feedback === "useful" ? "active-icon-button" : ""
            }`}
            onClick={() =>
              onAction(
                item.id,
                item.usefulness_feedback === "useful" ? "clear-feedback" : "mark-useful",
              )
            }
            disabled={busy}
            title={
              item.usefulness_feedback === "useful"
                ? "Clear useful feedback"
                : "Mark item useful"
            }
            aria-label={
              item.usefulness_feedback === "useful"
                ? "Clear useful feedback"
                : "Mark item useful"
            }
          >
            {busy ? <Loader2 className="spin" size={16} /> : <ThumbsUp size={16} />}
          </button>
          <button
            className={`button icon-button ${
              item.usefulness_feedback === "not_useful" ? "active-icon-button" : ""
            }`}
            onClick={() =>
              onAction(
                item.id,
                item.usefulness_feedback === "not_useful"
                  ? "clear-feedback"
                  : "mark-not-useful",
              )
            }
            disabled={busy}
            title={
              item.usefulness_feedback === "not_useful"
                ? "Clear not useful feedback"
                : "Mark item not useful"
            }
            aria-label={
              item.usefulness_feedback === "not_useful"
                ? "Clear not useful feedback"
                : "Mark item not useful"
            }
          >
            {busy ? <Loader2 className="spin" size={16} /> : <ThumbsDown size={16} />}
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
            className="button icon-button"
            onClick={() => onDelete(item.id)}
            disabled={busy}
            title="Permanently delete item"
            aria-label="Permanently delete item"
          >
            {busy ? <Loader2 className="spin" size={16} /> : <Trash2 size={16} />}
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
          <a
            className="button icon-button"
            href={item.url}
            target="_blank"
            rel="noreferrer"
            title="Open source"
          >
            <ExternalLink size={16} />
          </a>
        </div>
      </div>
      {detail ? (
        <FeedDetailPanel
          detail={detail}
          busy={busyMetadata}
          onPersonalMetadataSave={onPersonalMetadataSave}
        />
      ) : null}
    </article>
  );
}

function buildCardSummaryDisplay(item: FeedItem): { oneLine: string | null; bullets: string[] } {
  const lines = splitSummaryLines(item.summary_short);
  const bullets = lines.filter(isSummaryBulletLine).map(stripSummaryBulletPrefix).slice(0, 4);
  if (!bullets.length) {
    return { oneLine: null, bullets: [] };
  }
  const oneLine = lines.find((line) => !isSummaryBulletLine(line)) ?? null;
  return { oneLine, bullets };
}

function splitSummaryLines(value: string | null): string[] {
  return (value ?? "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function isSummaryBulletLine(value: string): boolean {
  return value.startsWith("- ") || value.startsWith("* ");
}

function stripSummaryBulletPrefix(value: string): string {
  return isSummaryBulletLine(value) ? value.slice(2).trim() : value.trim();
}

function buildFeedCardExplanation(item: FeedItem): string {
  const relatedSignals = uniqueLabels([
    ...item.tickers,
    ...item.products,
    item.category === "product" && item.subcategory
      ? formatProductUseCaseLabel(item.subcategory)
      : "",
    ...item.technologies.slice(0, 3),
    ...item.topics.slice(0, 3),
  ]);
  const scoreSignals = [
    item.classification_confidence >= 0.8 ? "high classifier confidence" : null,
    item.classification_confidence < 0.6 ? "lower classifier confidence" : null,
    item.source_quality_score >= 0.8 ? "high source credibility" : null,
    item.source_quality_score < 0.6 ? "lower source credibility" : null,
    item.relevance_score >= 0.72 ? "high AI relevance" : null,
    item.importance_score >= 0.72 ? "high importance" : null,
    item.novelty_score >= 0.72 ? "novel signal" : null,
    item.social_signal_score >= 0.65 ? "strong source engagement" : null,
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

function FeedDetailPanel({
  detail,
  busy,
  onPersonalMetadataSave,
}: {
  detail: FeedItemDetail;
  busy: boolean;
  onPersonalMetadataSave: (itemId: number, personalNote: string, manualTags: string) => void;
}) {
  const researchInsights = parseResearchInsights(detail);
  const [personalNote, setPersonalNote] = useState(detail.personal_note ?? "");
  const [manualTags, setManualTags] = useState(detail.manual_tags.join(", "));

  useEffect(() => {
    setPersonalNote(detail.personal_note ?? "");
    setManualTags(detail.manual_tags.join(", "));
  }, [detail.id, detail.manual_tags, detail.personal_note]);

  return (
    <div className="feed-detail-panel">
      <div className="section-header">
        <h4 className="section-title">Item Details</h4>
        <span className="small-muted">{detail.language}</span>
      </div>
      <div className="summary">{detail.score_explanation}</div>
      <div className="score-grid">
        <Score label="Source" value={detail.source_quality_score} />
        <Score label="Social" value={detail.social_signal_score} />
        <Score label="Relevance" value={detail.relevance_score} />
        <Score label="Confidence" value={detail.classification_confidence} />
        <Score label="Importance" value={detail.importance_score} />
        <Score label="Stock" value={detail.stock_impact_score} />
      </div>
      <PublicEngagementPanel metrics={detail.public_engagement} />
      <div className="summary">
        <strong>Classification audit:</strong>{" "}
        {detail.is_ai_related ? "AI-related" : "Needs AI relevance review"} ·{" "}
        {formatCategoryLabel(detail.category)}
        {detail.subcategory ? ` · ${formatCategoryLabel(detail.subcategory)}` : ""} · language{" "}
        {detail.language} · sentiment {formatCategoryLabel(detail.sentiment)} · confidence{" "}
        {Math.round(detail.classification_confidence * 100)}
        {detail.market_impact_type !== "none"
          ? ` · ${formatMarketImpactLabel(detail.market_impact_type)}`
          : ""}
      </div>
      <div className="badges">
        {detail.is_saved ? <span className="badge">saved</span> : null}
        {detail.is_important ? <span className="badge stock">important</span> : null}
        {detail.is_hidden ? <span className="badge muted-badge">hidden</span> : null}
        {detail.is_read ? <span className="badge muted-badge">read</span> : null}
        {detail.usefulness_feedback ? (
          <span className="badge">
            {detail.usefulness_feedback === "useful" ? "useful" : "not useful"}
          </span>
        ) : null}
        {detail.category === "product" && detail.subcategory ? (
          <span className="badge">{formatProductUseCaseLabel(detail.subcategory)}</span>
        ) : null}
        {detail.tickers.slice(0, 6).map((ticker) => (
          <span className="badge stock" key={ticker}>
            {ticker}
          </span>
        ))}
        {detail.manual_tags.map((tag) => (
          <span className="badge" key={`manual:${tag}`}>
            {tag}
          </span>
        ))}
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
        {detail.technologies.slice(0, 6).map((technology) => (
          <span className="badge" key={`technology:${technology}`}>
            {technology}
          </span>
        ))}
        {detail.topics.slice(0, 8).map((topic) => (
          <span className="badge" key={`topic:${topic}`}>
            {topic}
          </span>
        ))}
      </div>
      <div className="detail-note-editor">
        <label className="weight-field">
          <span className="field-label">Personal Note</span>
          <textarea
            className="field textarea"
            value={personalNote}
            onChange={(event) => setPersonalNote(event.target.value)}
            disabled={busy}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Manual Tags</span>
          <input
            className="field"
            value={manualTags}
            onChange={(event) => setManualTags(event.target.value)}
            disabled={busy}
          />
        </label>
        <div className="toolbar">
          <button
            className="button primary"
            onClick={() => onPersonalMetadataSave(detail.id, personalNote, manualTags)}
            disabled={busy}
            type="button"
          >
            {busy ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
            Save
          </button>
        </div>
      </div>
      {detail.why_it_matters ? (
        <div className="summary">
          <strong>Why it matters:</strong> {detail.why_it_matters}
        </div>
      ) : null}
      <div className="summary">
        <strong>AI relevance:</strong>{" "}
        {detail.is_ai_related
          ? "Classified as AI-related"
          : "Not currently classified as AI-related"}
      </div>
      {detail.market_impact_type !== "none" ? (
        <div className="summary">
          <strong>Market impact type:</strong> {formatMarketImpactLabel(detail.market_impact_type)}
        </div>
      ) : null}
      {detail.stock_reaction_summary ? (
        <div className="summary">
          <strong>Price reaction:</strong> {detail.stock_reaction_summary.summary}
        </div>
      ) : null}
      <SummaryProfilesPanel detail={detail} />
      {researchInsights ? <ResearchInsightsPanel insights={researchInsights} /> : null}
      {detail.summary_detailed ? (
        <div className="summary">
          <strong>Detailed summary:</strong>
          {`\n${detail.summary_detailed}`}
        </div>
      ) : null}
      <div className="summary">
        <strong>Uncertainty:</strong> {detail.uncertainty_notes.join(" ")}
      </div>
      {detail.personalization_notes.length ? (
        <div className="summary">
          <strong>Personalization:</strong> {detail.personalization_notes.join(" ")}
        </div>
      ) : null}
      {detail.text ? <div className="detail-text">{detail.text}</div> : null}
    </div>
  );
}

function PublicEngagementPanel({ metrics }: { metrics: PublicEngagementMetric[] }) {
  if (!metrics.length) {
    return null;
  }
  return (
    <div className="public-engagement-grid" aria-label="Public engagement evidence">
      {metrics.map((metric) => (
        <div className="public-engagement-metric" key={metric.key}>
          <div className="field-label">{metric.label}</div>
          <div className="score-value">{formatCompactNumber(metric.value)}</div>
        </div>
      ))}
    </div>
  );
}

function SummaryProfilesPanel({ detail }: { detail: FeedItemDetail }) {
  const hasSummaryProfiles =
    detail.one_line_summary ||
    detail.card_summary.length ||
    detail.technical_summary ||
    detail.market_watch_summary;
  if (!hasSummaryProfiles) {
    return null;
  }
  return (
    <div className="summary-profile-grid">
      {detail.one_line_summary ? (
        <div className="summary-profile">
          <div className="field-label">One-line</div>
          <div>{detail.one_line_summary}</div>
        </div>
      ) : null}
      {detail.card_summary.length ? (
        <div className="summary-profile">
          <div className="field-label">Card Summary</div>
          <ul>
            {detail.card_summary.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {detail.technical_summary ? (
        <div className="summary-profile">
          <div className="field-label">Technical</div>
          <div>{detail.technical_summary}</div>
        </div>
      ) : null}
      {detail.market_watch_summary ? (
        <div className="summary-profile">
          <div className="field-label">Market Watch</div>
          <div>{detail.market_watch_summary}</div>
        </div>
      ) : null}
      <div className="small-muted">
        Summary source: {formatSummarySource(detail.summary_source)}
      </div>
    </div>
  );
}

function ResearchInsightsPanel({
  insights,
  compact = false,
}: {
  insights: ResearchInsights;
  compact?: boolean;
}) {
  const rows = [
    ["Contribution", insights.contribution],
    ["Method", insights.method],
    ["Relevance", insights.relevance],
  ].filter((row): row is [string, string] => Boolean(row[1]));

  if (!rows.length) {
    return null;
  }

  return (
    <div className={`research-insights ${compact ? "compact-research-insights" : ""}`}>
      {rows.map(([label, value]) => (
        <div className="research-insight" key={label}>
          <div className="research-insight-label">{label}</div>
          <div className="research-insight-text">{value}</div>
        </div>
      ))}
    </div>
  );
}

function parseResearchInsights(item: FeedItem): ResearchInsights | null {
  if (!["research", "benchmark_evaluation"].includes(item.category) || !item.summary_detailed) {
    return null;
  }

  const insights: ResearchInsights = {};
  for (const line of item.summary_detailed.split("\n")) {
    const trimmed = line.trim();
    const lowered = trimmed.toLowerCase();
    if (lowered.startsWith("research contribution:")) {
      insights.contribution = valueAfterPrefix(trimmed);
    } else if (lowered.startsWith("research method:")) {
      insights.method = valueAfterPrefix(trimmed);
    } else if (lowered.startsWith("technical relevance:")) {
      insights.relevance = valueAfterPrefix(trimmed);
    }
  }

  return insights.contribution || insights.method || insights.relevance ? insights : null;
}

function valueAfterPrefix(value: string): string | undefined {
  const separatorIndex = value.indexOf(":");
  if (separatorIndex === -1) {
    return undefined;
  }
  const text = value.slice(separatorIndex + 1).trim();
  return text || undefined;
}

function updateSelectedFeedDetail(
  detail: FeedItemDetail | null,
  updated: FeedItem,
): FeedItemDetail | null {
  if (!detail || detail.id !== updated.id) {
    return detail;
  }
  return {
    ...detail,
    ...updated,
    text: detail.text,
    score_explanation: detail.score_explanation,
    uncertainty_notes: detail.uncertainty_notes,
    personalization_notes: detail.personalization_notes,
    action_state: {
      ...detail.action_state,
      is_saved: updated.is_saved,
      is_hidden: updated.is_hidden,
      is_important: updated.is_important,
      is_read: updated.is_read,
      has_usefulness_feedback: updated.usefulness_feedback !== null,
    },
  };
}

function reconcileFeedDetailAfterRefresh(
  detail: FeedItemDetail | null,
  feed: FeedItem[],
): FeedItemDetail | null {
  if (!detail) {
    return null;
  }
  const refreshed = feed.find((item) => item.id === detail.id);
  return refreshed ? updateSelectedFeedDetail(detail, refreshed) : null;
}

function reconcileEventClusterAfterRefresh(
  selectedCluster: EventCluster | null,
  clusters: EventCluster[],
): EventCluster | null {
  if (!selectedCluster) {
    return null;
  }
  return clusters.find((cluster) => cluster.cluster_key === selectedCluster.cluster_key) ?? null;
}

function syncSavedFeedItem(items: FeedItem[], updated: FeedItem): FeedItem[] {
  if (!updated.is_saved) {
    return items.filter((item) => item.id !== updated.id);
  }
  const exists = items.some((item) => item.id === updated.id);
  if (!exists) {
    return [updated, ...items];
  }
  return items.map((item) => (item.id === updated.id ? updated : item));
}

function syncModuleFeedItem(
  moduleFeeds: Partial<Record<FeedModuleKey, FeedItem[]>>,
  updated: FeedItem,
): Partial<Record<FeedModuleKey, FeedItem[]>> {
  return Object.fromEntries(
    Object.entries(moduleFeeds).map(([moduleKey, items]) => [
      moduleKey,
      items?.map((item) => (item.id === updated.id ? updated : item)) ?? [],
    ]),
  ) as Partial<Record<FeedModuleKey, FeedItem[]>>;
}

function removeModuleFeedItem(
  moduleFeeds: Partial<Record<FeedModuleKey, FeedItem[]>>,
  itemId: number,
): Partial<Record<FeedModuleKey, FeedItem[]>> {
  return Object.fromEntries(
    Object.entries(moduleFeeds).map(([moduleKey, items]) => [
      moduleKey,
      items?.filter((item) => item.id !== itemId) ?? [],
    ]),
  ) as Partial<Record<FeedModuleKey, FeedItem[]>>;
}

function feedActionStatus(action: string, itemId: number): string {
  if (action === "save") {
    return `Saved item ${itemId}`;
  }
  if (action === "mark-important") {
    return `Marked item ${itemId} important`;
  }
  if (action === "unmark-important") {
    return `Removed important mark from item ${itemId}`;
  }
  if (action === "mark-useful") {
    return `Marked item ${itemId} useful`;
  }
  if (action === "mark-not-useful") {
    return `Marked item ${itemId} not useful`;
  }
  if (action === "clear-feedback") {
    return `Cleared feedback for item ${itemId}`;
  }
  return `Updated item ${itemId}`;
}

function ManualSubmissionPanel({
  title,
  sourceName,
  url,
  text,
  engagement,
  personalNote,
  manualTags,
  saveItem,
  classifyWithLlm,
  summarizeWithLlm,
  disabled,
  onTitleChange,
  onSourceNameChange,
  onUrlChange,
  onTextChange,
  onEngagementChange,
  onPersonalNoteChange,
  onManualTagsChange,
  onSaveItemChange,
  onClassifyWithLlmChange,
  onSummarizeWithLlmChange,
  onSubmit,
}: {
  title: string;
  sourceName: string;
  url: string;
  text: string;
  engagement: ManualEngagementDraft;
  personalNote: string;
  manualTags: string;
  saveItem: boolean;
  classifyWithLlm: boolean;
  summarizeWithLlm: boolean;
  disabled: boolean;
  onTitleChange: (value: string) => void;
  onSourceNameChange: (value: string) => void;
  onUrlChange: (value: string) => void;
  onTextChange: (value: string) => void;
  onEngagementChange: (key: keyof ManualEngagementDraft, value: string) => void;
  onPersonalNoteChange: (value: string) => void;
  onManualTagsChange: (value: string) => void;
  onSaveItemChange: (value: boolean) => void;
  onClassifyWithLlmChange: (value: boolean) => void;
  onSummarizeWithLlmChange: (value: boolean) => void;
  onSubmit: () => void;
}) {
  const hasLlmAction = classifyWithLlm || summarizeWithLlm;
  const manualTagCount = splitTerms(manualTags).length;
  const tagsWithinLimit = manualTagCount <= MANUAL_TAG_LIMIT;
  const submitLabel = hasLlmAction
    ? `Submit & ${[
        classifyWithLlm ? "Classify" : null,
        summarizeWithLlm ? "Summarize" : null,
      ]
        .filter(Boolean)
        .join(" & ")}`
    : "Submit";

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Manual Submission</h2>
        <Send size={16} aria-hidden="true" />
      </div>
      <div className="form-panel">
        <label className="field-label" htmlFor="manual-title">
          Title, optional
        </label>
        <input
          id="manual-title"
          className="field"
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
          maxLength={MANUAL_TITLE_MAX_LENGTH}
          disabled={disabled}
          placeholder="Paste an AI item title or leave blank"
        />
        <label className="field-label" htmlFor="manual-source-name">
          Source name
        </label>
        <input
          id="manual-source-name"
          className="field"
          value={sourceName}
          onChange={(event) => onSourceNameChange(event.target.value)}
          maxLength={MANUAL_SOURCE_NAME_MAX_LENGTH}
          disabled={disabled}
          placeholder="Manual Submission"
        />
        <label className="field-label" htmlFor="manual-url">
          URL
        </label>
        <input
          id="manual-url"
          className="field"
          value={url}
          onChange={(event) => onUrlChange(event.target.value)}
          disabled={disabled}
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
          maxLength={MANUAL_TEXT_MAX_LENGTH}
          disabled={disabled}
          placeholder="Optional context for classification and summary"
        />
        <div className="field-meta">
          <span>{text.length.toLocaleString()} / {MANUAL_TEXT_MAX_LENGTH.toLocaleString()}</span>
          {hasLlmAction ? (
            <span>Kimi receives submitted title, URL, source, and notes.</span>
          ) : null}
        </div>
        <div className="manual-engagement-grid" aria-label="Public engagement metrics">
          {manualEngagementFields.map((field) => (
            <label className="weight-field" key={field.key}>
              <span className="field-label">{field.label}</span>
              <input
                className="field"
                type="number"
                inputMode="numeric"
                min="0"
                step="1"
                value={engagement[field.key]}
                onChange={(event) => onEngagementChange(field.key, event.target.value)}
                disabled={disabled}
              />
            </label>
          ))}
        </div>
        <label className="field-label" htmlFor="manual-personal-note">
          Personal note
        </label>
        <textarea
          id="manual-personal-note"
          className="field textarea"
          value={personalNote}
          onChange={(event) => onPersonalNoteChange(event.target.value)}
          maxLength={MANUAL_PERSONAL_NOTE_MAX_LENGTH}
          disabled={disabled}
          placeholder="Private note for your reading list"
        />
        <div className="field-meta">
          <span>
            {personalNote.length.toLocaleString()} /{" "}
            {MANUAL_PERSONAL_NOTE_MAX_LENGTH.toLocaleString()}
          </span>
        </div>
        <label className="field-label" htmlFor="manual-tags">
          Manual tags
        </label>
        <input
          id="manual-tags"
          className="field"
          value={manualTags}
          onChange={(event) => onManualTagsChange(event.target.value)}
          disabled={disabled}
          placeholder="agent, market impact"
        />
        <div className={tagsWithinLimit ? "field-meta" : "field-meta source-error"}>
          <span>
            {manualTagCount} / {MANUAL_TAG_LIMIT} tags
          </span>
        </div>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={saveItem}
            onChange={(event) => onSaveItemChange(event.target.checked)}
            disabled={disabled}
          />
          Save to reading list
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={classifyWithLlm}
            onChange={(event) => onClassifyWithLlmChange(event.target.checked)}
            disabled={disabled}
          />
          Classify with Kimi
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={summarizeWithLlm}
            onChange={(event) => onSummarizeWithLlmChange(event.target.checked)}
            disabled={disabled}
          />
          Summarize with Kimi
        </label>
        <button
          className="button primary"
          onClick={onSubmit}
          disabled={disabled || !tagsWithinLimit}
        >
          {disabled ? (
            <Loader2 className="spin" size={16} />
          ) : hasLlmAction ? (
            <Bot size={16} />
          ) : (
            <Send size={16} />
          )}
          {submitLabel}
        </button>
      </div>
    </section>
  );
}

function StockTable({
  stocks,
  signalSummaries,
  stockBriefing,
  stockPriceSnapshot,
  stockLlmSummary,
  eventClusters,
  selectedTicker,
  busyStockTicker,
  busyStockSummaryTicker,
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
  onExplainStock,
  onUpdateStock,
  onMoveStock,
  onDeleteStock,
  onSubmit,
}: {
  stocks: StockWatchlistItem[];
  signalSummaries: StockSignalSummary[];
  stockBriefing: StockBriefing | null;
  stockPriceSnapshot: StockMarketSnapshot | null;
  stockLlmSummary: StockBriefingLlmSummary | null;
  eventClusters: EventCluster[];
  selectedTicker: string | null;
  busyStockTicker: string | null;
  busyStockSummaryTicker: string | null;
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
  onExplainStock: (ticker: string) => void;
  onUpdateStock: (
    ticker: string,
    payload: Partial<Omit<StockWatchlistItem, "ticker">>,
  ) => void;
  onMoveStock: (ticker: string, direction: "up" | "down") => void;
  onDeleteStock: (ticker: string) => void;
  onSubmit: () => void;
}) {
  const signalMap = new Map(signalSummaries.map((summary) => [summary.stock.ticker, summary]));
  const [sortMode, setSortMode] = useState<StockSortMode>("attention");
  const displayStocks = orderStocksForTable(stocks, signalSummaries, sortMode);
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
      company_name: detailDraft.company_name.trim() || selectedStock.company_name,
      exchange: detailDraft.exchange.trim(),
      sector: detailDraft.sector.trim(),
      industry: detailDraft.industry.trim(),
      market_cap_usd: parseOptionalNumber(detailDraft.market_cap_usd),
      group_name: detailDraft.group_name.trim(),
      related_keywords: splitTerms(detailDraft.related_keywords),
      related_companies: splitTerms(detailDraft.related_companies),
      related_ai_themes: splitTerms(detailDraft.related_ai_themes),
      notes: detailDraft.notes.trim() || null,
    };
    if (portfolioFieldsEnabled) {
      payload.is_holding = detailDraft.is_holding;
      payload.shares = parseOptionalNumber(detailDraft.shares);
      payload.average_cost = parseOptionalNumber(detailDraft.average_cost);
    } else {
      payload.is_holding = false;
      payload.shares = null;
      payload.average_cost = null;
    }
    onUpdateStock(selectedStock.ticker, payload);
  };

  const reorderStock = (stock: StockWatchlistItem, direction: "up" | "down") => {
    onMoveStock(stock.ticker, direction);
  };

  const canMoveStock = (stock: StockWatchlistItem, direction: "up" | "down") => {
    if (sortMode !== "watchlist") {
      return false;
    }
    const peers = displayStocks.filter((item) => item.is_pinned === stock.is_pinned);
    const index = peers.findIndex((item) => item.ticker === stock.ticker);
    return direction === "up" ? index > 0 : index >= 0 && index < peers.length - 1;
  };

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">AI Stock Watchlist</h2>
        <div className="table-actions">
          <div className="segmented-control" aria-label="Stock table sort">
            <button
              className={`segmented-button ${sortMode === "attention" ? "active" : ""}`}
              onClick={() => setSortMode("attention")}
              type="button"
            >
              Attention
            </button>
            <button
              className={`segmented-button ${sortMode === "watchlist" ? "active" : ""}`}
              onClick={() => setSortMode("watchlist")}
              type="button"
            >
              Watchlist
            </button>
          </div>
          <span className="small-muted">{stocks.length} tickers</span>
        </div>
      </div>
      <div className="form-panel compact-form">
        <input
          className="field"
          value={ticker}
          onChange={(event) => onTickerChange(event.target.value)}
          placeholder="Ticker or company"
          aria-label="Stock ticker or company"
        />
        <input
          className="field"
          value={company}
          onChange={(event) => onCompanyChange(event.target.value)}
          placeholder="Company (optional)"
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
              <th>Market Cap</th>
              <th>Priority</th>
              <th>AI Today</th>
              <th>High</th>
              <th>Latest Event</th>
              <th>Sentiment</th>
              <th>Attention</th>
              <th>Last Updated</th>
              <th>Themes</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {displayStocks.map((stock) => {
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
                  <td>{formatMarketCap(stock.market_cap_usd)}</td>
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
                  <td>{summary?.today_signal_count ?? 0}</td>
                  <td>{summary?.high_impact_count ?? 0}</td>
                  <td className="table-event-cell">
                    {summary?.latest_event_title ?? "--"}
                    {summary?.latest_event_at ? (
                      <div className="small-muted">{formatDate(summary.latest_event_at)}</div>
                    ) : null}
                  </td>
                  <td>{formatDominantSentiment(summary?.sentiment_counts)}</td>
                  <td className="table-attention-cell">
                    <span>{Math.round((summary?.attention_score ?? 0) * 100)}</span>
                    {summary?.attention_reasons.length ? (
                      <div className="small-muted">
                        {summary.attention_reasons.slice(0, 2).join(" · ")}
                      </div>
                    ) : null}
                  </td>
                  <td>
                    {summary?.last_updated_at ? formatDate(summary.last_updated_at) : "--"}
                  </td>
                  <td>{stock.related_ai_themes.slice(0, 2).join(", ")}</td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="button icon-button"
                        onClick={() => reorderStock(stock, "up")}
                        disabled={disabled || deleting || !canMoveStock(stock, "up")}
                        title={
                          sortMode === "watchlist"
                            ? `Move ${stock.ticker} up`
                            : "Switch to watchlist order to reorder"
                        }
                        aria-label={`Move ${stock.ticker} up`}
                      >
                        {deleting ? <Loader2 className="spin" size={16} /> : <ChevronUp size={16} />}
                      </button>
                      <button
                        className="button icon-button"
                        onClick={() => reorderStock(stock, "down")}
                        disabled={disabled || deleting || !canMoveStock(stock, "down")}
                        title={
                          sortMode === "watchlist"
                            ? `Move ${stock.ticker} down`
                            : "Switch to watchlist order to reorder"
                        }
                        aria-label={`Move ${stock.ticker} down`}
                      >
                        {deleting ? (
                          <Loader2 className="spin" size={16} />
                        ) : (
                          <ChevronDown size={16} />
                        )}
                      </button>
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
        priceSnapshot={stockPriceSnapshot}
        llmSummary={stockLlmSummary}
        eventClusters={eventClusters}
        loading={busyStockTicker === selectedTicker && selectedTicker !== null}
        busyLlmSummary={busyStockSummaryTicker === selectedTicker && selectedTicker !== null}
        selectedTicker={selectedTicker}
        onExplainStock={onExplainStock}
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
          <span className="field-label">Display Name</span>
          <input
            className="field"
            value={draft.company_name}
            onChange={(event) => onDraftChange("company_name", event.target.value)}
            disabled={disabled}
          />
        </label>
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
          <span className="field-label">Market Cap USD</span>
          <input
            className="field"
            type="number"
            min="0"
            step="any"
            inputMode="decimal"
            value={draft.market_cap_usd}
            onChange={(event) => onDraftChange("market_cap_usd", event.target.value)}
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
      <div className="stock-detail-grid">
        <label className="weight-field">
          <span className="field-label">AI Themes</span>
          <input
            className="field"
            value={draft.related_ai_themes}
            onChange={(event) => onDraftChange("related_ai_themes", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Keywords</span>
          <input
            className="field"
            value={draft.related_keywords}
            onChange={(event) => onDraftChange("related_keywords", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Related Companies</span>
          <input
            className="field"
            value={draft.related_companies}
            onChange={(event) => onDraftChange("related_companies", event.target.value)}
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
  priceSnapshot,
  llmSummary,
  eventClusters,
  loading,
  busyLlmSummary,
  selectedTicker,
  onExplainStock,
}: {
  briefing: StockBriefing | null;
  priceSnapshot: StockMarketSnapshot | null;
  llmSummary: StockBriefingLlmSummary | null;
  eventClusters: EventCluster[];
  loading: boolean;
  busyLlmSummary: boolean;
  selectedTicker: string | null;
  onExplainStock: (ticker: string) => void;
}) {
  const [activeTab, setActiveTab] = useState<StockDetailTabKey>("overview");

  useEffect(() => {
    setActiveTab("overview");
  }, [selectedTicker]);

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

  const relatedClusters = eventClusters
    .filter((cluster) => cluster.tickers.includes(briefing.stock.ticker))
    .slice(0, 4);
  const personalSignalItems = collectStockPersonalSignalItems(briefing);

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
        <div className="cluster-explanation-actions">
          <button
            className="button secondary"
            onClick={() => onExplainStock(briefing.stock.ticker)}
            disabled={busyLlmSummary}
          >
            {busyLlmSummary ? <Loader2 className="spin" size={16} /> : <Bot size={16} />}
            Explain
          </button>
          <span className={`urgency urgency-${briefing.urgency}`}>{briefing.urgency}</span>
        </div>
      </div>

      <div className="stock-detail-tabs" role="tablist" aria-label="Stock detail sections">
        {STOCK_DETAIL_TABS.map((tab) => (
          <button
            className={`stock-detail-tab ${activeTab === tab.key ? "active" : ""}`}
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            role="tab"
            aria-selected={activeTab === tab.key}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" ? (
        <div className="stock-detail-tab-panel">
          <div className="score-grid">
            <div className="score-cell">
              <span className="score-label">Price</span>
              <span className="score-value">
                {formatPrice(briefing.market?.latest?.close_price)}
              </span>
            </div>
            <div className="score-cell">
              <span className="score-label">Change</span>
              <span className={`score-value ${marketChangeClass(briefing.market?.change ?? null)}`}>
                {formatChange(briefing.market)}
              </span>
            </div>
            <div className="score-cell">
              <span className="score-label">Volume</span>
              <span
                className={`score-value ${marketChangeClass(
                  briefing.market?.volume_change_percent ?? null,
                )}`}
              >
                {formatPercentChange(briefing.market?.volume_change_percent)}
              </span>
            </div>
            <div className="score-cell">
              <span className="score-label">Signals</span>
              <span className="score-value">{briefing.signal_count}</span>
            </div>
            <div className="score-cell">
              <span className="score-label">Attention</span>
              <span className="score-value">{Math.round(briefing.attention_score * 100)}</span>
              {briefing.attention_reasons.length ? (
                <span className="score-note">{briefing.attention_reasons[0]}</span>
              ) : null}
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

          <StockAttentionDrivers briefing={briefing} />

          <StockPriceChart market={priceSnapshot ?? briefing.market} />

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
        </div>
      ) : null}

      {activeTab === "signals" ? (
        <div className="stock-detail-tab-panel">
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
                      <span className="badge">
                        Price: {formatCategoryLabel(entry.price_reaction)}
                      </span>
                      {entry.event_price_change_percent !== null ? (
                        <span
                          className={`badge ${marketChangeClass(entry.event_price_change_percent)}`}
                        >
                          Event move {formatPercentChange(entry.event_price_change_percent)}
                          {entry.event_price_date ? ` on ${formatDate(entry.event_price_date)}` : ""}
                        </span>
                      ) : null}
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
      ) : null}

      {activeTab === "clusters" ? (
        <div className="stock-detail-tab-panel">
          <div className="digest-section">
            <div className="digest-section-title">Related Event Clusters</div>
            {relatedClusters.length ? (
              <div className="impact-event-list">
                {relatedClusters.map((cluster) => (
                  <a
                    className="impact-event-row"
                    href={cluster.representative_item.url}
                    target="_blank"
                    rel="noreferrer"
                    key={cluster.cluster_key}
                  >
                    <div>
                      <div className="digest-link">{cluster.title}</div>
                      <div className="small-muted">
                        {cluster.item_count} item{cluster.item_count === 1 ? "" : "s"} ·{" "}
                        {cluster.sources.slice(0, 3).join(", ")} · confidence{" "}
                        {Math.round(cluster.confidence * 100)}
                      </div>
                      <div className="timeline-reason">{cluster.main_summary}</div>
                    </div>
                  </a>
                ))}
              </div>
            ) : (
              <div className="empty-state">No stock-related event clusters yet.</div>
            )}
          </div>
        </div>
      ) : null}

      {activeTab === "notes" ? (
        <StockNotesPanel briefing={briefing} personalSignalItems={personalSignalItems} />
      ) : null}

      {activeTab === "summary" ? (
        <div className="stock-detail-tab-panel">
          {llmSummary ? (
            <StockLlmSummaryPanel summary={llmSummary} />
          ) : (
            <div className="empty-state">No LLM stock summary generated yet.</div>
          )}
        </div>
      ) : null}
    </div>
  );
}

function StockLlmSummaryPanel({ summary }: { summary: StockBriefingLlmSummary }) {
  const sections = parseStockLlmSummarySections(summary.summary);

  return (
    <div className="digest-section">
      <div className="digest-section-title">LLM Summary</div>
      <div className="stock-llm-summary-grid">
        {sections.map((section) => (
          <section className="stock-llm-summary-section" key={section.heading}>
            <div className="stock-llm-summary-heading">{section.heading}</div>
            <div className="llm-explanation">
              {section.body.map((line, index) => (
                <p key={`${section.heading}-${index}`}>{line}</p>
              ))}
            </div>
          </section>
        ))}
      </div>
      <div className="small-muted">
        {summary.model} · {summary.total_tokens} tokens
      </div>
    </div>
  );
}

const STOCK_LLM_SUMMARY_HEADINGS = [
  "What happened",
  "Why it matters",
  "Possible market relevance",
  "Uncertainties",
];

function parseStockLlmSummarySections(summary: string): StockLlmSummarySection[] {
  const sections = STOCK_LLM_SUMMARY_HEADINGS.map((heading) => ({ heading, body: [] as string[] }));
  let currentIndex = -1;
  const fallbackLines: string[] = [];

  for (const line of splitSummaryLines(summary)) {
    const headingMatch = matchStockLlmSummaryHeading(line);
    if (headingMatch) {
      currentIndex = headingMatch.index;
      if (headingMatch.remainder) {
        sections[currentIndex]!.body.push(headingMatch.remainder);
      }
      continue;
    }

    if (currentIndex >= 0) {
      sections[currentIndex]!.body.push(line);
    } else {
      fallbackLines.push(line);
    }
  }

  const parsedSections = sections.filter((section) => section.body.length > 0);
  if (parsedSections.length >= 2) {
    return parsedSections;
  }

  const body = fallbackLines.length ? fallbackLines : splitSummaryLines(summary);
  return [{ heading: "Summary", body: body.length ? body : ["No summary text returned."] }];
}

function matchStockLlmSummaryHeading(line: string): { index: number; remainder: string } | null {
  for (const [index, heading] of STOCK_LLM_SUMMARY_HEADINGS.entries()) {
    const pattern = new RegExp(
      `^(?:#+\\s*)?(?:\\*\\*)?${escapeRegExp(heading)}(?:\\*\\*)?\\s*:?\\s*(.*)$`,
      "i",
    );
    const match = line.match(pattern);
    if (match) {
      return { index, remainder: (match[1] ?? "").trim() };
    }
  }
  return null;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function StockAttentionDrivers({ briefing }: { briefing: StockBriefing }) {
  const drivers = briefing.attention_reasons.length
    ? briefing.attention_reasons
    : ["No strong attention driver yet"];
  return (
    <div className="stock-attention-panel">
      <div className="section-header">
        <div>
          <div className="digest-section-title">Attention Drivers</div>
          <div className="small-muted">
            Explains why this ticker ranks where it does in attention mode.
          </div>
        </div>
        <span className="badge">{Math.round(briefing.attention_score * 100)} attention</span>
      </div>
      <div className="digest-coverage">
        <span className="badge">{briefing.signal_count} signals</span>
        <span className="badge">{briefing.today_signal_count} today</span>
        <span className="badge alert-badge">{briefing.high_impact_count} high impact</span>
        {briefing.last_updated_at ? (
          <span className="badge muted-badge">updated {formatDate(briefing.last_updated_at)}</span>
        ) : null}
      </div>
      {briefing.attention_components.length ? (
        <div className="attention-component-grid">
          {briefing.attention_components.map((component) => (
            <div className="attention-component" key={component.key}>
              <div className="attention-component-head">
                <span>{component.label}</span>
                <span>{Math.round(component.contribution * 100)} pts</span>
              </div>
              <div className="score-note">
                {Math.round(component.value * 100)} value · {Math.round(component.weight * 100)}%
                weight
              </div>
            </div>
          ))}
        </div>
      ) : null}
      <div className="attention-driver-list">
        {drivers.map((driver) => (
          <div className="attention-driver-row" key={driver}>
            {driver}
          </div>
        ))}
      </div>
    </div>
  );
}

const STOCK_PRICE_RANGES: { key: StockPriceRangeKey; label: string; days: number }[] = [
  { key: "1d", label: "1D", days: 1 },
  { key: "5d", label: "5D", days: 5 },
  { key: "1m", label: "1M", days: 31 },
  { key: "6m", label: "6M", days: 183 },
  { key: "1y", label: "1Y", days: 366 },
];

const STOCK_DETAIL_TABS: { key: StockDetailTabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "signals", label: "Signals" },
  { key: "clusters", label: "Clusters" },
  { key: "notes", label: "Notes" },
  { key: "summary", label: "Summary" },
];

function StockNotesPanel({
  briefing,
  personalSignalItems,
}: {
  briefing: StockBriefing;
  personalSignalItems: FeedItem[];
}) {
  return (
    <div className="stock-detail-tab-panel">
      <div className="stock-detail-grid-view">
        <div className="digest-section">
          <div className="digest-section-title">Watchlist Notes</div>
          {briefing.stock.notes ? (
            <div className="summary">{briefing.stock.notes}</div>
          ) : (
            <div className="empty-state">No watchlist notes saved for {briefing.stock.ticker}.</div>
          )}
        </div>
        <div className="digest-section">
          <div className="digest-section-title">Personal Context</div>
          <div className="badges">
            <span className="badge">{personalSignalItems.length} personal item{personalSignalItems.length === 1 ? "" : "s"}</span>
            <span className="badge">
              {personalSignalItems.filter((item) => item.is_saved && !item.is_read).length} read later
            </span>
            <span className="badge">
              {uniqueManualTags(personalSignalItems).length} manual tags
            </span>
          </div>
        </div>
      </div>
      <div className="stock-timeline">
        {personalSignalItems.length ? (
          personalSignalItems.map((item) => (
            <a
              className="timeline-row"
              href={item.url}
              target="_blank"
              rel="noreferrer"
              key={item.id}
            >
              <div>
                <div className="timeline-title">{item.title}</div>
                <div className="small-muted">
                  {item.source_name}
                  {item.published_at ? ` · ${formatDate(item.published_at)}` : ""}
                </div>
                <div className="badges">
                  {item.is_saved ? <span className="badge">saved</span> : null}
                  {item.is_saved && !item.is_read ? (
                    <span className="badge">read later</span>
                  ) : null}
                  {item.is_read ? <span className="badge muted-badge">read</span> : null}
                  {item.is_important ? <span className="badge alert-badge">important</span> : null}
                  {item.manual_tags.map((tag) => (
                    <span className="badge stock" key={tag}>
                      {tag}
                    </span>
                  ))}
                </div>
                {item.personal_note ? <div className="saved-note">{item.personal_note}</div> : null}
                {item.summary_short || item.why_it_matters ? (
                  <div className="timeline-reason">{item.summary_short || item.why_it_matters}</div>
                ) : null}
              </div>
              <div className="timeline-score">{Math.round(item.stock_impact_score * 100)}</div>
            </a>
          ))
        ) : (
          <div className="empty-state">
            No saved articles, private notes, or manual tags are attached to recent{" "}
            {briefing.stock.ticker} signals yet.
          </div>
        )}
      </div>
    </div>
  );
}

function collectStockPersonalSignalItems(briefing: StockBriefing): FeedItem[] {
  return briefing.recent_timeline
    .map((entry) => entry.item)
    .filter(
      (item) =>
        item.is_saved ||
        item.is_important ||
        Boolean(item.personal_note) ||
        item.manual_tags.length > 0,
    );
}

function uniqueManualTags(items: FeedItem[]): string[] {
  return Array.from(new Set(items.flatMap((item) => item.manual_tags)));
}

function StockPriceChart({ market }: { market: StockMarketSnapshot | null }) {
  const [rangeKey, setRangeKey] = useState<StockPriceRangeKey>("1m");
  const history = market?.history ?? [];
  const selectedRange =
    STOCK_PRICE_RANGES.find((range) => range.key === rangeKey) ?? STOCK_PRICE_RANGES[1]!;
  const latestHistoryDate = parsePriceDate(history[history.length - 1]?.price_date);
  const rangedHistory =
    latestHistoryDate === null
      ? history
      : history.filter((point) => {
          const pointDate = parsePriceDate(point.price_date);
          if (pointDate === null) {
            return true;
          }
          const ageMs = latestHistoryDate.getTime() - pointDate.getTime();
          return ageMs <= selectedRange.days * 24 * 60 * 60 * 1000;
        });
  const visibleHistory =
    rangeKey === "1d"
      ? (rangedHistory.length ? rangedHistory : history).slice(-1)
      : rangedHistory.length >= 2
        ? rangedHistory
        : history;

  if (!visibleHistory.length) {
    return <div className="empty-state">No price history loaded yet.</div>;
  }

  const width = 280;
  const height = 76;
  const padding = 8;
  const isSinglePoint = visibleHistory.length === 1;
  const closes = visibleHistory.map((point) => point.close_price);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const chartPoints = visibleHistory.map((point, index) => {
    const x = isSinglePoint
      ? width / 2
      : padding + (index / (visibleHistory.length - 1)) * (width - padding * 2);
    const y = isSinglePoint
      ? height / 2
      : height - padding - ((point.close_price - min) / range) * (height - padding * 2);
    return { x, y };
  });
  const points = chartPoints.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
  const latestChartPoint = chartPoints[chartPoints.length - 1]!;
  const first = visibleHistory[0]!;
  const latest = visibleHistory[visibleHistory.length - 1]!;
  const trendClass = marketChangeClass(market?.change ?? null);

  return (
    <div className="price-chart" aria-label="Recent stock price chart">
      <div className="price-chart-head">
        <span className="digest-section-title">Price History</span>
        <span className={`small-muted ${trendClass}`}>{formatChange(market)}</span>
      </div>
      <div className="price-range-controls" aria-label="Price range">
        {STOCK_PRICE_RANGES.map((rangeOption) => (
          <button
            className={`price-range-button ${rangeKey === rangeOption.key ? "active" : ""}`}
            key={rangeOption.key}
            onClick={() => setRangeKey(rangeOption.key)}
            type="button"
          >
            {rangeOption.label}
          </button>
        ))}
      </div>
      {rangeKey === "1d" ? (
        <div className="price-chart-note">
          Intraday feed not configured; showing latest daily close.
        </div>
      ) : null}
      <svg className="price-chart-svg" viewBox={`0 0 ${width} ${height}`} role="img">
        {isSinglePoint ? null : <polyline className="price-chart-line" points={points} />}
        <circle
          className="price-chart-dot"
          cx={latestChartPoint.x}
          cy={latestChartPoint.y}
          r="3"
        />
      </svg>
      <div className="price-chart-meta">
        {isSinglePoint ? (
          <span>
            Latest close: {latest.price_date} · {formatPrice(latest.close_price)}
          </span>
        ) : (
          <>
            <span>
              {first.price_date} · {formatPrice(first.close_price)}
            </span>
            <span>
              {latest.price_date} · {formatPrice(latest.close_price)}
            </span>
          </>
        )}
      </div>
    </div>
  );
}

function parsePriceDate(value: string | undefined): Date | null {
  if (!value) {
    return null;
  }
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? null : date;
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
    payload: Partial<Omit<CompanyWatchlistItem, "company_key">>,
  ) => void;
  onDelete: (companyKey: string) => void;
  onSubmit: () => void;
}) {
  const selectedCompany = companies.find((item) => item.company_key === selectedCompanyKey) ?? null;
  const [detailDraft, setDetailDraft] = useState<CompanyDetailDraft>(() =>
    companyToDetailDraft(selectedCompany),
  );

  useEffect(() => {
    setDetailDraft(companyToDetailDraft(selectedCompany));
  }, [selectedCompany]);

  const updateDetailDraft = (key: keyof CompanyDetailDraft, value: string) => {
    setDetailDraft((current) => ({ ...current, [key]: value }));
  };

  const saveCompanyDetails = () => {
    if (!selectedCompany) {
      return;
    }
    onUpdate(selectedCompany.company_key, {
      company_name: detailDraft.company_name.trim() || selectedCompany.company_name,
      ticker: detailDraft.ticker.trim() || null,
      category: detailDraft.category.trim() || selectedCompany.category,
      related_terms: splitTerms(detailDraft.related_terms),
      notes: detailDraft.notes.trim() || null,
    });
  };

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
      <CompanyDetailEditor
        company={selectedCompany}
        draft={detailDraft}
        disabled={
          disabled ||
          (selectedCompany
            ? busyWatchlistKey === `company:${selectedCompany.company_key}`
            : false)
        }
        onDraftChange={updateDetailDraft}
        onSave={saveCompanyDetails}
      />
      <CompanyBriefingPanel
        briefing={briefing}
        loading={busyCompanyBriefing === selectedCompanyKey && selectedCompanyKey !== null}
        selectedCompanyKey={selectedCompanyKey}
      />
    </section>
  );
}

function CompanyDetailEditor({
  company,
  draft,
  disabled,
  onDraftChange,
  onSave,
}: {
  company: CompanyWatchlistItem | null;
  draft: CompanyDetailDraft;
  disabled: boolean;
  onDraftChange: (key: keyof CompanyDetailDraft, value: string) => void;
  onSave: () => void;
}) {
  if (!company) {
    return <div className="empty-state">Select a company to edit watchlist details.</div>;
  }

  return (
    <div className="form-panel stock-detail-form">
      <div className="section-header">
        <div>
          <h3 className="section-title">{company.company_name} details</h3>
          <div className="small-muted">{company.company_key}</div>
        </div>
        <span className="badge">{company.include_in_digest ? "digest" : "muted"}</span>
      </div>
      <div className="stock-detail-grid">
        <label className="weight-field">
          <span className="field-label">Company Name</span>
          <input
            className="field"
            value={draft.company_name}
            onChange={(event) => onDraftChange("company_name", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Ticker</span>
          <input
            className="field"
            value={draft.ticker}
            onChange={(event) => onDraftChange("ticker", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Category</span>
          <select
            className="field"
            value={draft.category}
            onChange={(event) => onDraftChange("category", event.target.value)}
            disabled={disabled}
          >
            <option value="ai_company">AI company</option>
            <option value="semiconductor">Semiconductor</option>
            <option value="cloud_ai">Cloud AI</option>
            <option value="ai_platform">AI platform</option>
            <option value="ai_lab">AI lab</option>
          </select>
        </label>
        <label className="weight-field">
          <span className="field-label">Related Terms</span>
          <input
            className="field"
            value={draft.related_terms}
            onChange={(event) => onDraftChange("related_terms", event.target.value)}
            disabled={disabled}
          />
        </label>
      </div>
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
          {disabled ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
          Save
        </button>
      </div>
    </div>
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

      <BriefingImpactMetrics
        itemCount={briefing.item_count}
        highImpactCount={briefing.high_impact_count}
        averageImportanceScore={briefing.average_importance_score}
      />

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
    payload: Partial<Omit<TopicWatchlistItem, "topic">>,
  ) => void;
  onDeleteTopic: (topic: string) => void;
  onSubmit: () => void;
}) {
  const selectedTopicItem = topics.find((item) => item.topic === selectedTopic) ?? null;
  const [detailDraft, setDetailDraft] = useState<TopicDetailDraft>(() =>
    topicToDetailDraft(selectedTopicItem),
  );

  useEffect(() => {
    setDetailDraft(topicToDetailDraft(selectedTopicItem));
  }, [selectedTopicItem]);

  const updateDetailDraft = (key: keyof TopicDetailDraft, value: string) => {
    setDetailDraft((current) => ({ ...current, [key]: value }));
  };

  const saveTopicDetails = () => {
    if (!selectedTopicItem) {
      return;
    }
    onUpdateTopic(selectedTopicItem.topic, {
      label: detailDraft.label.trim() || selectedTopicItem.label,
      category: detailDraft.category.trim() || selectedTopicItem.category,
      related_terms: splitTerms(detailDraft.related_terms),
      notes: detailDraft.notes.trim() || null,
    });
  };

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
      <TopicDetailEditor
        topic={selectedTopicItem}
        draft={detailDraft}
        disabled={
          disabled ||
          (selectedTopicItem
            ? busyWatchlistKey === `topic:${selectedTopicItem.topic}`
            : false)
        }
        onDraftChange={updateDetailDraft}
        onSave={saveTopicDetails}
      />
      <TopicBriefingPanel
        briefing={topicBriefing}
        loading={busyTopicBriefing === selectedTopic && selectedTopic !== null}
        selectedTopic={selectedTopic}
      />
    </section>
  );
}

function TopicDetailEditor({
  topic,
  draft,
  disabled,
  onDraftChange,
  onSave,
}: {
  topic: TopicWatchlistItem | null;
  draft: TopicDetailDraft;
  disabled: boolean;
  onDraftChange: (key: keyof TopicDetailDraft, value: string) => void;
  onSave: () => void;
}) {
  if (!topic) {
    return <div className="empty-state">Select a topic to edit watchlist details.</div>;
  }

  return (
    <div className="form-panel stock-detail-form">
      <div className="section-header">
        <div>
          <h3 className="section-title">{topic.label} details</h3>
          <div className="small-muted">{topic.topic}</div>
        </div>
        <span className="badge">{topic.include_in_digest ? "digest" : "muted"}</span>
      </div>
      <div className="stock-detail-grid">
        <label className="weight-field">
          <span className="field-label">Label</span>
          <input
            className="field"
            value={draft.label}
            onChange={(event) => onDraftChange("label", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Category</span>
          <select
            className="field"
            value={draft.category}
            onChange={(event) => onDraftChange("category", event.target.value)}
            disabled={disabled}
          >
            <option value="technical_trend">Trend</option>
            <option value="research">Research</option>
            <option value="product">Product</option>
            <option value="stock_company_event">Stock</option>
            <option value="social_trend">Social</option>
          </select>
        </label>
        <label className="weight-field">
          <span className="field-label">Related Terms</span>
          <input
            className="field"
            value={draft.related_terms}
            onChange={(event) => onDraftChange("related_terms", event.target.value)}
            disabled={disabled}
          />
        </label>
      </div>
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
          {disabled ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
          Save
        </button>
      </div>
    </div>
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
          <div className="small-muted">{briefing.definition}</div>
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

      <BriefingImpactMetrics
        itemCount={briefing.item_count}
        highImpactCount={briefing.high_impact_count}
        averageImportanceScore={briefing.average_importance_score}
      />

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
        <TopicBriefingPaperLinks
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

function BriefingImpactMetrics({
  itemCount,
  highImpactCount,
  averageImportanceScore,
  averageNoveltyScore,
}: {
  itemCount: number;
  highImpactCount: number;
  averageImportanceScore: number;
  averageNoveltyScore?: number;
}) {
  return (
    <div className="score-grid">
      <div className="score-cell">
        <span className="score-label">Items</span>
        <span className="score-value">{itemCount}</span>
      </div>
      <div className="score-cell">
        <span className="score-label">High Impact</span>
        <span className="score-value">{highImpactCount}</span>
      </div>
      <div className="score-cell">
        <span className="score-label">Avg Importance</span>
        <span className="score-value">{Math.round(averageImportanceScore * 100)}</span>
      </div>
      {averageNoveltyScore !== undefined ? (
        <div className="score-cell">
          <span className="score-label">Avg Novelty</span>
          <span className="score-value">{Math.round(averageNoveltyScore * 100)}</span>
        </div>
      ) : null}
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

function TopicBriefingPaperLinks({
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
          {items.slice(0, 5).map((item) => {
            const insights = parseResearchInsights(item);
            return (
              <div className="digest-preview-item" key={item.id}>
                <a className="digest-link" href={item.url} target="_blank" rel="noreferrer">
                  {item.title}
                </a>
                <div className="small-muted">
                  {item.source_name}
                  {item.published_at ? ` · ${formatDate(item.published_at)}` : ""}
                </div>
                {insights ? (
                  <ResearchInsightsPanel insights={insights} compact />
                ) : item.summary_short || item.why_it_matters ? (
                  <div className="digest-item-summary">
                    {item.summary_short || item.why_it_matters}
                  </div>
                ) : null}
              </div>
            );
          })}
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
    payload: Partial<Omit<ProductWatchlistItem, "category">>,
  ) => void;
  onDelete: (category: string) => void;
  onSubmit: () => void;
}) {
  const selectedProduct = items.find((item) => item.category === selectedCategory) ?? null;
  const [detailDraft, setDetailDraft] = useState<ProductDetailDraft>(() =>
    productToDetailDraft(selectedProduct),
  );

  useEffect(() => {
    setDetailDraft(productToDetailDraft(selectedProduct));
  }, [selectedProduct]);

  const updateDetailDraft = (key: keyof ProductDetailDraft, value: string) => {
    setDetailDraft((current) => ({ ...current, [key]: value }));
  };

  const saveProductDetails = () => {
    if (!selectedProduct) {
      return;
    }
    onUpdate(selectedProduct.category, {
      label: detailDraft.label.trim() || selectedProduct.label,
      related_terms: splitTerms(detailDraft.related_terms),
      notes: detailDraft.notes.trim() || null,
    });
  };

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
      <ProductDetailEditor
        product={selectedProduct}
        draft={detailDraft}
        disabled={
          disabled ||
          (selectedProduct
            ? busyWatchlistKey === `product:${selectedProduct.category}`
            : false)
        }
        onDraftChange={updateDetailDraft}
        onSave={saveProductDetails}
      />
      <ProductBriefingPanel
        briefing={briefing}
        loading={busyProductBriefing === selectedCategory && selectedCategory !== null}
        selectedCategory={selectedCategory}
      />
    </section>
  );
}

function ProductDetailEditor({
  product,
  draft,
  disabled,
  onDraftChange,
  onSave,
}: {
  product: ProductWatchlistItem | null;
  draft: ProductDetailDraft;
  disabled: boolean;
  onDraftChange: (key: keyof ProductDetailDraft, value: string) => void;
  onSave: () => void;
}) {
  if (!product) {
    return <div className="empty-state">Select a product category to edit details.</div>;
  }

  return (
    <div className="form-panel stock-detail-form">
      <div className="section-header">
        <div>
          <h3 className="section-title">{product.label} details</h3>
          <div className="small-muted">{product.category}</div>
        </div>
        <span className="badge">{product.include_in_digest ? "digest" : "muted"}</span>
      </div>
      <div className="stock-detail-grid">
        <label className="weight-field">
          <span className="field-label">Label</span>
          <input
            className="field"
            value={draft.label}
            onChange={(event) => onDraftChange("label", event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="weight-field">
          <span className="field-label">Related Terms</span>
          <input
            className="field"
            value={draft.related_terms}
            onChange={(event) => onDraftChange("related_terms", event.target.value)}
            disabled={disabled}
          />
        </label>
      </div>
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
          {disabled ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
          Save
        </button>
      </div>
    </div>
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

  const discoveryScores = new Map(
    briefing.discovery_scores.map((score) => [score.item_id, score]),
  );

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

      <BriefingImpactMetrics
        itemCount={briefing.item_count}
        highImpactCount={briefing.high_impact_count}
        averageImportanceScore={briefing.average_importance_score}
        averageNoveltyScore={briefing.average_novelty_score}
      />

      <div className="topic-briefing-grid">
        <TopicBriefingList
          title="Trending Sources"
          emptyText="No source activity yet."
          items={briefing.trending_sources.map(
            (source) => `${source.source_name} (${source.item_count})`,
          )}
        />
        <TopicBriefingList
          title="Use Cases"
          emptyText="No use-case classification yet."
          items={briefing.use_case_counts.map(
            (bucket) => `${bucket.source_name} (${bucket.item_count})`,
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
          title="Traction Signals"
          emptyText="No traction signals yet."
          items={briefing.traction_signals}
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
                  {formatProductDiscoveryNote(discoveryScores.get(item.id))}
                </div>
              </div>
              <div className="timeline-score">
                {Math.round((discoveryScores.get(item.id)?.score ?? item.importance_score) * 100)}
              </div>
            </a>
          ))
        ) : (
          <div className="empty-state">No product-category signals yet.</div>
        )}
      </div>
    </div>
  );
}

function IngestionActionButtons({
  activeOperation,
  disabled,
  onRunSource,
  labelMode = "long",
}: {
  activeOperation: DashboardOperation | null;
  disabled: boolean;
  onRunSource: (source: IngestionSource) => void;
  labelMode?: "short" | "long";
}) {
  return (
    <>
      {ingestionSourceActions.map((action) => {
        const Icon = action.icon;
        const operation: DashboardOperation = `ingest:${action.source}`;
        const running = activeOperation === operation;
        return (
          <button
            className="button"
            onClick={() => onRunSource(action.source)}
            disabled={disabled}
            title={action.title}
            type="button"
            key={action.source}
          >
            {running ? <Loader2 className="spin" size={16} /> : <Icon size={16} />}
            {labelMode === "short" ? action.shortLabel : action.label}
          </button>
        );
      })}
    </>
  );
}

function SourceTable({
  sources,
  runs,
  sourceFilter,
  runStatusFilter,
  runSourceFilter,
  lastCycleResult,
  blockedSources,
  sourceTemplate,
  name,
  type,
  accessMethod,
  baseUrl,
  pollingInterval,
  rateLimit,
  termsNotes,
  rawContentPolicy,
  disabled,
  busySourceId,
  activeOperation,
  onSourceTemplateChange,
  onNameChange,
  onTypeChange,
  onAccessMethodChange,
  onBaseUrlChange,
  onPollingIntervalChange,
  onRateLimitChange,
  onTermsNotesChange,
  onRawContentPolicyChange,
  onSourceFilterChange,
  onRunStatusFilterChange,
  onRunSourceFilterChange,
  onSubmit,
  onRunSource,
  onRunBuiltInSource,
  onToggleSource,
  onUpdateSource,
  onToggleSourceBlock,
  onDeleteSource,
}: {
  sources: SourceHealth[];
  runs: SourceRunHistoryItem[];
  sourceFilter: SourceHealthFilter;
  runStatusFilter: "all" | "failed";
  runSourceFilter: SourceHealth | null;
  lastCycleResult: ScheduledCycleResponse | null;
  blockedSources: string[];
  sourceTemplate: string;
  name: string;
  type: string;
  accessMethod: string;
  baseUrl: string;
  pollingInterval: string;
  rateLimit: string;
  termsNotes: string;
  rawContentPolicy: string;
  disabled: boolean;
  busySourceId: number | null;
  activeOperation: DashboardOperation | null;
  onSourceTemplateChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onTypeChange: (value: string) => void;
  onAccessMethodChange: (value: string) => void;
  onBaseUrlChange: (value: string) => void;
  onPollingIntervalChange: (value: string) => void;
  onRateLimitChange: (value: string) => void;
  onTermsNotesChange: (value: string) => void;
  onRawContentPolicyChange: (value: string) => void;
  onSourceFilterChange: (value: SourceHealthFilter) => void;
  onRunStatusFilterChange: (value: "all" | "failed") => void;
  onRunSourceFilterChange: (source: SourceHealth | null) => void;
  onSubmit: () => void;
  onRunSource: (source: SourceHealth) => void;
  onRunBuiltInSource: (source: IngestionSource) => void;
  onToggleSource: (source: SourceHealth) => void;
  onUpdateSource: (source: SourceHealth, payload: SourceUpdatePayload) => void;
  onToggleSourceBlock: (source: SourceHealth) => void;
  onDeleteSource: (source: SourceHealth) => void;
}) {
  const [drafts, setDrafts] = useState<Record<number, SourceDraft>>({});
  const selectedTemplate =
    sourceFollowTemplates.find((template) => template.key === sourceTemplate) ??
    sourceFollowTemplates[0];

  useEffect(() => {
    setDrafts(Object.fromEntries(sources.map((source) => [source.id, buildSourceDraft(source)])));
  }, [sources]);

  const setDraftValue = (
    sourceId: number,
    field: keyof SourceDraft,
    value: SourceDraft[keyof SourceDraft],
  ) => {
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
  const sourceHealthCounts = buildSourceHealthCounts(sources, blockedSources);
  const displayedSources = sources.filter((source) =>
    sourceMatchesHealthFilter(source, sourceFilter, blockedSources),
  );

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Source Health</h2>
        <DatabaseZap size={16} aria-hidden="true" />
      </div>
      <div className="source-run-panel">
        <div className="source-run-panel-head">
          <div>
            <div className="digest-section-title">Built-in Source Runs</div>
            <div className="small-muted">Stable APIs, public feeds, and configured stock sources</div>
          </div>
          <span className="tag">{ingestionSourceActions.length} runners</span>
        </div>
        <div className="source-run-toolbar" aria-label="Built-in source ingestion actions">
          <IngestionActionButtons
            activeOperation={activeOperation}
            disabled={disabled}
            onRunSource={onRunBuiltInSource}
          />
        </div>
      </div>
      <div className="form-panel compact-form source-follow-form">
        <select
          className="field"
          value={selectedTemplate.key}
          onChange={(event) => onSourceTemplateChange(event.target.value)}
          disabled={disabled}
          aria-label="Source template"
        >
          {sourceFollowTemplates.map((template) => (
            <option value={template.key} key={template.key}>
              {template.label}
            </option>
          ))}
        </select>
        <input
          className="field"
          placeholder={selectedTemplate.namePlaceholder}
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
          {sourceTypeOptions.map((option) => (
            <option value={option.value} key={option.value}>
              {option.label}
            </option>
          ))}
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
          placeholder={selectedTemplate.urlPlaceholder}
          value={baseUrl}
          onChange={(event) => onBaseUrlChange(event.target.value)}
          disabled={disabled}
        />
        <input
          className="field"
          placeholder="Polling"
          value={pollingInterval}
          onChange={(event) => onPollingIntervalChange(event.target.value)}
          disabled={disabled}
        />
        <input
          className="field"
          placeholder="Rate limit"
          value={rateLimit}
          onChange={(event) => onRateLimitChange(event.target.value)}
          disabled={disabled}
        />
        <input
          className="field"
          placeholder={selectedTemplate.termsPlaceholder}
          value={termsNotes}
          onChange={(event) => onTermsNotesChange(event.target.value)}
          disabled={disabled}
        />
        <input
          className="field"
          placeholder={selectedTemplate.policyPlaceholder}
          value={rawContentPolicy}
          onChange={(event) => onRawContentPolicyChange(event.target.value)}
          disabled={disabled}
        />
        <button className="button primary" onClick={onSubmit} disabled={disabled}>
          {disabled ? <Loader2 className="spin" size={16} /> : <Plus size={16} />}
          Follow
        </button>
      </div>
      <div className="source-health-summary" aria-label="Source health filters">
        {sourceHealthFilterOptions.map((option) => (
          <button
            className={`source-health-card ${sourceFilter === option.key ? "active" : ""}`}
            key={option.key}
            onClick={() => onSourceFilterChange(option.key)}
            type="button"
          >
            <span className="score-label">{option.label}</span>
            <span className="score-value">{sourceHealthCounts[option.key]}</span>
          </button>
        ))}
      </div>
      <div className="table-wrap">
        <table className="source-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Type</th>
              <th>Access</th>
              <th>Auth</th>
              <th>Enabled</th>
              <th>Priority</th>
              <th>Polling</th>
              <th>Rate Limit</th>
              <th>Terms Notes</th>
              <th>Policy</th>
              <th>Status</th>
              <th>Stored</th>
              <th>Quality</th>
              <th>Last Run</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {displayedSources.map((source) => {
              const draft = drafts[source.id] ?? buildSourceDraft(source);
              const changed = isSourceDraftChanged(source, draft);
              const saving = busySourceId === source.id;
              const failureCopy = `${source.failure_count} recent ${
                source.failure_count === 1 ? "failure" : "failures"
              }`;
              const blocked = sourceNameInList(source.name, blockedSources);
              return (
                <tr key={source.id}>
                  <td>
                    <input
                      className="field table-field source-name-field"
                      value={draft.name}
                      onChange={(event) => setDraftValue(source.id, "name", event.target.value)}
                    />
                    <input
                      className="field table-field source-url-field"
                      value={draft.base_url}
                      onChange={(event) => setDraftValue(source.id, "base_url", event.target.value)}
                      placeholder="URL or feed"
                    />
                  </td>
                  <td>
                    <select
                      className="field table-field source-short-field"
                      value={draft.type}
                      onChange={(event) => setDraftValue(source.id, "type", event.target.value)}
                    >
                      {sourceTypeOptions.map((option) => (
                        <option value={option.value} key={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select
                      className="field table-field source-short-field"
                      value={draft.access_method}
                      onChange={(event) =>
                        setDraftValue(source.id, "access_method", event.target.value)
                      }
                    >
                      <option value="rss">RSS</option>
                      <option value="official_api">Official API</option>
                      <option value="official_graphql_api">Official GraphQL API</option>
                      <option value="manual_watch">Manual watch</option>
                    </select>
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={draft.auth_required}
                      onChange={(event) =>
                        setDraftValue(source.id, "auth_required", event.target.checked)
                      }
                      aria-label={`Authentication required for ${source.name}`}
                    />
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
                  <td>
                    <input
                      className="field table-field source-policy-field"
                      value={draft.raw_content_policy}
                      onChange={(event) =>
                        setDraftValue(source.id, "raw_content_policy", event.target.value)
                      }
                      placeholder="Storage policy"
                    />
                    <div className="small-muted">{source.failure_handling}</div>
                  </td>
                  <td className={source.latest_status === "success" ? "health-ok" : ""}>
                    <div>{source.latest_status}</div>
                    {source.latest_error ? (
                      <div className="small-muted source-error">{source.latest_error}</div>
                    ) : null}
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
                    {source.recent_run_count > 0 ? (
                      <>
                        <div>{formatRatioPercent(source.recent_success_rate)} success</div>
                        <div className="small-muted">
                          {source.recent_items_stored}/{source.recent_items_fetched} stored
                        </div>
                        <div className="small-muted">
                          {formatRatioPercent(source.recent_store_rate)} store rate ·{" "}
                          {source.recent_run_count} runs
                        </div>
                      </>
                    ) : (
                      <span className="small-muted">No recent runs</span>
                    )}
                  </td>
                  <td>
                    <div>{source.last_finished_at ? formatDate(source.last_finished_at) : "never"}</div>
                    {source.latest_duration_seconds !== null ? (
                      <div className="small-muted">
                        duration {formatDuration(source.latest_duration_seconds)}
                      </div>
                    ) : null}
                    {source.last_success_at ? (
                      <div className="small-muted">success {formatDate(source.last_success_at)}</div>
                    ) : null}
                    {source.next_run_due_at ? (
                      <div className={source.is_stale ? "small-muted source-attention" : "small-muted"}>
                        due {formatDate(source.next_run_due_at)}
                      </div>
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
                      <button
                        className={`button icon-button ${
                          runSourceFilter?.id === source.id ? "active-icon-button" : ""
                        }`}
                        onClick={() => onRunSourceFilterChange(source)}
                        disabled={disabled || saving}
                        title="Show this source run history"
                        type="button"
                      >
                        {saving ? <Loader2 className="spin" size={16} /> : <History size={16} />}
                      </button>
                      <button
                        className={`button icon-button ${blocked ? "active-icon-button" : ""}`}
                        onClick={() => onToggleSourceBlock(source)}
                        disabled={disabled || saving}
                        title={
                          blocked
                            ? "Unblock source from personal views"
                            : "Block source from personal views"
                        }
                        type="button"
                      >
                        {saving ? <Loader2 className="spin" size={16} /> : <EyeOff size={16} />}
                      </button>
                      <button
                        className="button icon-button"
                        onClick={() => onDeleteSource(source)}
                        disabled={disabled || saving}
                        title="Remove source"
                        type="button"
                      >
                        {saving ? <Loader2 className="spin" size={16} /> : <Trash2 size={16} />}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {!displayedSources.length ? (
              <tr>
                <td colSpan={15}>
                  <div className="empty-state">No sources match this health filter.</div>
                </td>
              </tr>
            ) : null}
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
            <span className="badge">{formatDuration(lastCycleResult.duration_seconds)}</span>
            <span className="badge">{lastCycleResult.successful_source_count} succeeded</span>
            <span
              className={`badge ${
                lastCycleResult.failed_source_count > 0 ? "alert-badge" : "muted-badge"
              }`}
            >
              {lastCycleResult.failed_source_count} failed
            </span>
            <span
              className={`badge ${
                lastCycleResult.skipped_source_count > 0 ? "muted-badge" : ""
              }`}
            >
              {lastCycleResult.skipped_source_count} skipped
            </span>
            <span className="badge">{lastCycleResult.generated_alert_count} alerts</span>
            <span className="badge">{lastCycleResult.seeded_stock_count} stocks</span>
            <span className="badge">{lastCycleResult.seeded_company_count} companies</span>
            <span className="badge">{lastCycleResult.seeded_topic_count} topics</span>
            <span className="badge">{lastCycleResult.seeded_product_count} products</span>
            <span className="badge">
              Digest {formatDigestSnapshotStatus(lastCycleResult)}
            </span>
          </div>
          {lastCycleResult.digest_snapshot_message ? (
            <div className="small-muted">{lastCycleResult.digest_snapshot_message}</div>
          ) : null}
          <div className="cycle-source-list">
            {lastCycleResult.ingestion_results.map((result) => (
              <div
                className={`cycle-source-result ${
                  result.needs_attention
                    ? "needs-attention"
                    : result.status === "success"
                      ? "success"
                      : "muted"
                }`}
                key={result.source_name}
              >
                <div className="cycle-source-heading">
                  <span>{result.source_name}</span>
                  <span className="small-muted">
                    {result.status} · {result.items_fetched} fetched · {result.items_stored} stored ·{" "}
                    {Math.round(result.store_rate * 100)}% stored
                  </span>
                </div>
                {result.error_message ? (
                  <div className="small-muted source-error">{result.error_message}</div>
                ) : null}
                {result.recovery_hint ? (
                  <div className="small-muted">{result.recovery_hint}</div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
      <div className="source-run-toolbar" aria-label="Source run history filters">
        <button
          className={`button ${runStatusFilter === "all" ? "primary" : ""}`}
          onClick={() => onRunStatusFilterChange("all")}
          type="button"
        >
          All Runs
        </button>
        <button
          className={`button ${runStatusFilter === "failed" ? "primary" : ""}`}
          onClick={() => onRunStatusFilterChange("failed")}
          type="button"
        >
          Failed Runs
        </button>
        {runSourceFilter ? (
          <button
            className="button primary"
            onClick={() => onRunSourceFilterChange(null)}
            type="button"
          >
            {runSourceFilter.name}
          </button>
        ) : null}
      </div>
      <div className="source-run-list">
        {runs.length ? (
          runs.map((run) => (
            <div className="source-run-row" key={run.id}>
              <div>
                <div className="digest-link">{run.source_name}</div>
                <div className="small-muted">
                  {formatDate(run.started_at)} · fetched {run.items_fetched} · stored{" "}
                  {run.items_stored}
                  {run.duration_seconds !== null ? ` · ${formatDuration(run.duration_seconds)}` : ""}
                  {run.error_message ? ` · ${run.error_message}` : ""}
                </div>
              </div>
              <span className={`badge ${run.status === "success" ? "" : "muted-badge"}`}>
                {run.status}
              </span>
            </div>
          ))
        ) : (
          <div className="empty-state">
            {sourceRunHistoryEmptyText(runStatusFilter, runSourceFilter)}
          </div>
        )}
      </div>
    </section>
  );
}

function buildSourceDraft(source: SourceHealth): SourceDraft {
  return {
    name: source.name,
    type: source.type,
    access_method: source.access_method,
    base_url: source.base_url ?? "",
    auth_required: source.auth_required,
    priority: String(source.priority),
    polling_interval: source.polling_interval ?? "",
    rate_limit: source.rate_limit ?? "",
    terms_notes: source.terms_notes ?? "",
    raw_content_policy: source.raw_content_policy ?? "",
  };
}

function buildSourcePayload(draft: SourceDraft): SourceUpdatePayload {
  const priority = Number(draft.priority);

  return {
    name: draft.name.trim(),
    type: draft.type.trim() || "rss",
    access_method: draft.access_method.trim() || "rss",
    base_url: draft.base_url.trim() || null,
    auth_required: draft.auth_required,
    priority: Number.isFinite(priority) && priority >= 0 ? priority : 100,
    polling_interval: draft.polling_interval.trim() || null,
    rate_limit: draft.rate_limit.trim() || null,
    terms_notes: draft.terms_notes.trim() || null,
    raw_content_policy: draft.raw_content_policy.trim() || null,
  };
}

function isSourceDraftChanged(source: SourceHealth, draft: SourceDraft): boolean {
  return (
    source.name !== draft.name.trim() ||
    source.type !== draft.type.trim() ||
    source.access_method !== draft.access_method.trim() ||
    (source.base_url ?? "") !== draft.base_url.trim() ||
    source.auth_required !== draft.auth_required ||
    String(source.priority) !== draft.priority.trim() ||
    (source.polling_interval ?? "") !== draft.polling_interval.trim() ||
    (source.rate_limit ?? "") !== draft.rate_limit.trim() ||
    (source.terms_notes ?? "") !== draft.terms_notes.trim() ||
    source.raw_content_policy !== draft.raw_content_policy.trim()
  );
}

function buildSourceHealthCounts(
  sources: SourceHealth[],
  blockedSources: string[],
): Record<SourceHealthFilter, number> {
  return {
    all: sources.length,
    attention: sources.filter((source) => source.needs_attention).length,
    failed: sources.filter((source) => source.latest_status === "failed").length,
    stale: sources.filter((source) => source.is_stale).length,
    never_run: sources.filter((source) => source.latest_status === "never_run").length,
    disabled: sources.filter((source) => !source.enabled).length,
    blocked: sources.filter((source) => sourceNameInList(source.name, blockedSources)).length,
  };
}

function sourceMatchesHealthFilter(
  source: SourceHealth,
  filter: SourceHealthFilter,
  blockedSources: string[],
): boolean {
  if (filter === "attention") return source.needs_attention;
  if (filter === "failed") return source.latest_status === "failed";
  if (filter === "stale") return source.is_stale;
  if (filter === "never_run") return source.latest_status === "never_run";
  if (filter === "disabled") return !source.enabled;
  if (filter === "blocked") return sourceNameInList(source.name, blockedSources);
  return true;
}

function sourceRunHistoryEmptyText(
  statusFilter: "all" | "failed",
  sourceFilter: SourceHealth | null,
): string {
  if (sourceFilter && statusFilter === "failed") {
    return `No failed source runs recorded for ${sourceFilter.name}.`;
  }
  if (sourceFilter) {
    return `No source runs recorded for ${sourceFilter.name}.`;
  }
  return statusFilter === "failed"
    ? "No failed source runs recorded yet."
    : "No source runs recorded yet.";
}

function sourceNameInList(sourceName: string, sourceNames: string[]): boolean {
  return sourceNames.some((name) => name.toLowerCase() === sourceName.toLowerCase());
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
  eventClusters: EventCluster[],
  sources: SourceHealth[],
  preferences: UserPreferences | null,
  moduleFeedOverrides: Partial<Record<FeedModuleKey, FeedItem[]>>,
  alerts: AlertItem[],
  stocks: StockWatchlistItem[],
  companies: CompanyWatchlistItem[],
  topics: TopicWatchlistItem[],
  products: ProductWatchlistItem[],
): Record<ModuleKey, number> {
  const settingsCount =
    Object.values(preferences?.ranking_weights ?? DEFAULT_RANKING_WEIGHTS).filter(
      (value) => value > 0,
    ).length +
    (preferences?.preferred_sources.length ?? 0) +
    (preferences?.blocked_sources.length ?? 0) +
    (preferences?.language_preferences.length ?? 0);
  return {
    dashboard: feed.length,
    trends: topics.length || moduleCount(feed, "trends", moduleFeedOverrides),
    research: moduleCount(feed, "research", moduleFeedOverrides),
    products: products.length || moduleCount(feed, "products", moduleFeedOverrides),
    stocks: stocks.length + companies.length || moduleCount(feed, "stocks", moduleFeedOverrides),
    chinese: moduleCount(feed, "chinese", moduleFeedOverrides),
    saved: savedItems.length,
    clusters: eventClusters.length,
    submit: feed.filter((item) => item.category === "manual_submission").length,
    alerts: alerts.filter((alert) => alert.status === "active").length,
    digest: collectDigestFeedItems(digest).length,
    sources: sources.filter((source) => source.needs_attention).length,
    settings: settingsCount,
  };
}

function moduleCount(
  feed: FeedItem[],
  moduleKey: FeedModuleKey,
  moduleFeedOverrides: Partial<Record<FeedModuleKey, FeedItem[]>>,
): number {
  return (
    moduleFeedOverrides[moduleKey]?.length ??
    feed.filter((item) => itemMatchesModule(item, moduleKey)).length
  );
}

function filterFeedByModule(
  feed: FeedItem[],
  moduleKey: ModuleKey,
  digest: DailyDigest | null,
  savedItems: FeedItem[],
  moduleFeedOverrides: Partial<Record<FeedModuleKey, FeedItem[]>>,
): FeedItem[] {
  if (moduleKey === "dashboard") {
    return feed;
  }
  if (isFeedModuleKey(moduleKey) && moduleFeedOverrides[moduleKey]) {
    return moduleFeedOverrides[moduleKey] ?? [];
  }
  if (moduleKey === "saved") {
    return savedItems;
  }
  if (moduleKey === "digest") {
    return collectDigestFeedItems(digest);
  }
  if (moduleKey === "sources" || moduleKey === "settings") {
    return [];
  }
  return feed.filter((item) => itemMatchesModule(item, moduleKey));
}

function isFeedModuleKey(moduleKey: ModuleKey): moduleKey is FeedModuleKey {
  return feedModuleKeys.has(moduleKey);
}

function formatModuleLabel(moduleKey: FeedModuleKey): string {
  return moduleNavItems.find((item) => item.key === moduleKey)?.label ?? moduleKey;
}

function searchStatusText(
  resultCount: number,
  moduleKey: FeedModuleKey | null,
  startedAt?: number,
): string {
  const moduleText = moduleKey ? ` in ${formatModuleLabel(moduleKey)}` : "";
  const elapsedText =
    typeof startedAt === "number"
      ? ` in ${formatElapsedMs(performance.now() - startedAt)}`
      : "";
  return `Search returned ${resultCount} items${moduleText}${elapsedText}`;
}

function formatLlmCandidatePreview(
  previews: FeedProcessingResponse["candidate_previews"],
): string {
  const planned = previews.filter((preview) => preview.planned_operations.length > 0).slice(0, 3);
  if (!planned.length) {
    return "";
  }
  const titles = planned.map((preview) => `${preview.title} (${preview.source_name})`);
  const remaining = previews.filter((preview) => preview.planned_operations.length > 0).length - titles.length;
  return ` · planned: ${titles.join("; ")}${remaining > 0 ? `; +${remaining} more` : ""}`;
}

function formatElapsedMs(elapsedMs: number): string {
  if (!Number.isFinite(elapsedMs) || elapsedMs < 0) {
    return "0s";
  }
  if (elapsedMs < 1000) {
    return `${Math.max(1, Math.round(elapsedMs))}ms`;
  }
  return `${(elapsedMs / 1000).toFixed(1)}s`;
}

function itemMatchesModule(item: FeedItem, moduleKey: ModuleKey): boolean {
  if (moduleKey === "trends") {
    return [
      "technical_trend",
      "policy_regulation",
      "infrastructure",
      "open_source_release",
      "tutorial_opinion",
    ].includes(item.category);
  }
  if (moduleKey === "research") {
    return ["research", "benchmark_evaluation"].includes(item.category);
  }
  if (moduleKey === "products") {
    return item.category === "product" || item.products.length > 0;
  }
  if (moduleKey === "stocks") {
    return (
      ["stock_company_event", "funding_mna"].includes(item.category) || item.tickers.length > 0
    );
  }
  if (moduleKey === "chinese") {
    return item.category === "social_trend" || item.language === "zh";
  }
  return false;
}

function collectDigestFeedItems(digest: DailyDigest | null): FeedItem[] {
  const byId = new Map<number, FeedItem>();
  (digest?.sections ?? []).forEach((section) => {
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

function buildDigestDateQuery(value: string): string {
  const normalized = value.trim();
  return normalized ? `?date=${encodeURIComponent(normalized)}` : "";
}

function buildDigestEmailHref(subject: string, markdown: string): string {
  const params = new URLSearchParams({
    subject,
    body: markdown,
  });
  return `mailto:?${params.toString()}`;
}

function downloadMarkdownFile(filename: string, markdown: string): void {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function downloadJsonFile(filename: string, data: Record<string, unknown>): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function safeFilenamePart(value: string): string {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "latest"
  );
}

function buildSourceRunQuery(statusFilter: "all" | "failed", sourceId?: number): string {
  const params = new URLSearchParams({ limit: "8" });
  if (statusFilter === "failed") {
    params.set("status", "failed");
  }
  if (sourceId) {
    params.set("source_id", String(sourceId));
  }
  return `?${params.toString()}`;
}

function isAlertRuleSnoozed(rule: AlertRule): boolean {
  return rule.snoozed_until ? new Date(rule.snoozed_until).getTime() > Date.now() : false;
}

function formatCategoryLabel(value: string): string {
  const optionLabel = categoryOptions.find((option) => option.value === value)?.label;
  if (optionLabel) {
    return optionLabel;
  }
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function formatProductUseCaseLabel(value: string): string {
  return (
    productUseCaseOptions.find((option) => option.value === value)?.label ??
    formatCategoryLabel(value)
  );
}

function formatMarketImpactLabel(value: string): string {
  const labels: Record<string, string> = {
    earnings_guidance: "Earnings/guidance",
    analyst_action: "Analyst action",
    partnership_customer: "Partnership/customer",
    supply_chain_regulation: "Supply chain/regulation",
    funding_mna: "Funding/M&A",
    demand_signal: "Demand signal",
    positive_signal: "Positive market signal",
    negative_signal: "Negative market signal",
    stock_signal: "Stock signal",
  };
  return labels[value] ?? formatCategoryLabel(value);
}

function formatSummarySource(value: string): string {
  const labels: Record<string, string> = {
    stored_summary: "stored summary",
    why_it_matters: "why it matters",
    deterministic: "deterministic fallback",
  };
  return labels[value] ?? value.replace(/_/g, " ");
}

function formatConfirmationLevel(value: string): string {
  if (value === "strong_cross_source") {
    return "Strong cross-source";
  }
  if (value === "cross_source") {
    return "Cross-source";
  }
  if (value === "repeated_single_source") {
    return "Repeated single-source";
  }
  return "Single-source";
}

function splitTerms(value: string) {
  return value
    .split(",")
    .map((term) => term.trim())
    .filter(Boolean);
}

function buildManualEngagementPayload(draft: ManualEngagementDraft): Record<string, number> | null {
  const entries = manualEngagementFields
    .map((field) => {
      const parsed = parseOptionalWholeNumber(draft[field.key]);
      return parsed === null ? null : [field.key, parsed];
    })
    .filter((entry): entry is [keyof ManualEngagementDraft, number] => entry !== null);

  return entries.length ? Object.fromEntries(entries) : null;
}

function parseOptionalWholeNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return Math.max(0, Math.trunc(parsed));
}

function buildSearchIntentChips(intent: SearchIntent | null): string[] {
  if (!intent) {
    return [];
  }

  const chips = [
    intent.query ? `query: ${intent.query}` : null,
    intent.source ? `source: ${intent.source}` : null,
    intent.category ? `category: ${intent.category}` : null,
    intent.subcategory ? `use case: ${formatProductUseCaseLabel(intent.subcategory)}` : null,
    intent.ticker ? `ticker: ${intent.ticker}` : null,
    intent.company ? `company: ${intent.company}` : null,
    intent.topic ? `topic: ${intent.topic}` : null,
    intent.manual_tag ? `tag: ${intent.manual_tag}` : null,
    intent.language ? `language: ${intent.language}` : null,
    intent.date_from ? `from: ${intent.date_from}` : null,
    intent.date_to ? `to: ${intent.date_to}` : null,
    intent.min_importance_score !== null ? `importance: ${intent.min_importance_score}` : null,
    intent.min_social_signal_score !== null
      ? `social signal: ${intent.min_social_signal_score}`
      : null,
    intent.ai_related === null
      ? null
      : intent.ai_related
        ? "AI-related"
        : "needs AI relevance review",
    intent.saved_only ? "saved" : null,
    intent.read_status ? `read: ${intent.read_status}` : null,
  ];

  return chips.filter(Boolean) as string[];
}

function stockToDetailDraft(stock: StockWatchlistItem | null): StockDetailDraft {
  return {
    company_name: stock?.company_name ?? "",
    exchange: stock?.exchange ?? "",
    sector: stock?.sector ?? "",
    industry: stock?.industry ?? "",
    market_cap_usd:
      stock?.market_cap_usd === null || stock?.market_cap_usd === undefined
        ? ""
        : String(stock.market_cap_usd),
    group_name: stock?.group_name ?? "",
    related_keywords: stock?.related_keywords.join(", ") ?? "",
    related_companies: stock?.related_companies.join(", ") ?? "",
    related_ai_themes: stock?.related_ai_themes.join(", ") ?? "",
    is_holding: stock?.is_holding ?? false,
    shares: stock?.shares === null || stock?.shares === undefined ? "" : String(stock.shares),
    average_cost:
      stock?.average_cost === null || stock?.average_cost === undefined
        ? ""
        : String(stock.average_cost),
    notes: stock?.notes ?? "",
  };
}

function companyToDetailDraft(company: CompanyWatchlistItem | null): CompanyDetailDraft {
  return {
    company_name: company?.company_name ?? "",
    ticker: company?.ticker ?? "",
    category: company?.category ?? "ai_company",
    related_terms: company?.related_terms.join(", ") ?? "",
    notes: company?.notes ?? "",
  };
}

function topicToDetailDraft(topic: TopicWatchlistItem | null): TopicDetailDraft {
  return {
    label: topic?.label ?? "",
    category: topic?.category ?? "technical_trend",
    related_terms: topic?.related_terms.join(", ") ?? "",
    notes: topic?.notes ?? "",
  };
}

function productToDetailDraft(product: ProductWatchlistItem | null): ProductDetailDraft {
  return {
    label: product?.label ?? "",
    related_terms: product?.related_terms.join(", ") ?? "",
    notes: product?.notes ?? "",
  };
}

function alertRuleToDraft(rule: AlertRule | null): AlertRuleDraft {
  return {
    name: rule?.name ?? "",
    description: rule?.description ?? "",
    category: rule?.category ?? "all",
    severity: rule?.severity ?? "medium",
    min_importance_score:
      rule?.min_importance_score === undefined ? "0.75" : String(rule.min_importance_score),
    min_stock_impact_score:
      rule?.min_stock_impact_score === undefined ? "0" : String(rule.min_stock_impact_score),
    tickers: rule?.tickers.join(", ") ?? "",
    topics: rule?.topics.join(", ") ?? "",
  };
}

function parseBoundedScore(value: string, fallback: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(0, Math.min(1, parsed));
}

function hasPortfolioDetails(stock: StockWatchlistItem | null): boolean {
  if (!stock) {
    return false;
  }
  return Boolean(stock?.is_holding || stock?.shares !== null || stock?.average_cost !== null);
}

function orderStocksForTable(
  stocks: StockWatchlistItem[],
  signalSummaries: StockSignalSummary[],
  sortMode: StockSortMode,
): StockWatchlistItem[] {
  if (sortMode === "watchlist") {
    return stocks;
  }

  const summaryMap = new Map(
    signalSummaries.map((summary, index) => [summary.stock.ticker, { summary, index }]),
  );

  return [...stocks].sort((left, right) => {
    if (left.is_pinned !== right.is_pinned) {
      return left.is_pinned ? -1 : 1;
    }

    const leftSignal = summaryMap.get(left.ticker);
    const rightSignal = summaryMap.get(right.ticker);
    const leftAttention = leftSignal?.summary.attention_score ?? -1;
    const rightAttention = rightSignal?.summary.attention_score ?? -1;

    if (rightAttention !== leftAttention) {
      return rightAttention - leftAttention;
    }

    const leftSignalIndex = leftSignal?.index ?? Number.MAX_SAFE_INTEGER;
    const rightSignalIndex = rightSignal?.index ?? Number.MAX_SAFE_INTEGER;
    if (leftSignalIndex !== rightSignalIndex) {
      return leftSignalIndex - rightSignalIndex;
    }

    if (left.display_order !== right.display_order) {
      return left.display_order - right.display_order;
    }

    return left.ticker.localeCompare(right.ticker);
  });
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

function formatMarketCap(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value) || value <= 0) {
    return "--";
  }
  return `$${formatCompactNumber(value)}`;
}

function formatProductDiscoveryNote(score: ProductDiscoveryScore | undefined): string {
  if (!score) {
    return "";
  }
  return ` · discovery ${Math.round(score.score * 100)} · novelty ${Math.round(
    score.novelty_score * 100,
  )} · traction ${Math.round(score.traction_score * 100)}`;
}

function formatChange(market: StockMarketSnapshot | null | undefined): string {
  if (!market || market.change === null || market.change_percent === null) {
    return "--";
  }
  const sign = market.change > 0 ? "+" : "";
  return `${sign}${market.change.toFixed(2)} (${sign}${market.change_percent.toFixed(2)}%)`;
}

function formatRatioPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "--";
  }
  return `${Math.round(value * 100)}%`;
}

function formatPercentChange(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "--";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
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
