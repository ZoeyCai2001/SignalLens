# Product Requirements Document
# Personal AI Intelligence Dashboard

**Version:** 0.1  
**Status:** Draft  
**Primary User:** Personal use, with possible extension to a small group of friends  
**Language:** English  
**Core Modules:** AI Trends / AI Research / AI Products / AI Stock Watchlist / Chinese Social Trends / Daily Digest

---

## 1. Product Overview

### 1.1 Project Name

**AI Intelligence Dashboard**

### 1.2 Product Goal

The goal of this project is to build a personal web-based intelligence dashboard that collects, filters, summarizes, and ranks AI-related information from multiple online sources.

The system should help the user quickly understand:

1. **AI news and technical trends**  
   Examples: agent harness, skills, AI coding agents, model routing, open-source LLMs, AI infrastructure, multi-agent systems, new research papers, benchmark shifts.

2. **AI-related stock and company events**  
   Examples: news about companies held or watched by the user, such as MU, SNDK, MRVL, NVIDIA, AMD, Broadcom, TSMC, cloud companies, AI software companies, and major AI infrastructure vendors.

3. **AI products and applications**  
   Examples: new AI web apps, coding tools, AI productivity products, consumer AI apps, AI-native workflows, and AI products becoming popular on social platforms.

The product is mainly for **personal use**, with possible extension to a small group of friends. It is not intended as a commercial media platform at the first stage.

---

## 2. Target Users

### 2.1 Primary User

The primary user is an AI-interested individual who wants to monitor AI trends across research, technology, finance, and product development.

The user has several characteristics:

- Interested in AI research and technical topics.
- Interested in AI-related company news that may affect stock prices.
- Holds or watches specific stocks, currently including **MU**, **SNDK**, and **MRVL**.
- Wants both English and Chinese information sources.
- Wants to avoid manually checking many platforms every day.
- Can provide LLM API keys if needed.
- Uses a MacBook with M3 chip.

### 2.2 Secondary Users

A small number of friends may later use the product. They may have different watched stocks, topic interests, or preferred sources.

At the first stage, the product should support one user well. Multi-user support should be designed but not overbuilt.

---

## 3. Core Product Value

The product should not simply be an RSS reader. Its value comes from:

1. **Source aggregation**  
   Collect AI-related information from news websites, social media, finance APIs, research platforms, developer communities, and product launch platforms.

2. **AI relevance filtering**  
   Remove irrelevant noise and keep only content related to AI, AI companies, AI products, AI infrastructure, or AI-driven market events.

3. **Personalized ranking**  
   Rank items based on the user's interests, watched stocks, preferred technical topics, and source credibility.

4. **LLM-based summarization**  
   Convert long articles, tweets, papers, posts, and discussions into concise summaries.

5. **Signal detection**  
   Detect whether an item is merely interesting, technically important, product-relevant, or potentially market-moving.

6. **Cross-source clustering**  
   Merge multiple items about the same event into one event card.

7. **Daily digest and alerting**  
   Produce a daily AI briefing and optional urgent alerts for stock-sensitive news.

---

## 4. Product Structure

The product should be organized around six first-class modules:

1. **AI Trends**
2. **AI Research**
3. **AI Products**
4. **AI Stock Watchlist**
5. **Chinese Social Trends**
6. **Daily Digest**

The **AI Stock Watchlist** should be a first-class module, not only a feed filter. It should work similarly to the “自选列表” function in stock apps, allowing the user to select and monitor interested stocks.

---

## 5. Scope

### 5.1 In Scope for MVP

The MVP should include:

- A web dashboard.
- A backend ingestion pipeline.
- Source connectors for several reliable sources.
- User-defined watchlists:
  - Topics.
  - Companies.
  - Stock tickers.
  - Product categories.
- AI Stock Watchlist.
- LLM-based classification and summarization.
- A searchable database of collected items.
- Daily digest generation.
- Basic event ranking.
- Basic stock-news linkage.
- Manual URL submission.

### 5.2 Out of Scope for MVP

The MVP should not include:

- Public user registration.
- Payment system.
- Mobile app.
- Fully automated trading signals.
- Investment advice generation.
- Large-scale web crawling.
- Training custom LLMs.
- Real-time high-frequency trading data.
- Circumventing platform anti-scraping restrictions.
- Scraping private or login-protected content without permission.

---

## 6. Information Categories

The system should classify every collected item into one or more of the following categories.

### 6.1 AI Technical Trends

This category covers new or trending technical concepts.

Examples:

- Agent harness.
- Skill retrieval.
- Tool-use agents.
- AI coding agents.
- Model Context Protocol.
- Agent memory.
- Multi-agent collaboration.
- RAG systems.
- Long-context models.
- Model routing.
- AI evaluation.
- AI infrastructure.
- Open-source LLMs.
- Inference optimization.
- AI safety and governance.
- Multimodal models.

### 6.2 AI Research

This category covers papers, preprints, benchmarks, technical blogs, and research discussions.

Sources may include:

- arXiv.
- Hugging Face.
- GitHub repositories.
- Hacker News.
- AI company blogs.
- Research lab blogs.
- Researcher Twitter/X accounts.

### 6.3 AI Stock and Company Events

This category covers company-level events that may affect stocks.

Examples:

- Earnings.
- Guidance.
- AI demand commentary.
- Data center revenue.
- GPU/ASIC/DRAM/NAND demand.
- New chip releases.
- Cloud capex updates.
- Major AI partnerships.
- Product launches.
- Supply chain news.
- Export control news.
- Analyst upgrades or downgrades.
- M&A rumors.
- Regulatory events.

Initial watched tickers:

- MU.
- SNDK.
- MRVL.

The system should also support tracking related companies:

- NVDA.
- AMD.
- AVGO.
- TSM.
- ASML.
- AMAT.
- LRCX.
- MSFT.
- GOOGL.
- AMZN.
- META.
- ORCL.
- ARM.
- SMCI.
- DELL.
- HPE.

This list should be editable.

### 6.4 AI Products

This category covers AI applications and user-facing products.

Examples:

- AI coding products.
- AI browser products.
- AI note-taking products.
- AI search products.
- AI photo/video tools.
- AI productivity apps.
- AI workflow tools.
- AI agents for business operations.
- AI consumer apps.
- AI products popular on Xiaohongshu, Product Hunt, Hacker News, Reddit, or X.

### 6.5 AI Social Trends

This category covers early signals from social platforms.

Examples:

- A product suddenly becoming popular.
- A technical term becoming trendy.
- A company being discussed heavily.
- A controversial model release.
- User complaints about an AI product.
- Influencer-driven adoption.
- Chinese social platform sentiment around AI products.

---

## 7. Source Strategy

Source quality is the most important part of this project. The product should use a layered source strategy.

### 7.1 Source Layers

#### Layer 1: Official and Structured APIs

These sources should be preferred because they are stable and easier to maintain.

Examples:

- arXiv API.
- Hacker News API.
- GitHub REST API.
- Hugging Face Hub API.
- Product Hunt API.
- NewsAPI or similar news APIs.
- Alpha Vantage.
- Finnhub.
- SEC filings APIs or EDGAR data access.
- Official company blogs and RSS feeds.

#### Layer 2: Public Web and RSS Sources

These are useful but may require HTML parsing or RSS handling.

Examples:

- OpenAI blog.
- Anthropic news.
- Google DeepMind blog.
- Meta AI blog.
- Microsoft AI blog.
- NVIDIA blog.
- AMD blog.
- Hugging Face blog.
- Stability AI blog.
- Perplexity blog.
- Cursor blog.
- Vercel AI blog.
- LangChain blog.
- LlamaIndex blog.
- Modal blog.
- Together AI blog.
- SemiAnalysis.
- The Decoder.
- TechCrunch AI.
- The Verge AI.
- VentureBeat AI.
- MIT Technology Review AI.
- Bloomberg AI-related news, if accessible.
- CNBC technology and chip news, if accessible.

#### Layer 3: Social and Community Sources

These sources are valuable for early signals but noisier.

Examples:

- X/Twitter.
- Reddit.
- Hacker News comments.
- GitHub issues and stars.
- Product Hunt launches and comments.
- Xiaohongshu.
- WeChat public accounts, if manually configured or available through lawful channels.
- Selected blogs and newsletters.

#### Layer 4: Manual Sources

The system should allow manual URL submission.

The user should be able to paste:

- A tweet/X post.
- A Xiaohongshu post link.
- A news article.
- A company press release.
- A research paper.
- A blog post.
- A product page.

The system should then summarize, classify, and store it.

---

## 8. Recommended Initial Sources

### 8.1 AI Technical and Research Sources

The first version should include:

1. **arXiv**
   - Query categories:
     - cs.AI
     - cs.LG
     - cs.CL
     - cs.CV
     - cs.RO
   - Keyword filters:
     - agent
     - harness
     - tool use
     - retrieval
     - coding agent
     - reasoning
     - multimodal
     - inference
     - benchmark
     - alignment
     - memory
     - MCP

2. **Hacker News**
   - Track AI-related front-page posts.
   - Track comments for high-signal technical discussion.
   - Useful for early developer interest.

3. **GitHub**
   - Track repositories by keywords:
     - agent
     - llm
     - rag
     - mcp
     - coding-agent
     - ai-agent
     - inference
     - workflow
     - evaluation
   - Track sudden star growth where possible.
   - Track selected repositories manually.

4. **Hugging Face**
   - Track trending models, datasets, and Spaces.
   - Track major model releases.
   - Track new AI demos.

5. **AI company blogs**
   - OpenAI.
   - Anthropic.
   - Google DeepMind.
   - Meta AI.
   - Microsoft AI.
   - NVIDIA.
   - Hugging Face.
   - LangChain.
   - LlamaIndex.

### 8.2 AI Finance and Stock Sources

The first version should include:

1. **Finnhub**
   - Company news by ticker.
   - Basic quote data.
   - Company profile.
   - Earnings calendar if available under selected plan.

2. **Alpha Vantage**
   - Market news and sentiment.
   - Ticker-specific news.
   - Technical indicators if needed.

3. **Yahoo Finance**
   - Use as a user-facing reference website.
   - Avoid depending on unofficial scraping as the primary backend source.
   - If using yfinance for personal prototyping, treat it as unstable and replaceable.

4. **SEC filings**
   - 10-K.
   - 10-Q.
   - 8-K.
   - Insider filings if needed.
   - Earnings-related filings.

5. **Company investor relations pages**
   - MU investor relations.
   - SNDK investor relations.
   - MRVL investor relations.
   - Related semiconductor and AI infrastructure companies.

6. **Market news websites**
   - CNBC.
   - Bloomberg, if available.
   - Reuters, if available.
   - MarketWatch.
   - Seeking Alpha, if available.
   - The Information, if available.
   - SemiAnalysis.

### 8.3 AI Product Sources

The first version should include:

1. **Product Hunt**
   - New AI launches.
   - Upvotes.
   - Comments.
   - Product tags.

2. **Hacker News**
   - “Show HN” AI products.
   - AI tool launches.

3. **GitHub**
   - New open-source AI products.
   - Fast-growing repositories.

4. **Hugging Face Spaces**
   - New and trending AI demos.

5. **X/Twitter**
   - Founder and builder announcements.
   - AI product virality.
   - Influencer adoption.

6. **Xiaohongshu**
   - Chinese consumer AI product trends.
   - AI photo, AI video, AI study, AI productivity, AI coding, and AI workflow keywords.
   - Should be treated as an optional connector due to access and compliance uncertainty.

---

## 9. Source Access Requirements

### 9.1 General Requirements

Each source connector should support:

- Source name.
- Source type.
- Access method.
- Authentication method.
- Rate limit.
- Polling interval.
- Raw content storage policy.
- Terms-of-service notes.
- Failure handling.
- Last successful fetch timestamp.

### 9.2 X/Twitter

The system should support X/Twitter as a high-value but cost-sensitive source.

Required capabilities:

- Search posts by keyword.
- Track selected accounts.
- Track posts mentioning watched companies or topics.
- Track engagement metrics if available:
  - likes
  - reposts
  - replies
  - views, if available
- Store post URL and metadata.
- Avoid storing excessive full-text data if terms restrict it.

Suggested monitored accounts:

- AI researchers.
- AI company founders.
- AI infrastructure founders.
- Semiconductor analysts.
- Financial analysts.
- AI product builders.
- Open-source AI maintainers.

Initial implementation recommendation:

- Start with official X API if budget allows.
- If official access is too expensive, support manual URL submission first.
- Do not build the product around fragile unofficial scraping.

### 9.3 Xiaohongshu

Xiaohongshu is important for Chinese consumer AI product signals but should be handled carefully.

Required capabilities:

- Track keyword search results if lawful access is available.
- Track public notes about AI products.
- Extract:
  - title
  - author
  - post URL
  - publish time
  - likes/collects/comments if available
  - text
  - images only if allowed
- Support Chinese keyword lists:
  - AI工具
  - AI写作
  - AI编程
  - AI修图
  - AI视频
  - AI搜索
  - AI笔记
  - AI学习
  - 智能体
  - AI办公
  - AI副业
  - Cursor
  - ChatGPT
  - Claude
  - Gemini
  - 豆包
  - Kimi
  - 通义
  - DeepSeek

Implementation recommendation:

- Treat Xiaohongshu as a Phase 2 connector.
- Prefer official/open platform access if available for the intended use case.
- If using a third-party public-data provider, document the provider, scope, cost, and compliance risk.
- Do not bypass login, anti-bot, captcha, device fingerprinting, or access controls.

### 9.4 News Websites

The system should support two methods:

1. **News API provider**
   - NewsAPI, GDELT, Event Registry, or similar.
   - Best for broad search and normalized metadata.

2. **RSS / official feeds**
   - Best for blogs, company updates, and smaller sources.

The system should store:

- title
- source
- author
- URL
- publication time
- summary
- full text if allowed
- extracted entities
- related tickers
- related topics

### 9.5 Finance Data

The system should avoid acting as a trading system. The goal is news intelligence, not trading execution.

Finance data requirements:

- Current and historical price for watched tickers.
- Daily percentage move.
- Intraday movement if available.
- Volume change.
- Market cap.
- Sector.
- Related company mapping.
- News-to-price timeline.

For each finance-related news item, the system should compute:

- Related ticker.
- Event type.
- Possible direction:
  - positive
  - negative
  - mixed
  - uncertain
- Confidence.
- Whether the item may be market-moving.
- Whether the price already reacted.

The product must clearly state:

> This product is for information organization only. It does not provide financial advice.

---

## 10. AI Stock Watchlist

### 10.1 Feature Name

**AI Stock Watchlist**

### 10.2 Feature Goal

The system should allow the user to create and manage a personalized stock watchlist, similar to the “自选列表” function in stock trading or finance apps. The watchlist is used to monitor AI-related news, company events, market movements, and potential stock-impact signals for selected companies.

This feature is not intended to provide trading advice. Its goal is to help the user organize AI-related company information and detect potentially important events.

### 10.3 Core User Story

As a user, I want to select stocks that I am interested in, so that the system can continuously monitor AI-related news, company events, stock movements, and market signals for those companies.

### 10.4 Initial Watchlist

The initial stock watchlist should include:

- MU — Micron Technology
- SNDK — SanDisk
- MRVL — Marvell Technology

The user should be able to add, remove, reorder, group, and prioritize stocks.

### 10.5 Watchlist Management Requirements

The system should support the following actions:

1. **Add stock**
   - Add by ticker symbol.
   - Add by company name.
   - Automatically resolve company name, exchange, sector, and industry.

2. **Remove stock**
   - Remove a stock from the watchlist without deleting historical collected news.

3. **Edit stock metadata**
   - Custom display name.
   - Priority level.
   - Notes.
   - Related keywords.
   - Related AI themes.

4. **Group stocks**
   Example groups:
   - My Holdings
   - AI Chips
   - Memory / Storage
   - AI Infrastructure
   - Cloud
   - AI Software
   - Watch Only

5. **Set priority**
   Each stock should have a priority level:
   - High
   - Medium
   - Low

6. **Pin important stocks**
   Pinned stocks should appear at the top of the stock dashboard.

### 10.6 Stock Watchlist Data Fields

Each stock in the watchlist should include:

```json
{
  "ticker": "MRVL",
  "company_name": "Marvell Technology",
  "exchange": "NASDAQ",
  "sector": "Technology",
  "industry": "Semiconductors",
  "priority": "High",
  "group": "AI Chips",
  "is_holding": true,
  "average_cost": null,
  "shares": null,
  "related_keywords": [
    "AI data center",
    "custom silicon",
    "optical interconnect",
    "ASIC",
    "cloud AI infrastructure"
  ],
  "related_companies": [
    "NVDA",
    "AMD",
    "AVGO",
    "TSM"
  ],
  "notes": "Monitor AI custom silicon and data center growth."
}
```

For privacy, fields such as `average_cost` and `shares` should be optional. The MVP can support watchlist tracking without storing position size or cost basis.

### 10.7 AI-Relevance Mapping

For each watched stock, the system should maintain an AI relevance profile.

#### MU — Micron Technology

Relevant AI themes:

- HBM memory
- DRAM demand
- NAND demand
- AI server memory
- Data center capex
- GPU memory supply chain
- Cloud infrastructure demand

Relevant keywords:

- HBM
- DRAM
- NAND
- data center
- AI server
- memory pricing
- Nvidia supply chain
- cloud capex

#### MRVL — Marvell Technology

Relevant AI themes:

- Custom silicon
- AI data center networking
- Optical interconnect
- ASIC
- DSP
- Cloud infrastructure
- High-speed connectivity

Relevant keywords:

- custom silicon
- ASIC
- AI data center
- optical
- interconnect
- cloud AI
- networking chip

#### SNDK — SanDisk

Relevant AI themes:

- NAND storage
- Enterprise SSD
- AI data storage
- Data center storage
- Memory cycle

Relevant keywords:

- NAND
- SSD
- storage
- enterprise storage
- data center
- AI storage demand

### 10.8 Stock Dashboard Requirements

The stock watchlist page should show a table of selected stocks.

Required columns:

- Ticker
- Company name
- Current price
- Daily change
- AI news count today
- High-impact news count
- Latest AI-related event
- Sentiment
- Priority
- Last updated

Example:

| Ticker | Company | Change | AI News | High-Impact | Latest Event | Sentiment |
|---|---|---:|---:|---:|---|---|
| MU | Micron | +2.1% | 5 | 1 | HBM demand discussed in analyst note | Positive |
| MRVL | Marvell | -1.3% | 7 | 2 | AI custom silicon revenue mentioned | Mixed |
| SNDK | SanDisk | +0.4% | 2 | 0 | NAND pricing update | Neutral |

### 10.9 Stock Detail Page

Each stock should have its own detail page.

The page should include:

1. **Company overview**
   - Company name
   - Ticker
   - Exchange
   - Sector
   - Industry
   - AI relevance description

2. **Price chart**
   - Intraday
   - 5 days
   - 1 month
   - 6 months
   - 1 year

3. **AI-related news timeline**
   - News items linked to price movement
   - Event clusters
   - Source links

4. **AI theme breakdown**
   Example:
   - HBM
   - AI data center
   - Cloud capex
   - Custom silicon
   - Storage demand

5. **Market-impact events**
   - Earnings
   - Guidance
   - Analyst rating
   - Product launch
   - Partnership
   - Supply chain news
   - Regulation

6. **LLM-generated summary**
   - What happened
   - Why it matters
   - Possible market relevance
   - Uncertainties

7. **User notes**
   - Personal notes
   - Saved articles
   - Manual tags

### 10.10 Stock-Related Alert Rules

The watchlist should support alert rules.

Example alert rule:

```json
{
  "ticker": "MRVL",
  "alert_type": "high_impact_ai_news",
  "condition": "importance_score >= 0.8",
  "notification": "dashboard"
}
```

Supported alert types:

1. **High-impact AI news**
   - Trigger when an important AI-related item is detected for a watched stock.

2. **Large price movement with AI news**
   - Trigger when price moves significantly and there is related AI news.

3. **Earnings or guidance mention**
   - Trigger when earnings, revenue guidance, AI demand, or data center demand is mentioned.

4. **Analyst action**
   - Trigger when an analyst upgrade, downgrade, price target change, or rating note is detected.

5. **Supply chain signal**
   - Trigger when supplier, customer, or competitor news may affect the watched stock.

6. **Theme breakout**
   - Trigger when a theme such as HBM, AI data center, custom silicon, or NAND pricing becomes highly active.

### 10.11 AI Stock Event Classification

For every stock-related item, the system should classify:

```json
{
  "ticker": "MU",
  "company": "Micron Technology",
  "is_ai_related": true,
  "event_type": "demand_signal",
  "ai_theme": ["HBM", "AI server memory", "data center"],
  "possible_market_impact": "positive",
  "confidence": 0.74,
  "time_sensitivity": "medium",
  "summary": "The article discusses strong AI server memory demand, which may be relevant to Micron's HBM and DRAM business.",
  "uncertainties": [
    "The article does not provide company-specific revenue guidance.",
    "The market may have already priced in part of the demand outlook."
  ]
}
```

Possible event types:

- earnings
- guidance
- analyst_rating
- product_launch
- partnership
- customer_win
- supply_chain
- demand_signal
- pricing_cycle
- regulation
- export_control
- macro_event
- competitor_event
- rumor
- social_sentiment
- technical_analysis
- irrelevant

### 10.12 Watchlist Ranking Logic

Inside the stock watchlist, stocks should be ranked by a combined score:

```text
stock_attention_score =
  0.30 * high_impact_news_score
+ 0.20 * price_movement_score
+ 0.20 * AI_relevance_score
+ 0.15 * social_discussion_score
+ 0.10 * source_quality_score
+ 0.05 * user_priority_score
```

This score determines which watched stocks should appear first each day.

### 10.13 Privacy Requirement

The watchlist should support two modes:

1. **Simple watch mode**
   - Only stores tickers and interests.
   - No position size.
   - No cost basis.

2. **Portfolio note mode**
   - Optionally stores:
     - whether the user holds the stock
     - shares
     - average cost
     - personal notes

For MVP, only **simple watch mode** is required.

### 10.14 MVP Acceptance Criteria

The AI Stock Watchlist MVP is complete when:

- The user can add and remove watched stocks.
- The user can view all watched stocks in one table.
- The system can fetch recent stock-related news.
- The system can identify whether a news item is AI-related.
- The system can link news to watched tickers.
- The system can generate a short AI relevance summary for each stock.
- The system can rank watched stocks by attention score.
- The system can show a detail page for each stock.
- The system clearly states that it does not provide financial advice.

---

## 11. Functional Requirements

### 11.1 Dashboard Home Page

The home page should show a ranked feed of AI-related items.

Each item card should include:

- Title.
- Source.
- Time.
- Category.
- Summary.
- Relevance score.
- Novelty score.
- Importance score.
- Related tickers.
- Related topics.
- Link to original source.
- Save button.
- Hide button.
- Mark as important button.
- “Why am I seeing this?” explanation.

### 11.2 Category Views

The dashboard should include separate views:

1. **AI Trends**
2. **AI Research**
3. **AI Stocks**
4. **AI Products**
5. **Chinese Social Trends**
6. **Saved Items**
7. **Daily Digest**

### 11.3 Search

The product should support search across all stored items.

Search fields:

- keyword
- source
- ticker
- topic
- category
- date range
- importance score
- language
- saved status

Search should support natural language queries, such as:

- “Show me recent news about MRVL and AI data centers.”
- “What are the latest AI coding products?”
- “Find recent discussion about agent harness.”
- “Show Chinese social media posts about AI photo tools.”
- “Summarize the most important semiconductor AI news this week.”

### 11.4 Watchlists

The user should be able to configure watchlists.

#### 11.4.1 Topic Watchlist

Example topics:

- agent harness
- skill retrieval
- AI coding
- model routing
- AI infrastructure
- LLM inference
- multimodal models
- RAG
- AI memory
- MCP
- AI evaluation
- AI products
- Chinese AI apps

#### 11.4.2 Stock Watchlist

The Stock Watchlist should be implemented according to Section 10.

#### 11.4.3 Source Watchlist

The user should be able to follow:

- specific X accounts
- specific blogs
- specific companies
- specific GitHub repositories
- specific Product Hunt topics
- specific Xiaohongshu keywords

### 11.5 LLM Classification

Every item should be classified by an LLM or smaller classifier.

Required labels:

- Is AI-related?
- Category.
- Subcategory.
- Related companies.
- Related tickers.
- Related products.
- Related technologies.
- Language.
- Sentiment.
- Market impact type.
- Confidence.

Possible categories:

- technical trend
- research
- product
- stock/company
- social trend
- policy/regulation
- infrastructure
- funding/M&A
- benchmark/evaluation
- open-source release
- tutorial/opinion
- noise/irrelevant

### 11.6 LLM Summarization

The system should generate different summary lengths.

Required summary types:

1. **One-line summary**
   - 1 sentence.

2. **Short card summary**
   - 2–4 bullet points.

3. **Detailed summary**
   - 1–3 paragraphs.

4. **Why it matters**
   - Explain technical, product, or market relevance.

5. **Market watch summary**
   - For stock-related items only.

6. **Technical summary**
   - For research and engineering items only.

### 11.7 Event Clustering

The system should group duplicate or related items into event clusters.

Example:

If multiple sources discuss “Marvell announces new AI custom silicon deal,” the system should create one event cluster containing:

- original press release
- finance news articles
- X posts
- analyst comments
- stock movement
- related company mentions

Each event cluster should include:

- event title
- main summary
- earliest source
- latest update time
- all related sources
- affected tickers
- confidence
- importance score
- timeline

### 11.8 Ranking

The ranking algorithm should consider:

- User interest match.
- Source credibility.
- Freshness.
- Novelty.
- Social engagement.
- Company relevance.
- Stock relevance.
- Technical importance.
- Product adoption signal.
- Cross-source confirmation.
- Whether the item is actionable for reading.

A possible scoring formula:

```text
score =
  0.25 * relevance
+ 0.20 * importance
+ 0.15 * novelty
+ 0.15 * source_quality
+ 0.10 * social_signal
+ 0.10 * stock_relevance
+ 0.05 * freshness
```

The weights should be configurable.

### 11.9 Daily Digest

The system should generate a daily digest.

Digest sections:

1. Top AI technical news.
2. Top AI stock/company news.
3. Top AI product launches.
4. Chinese social trend signals.
5. Research papers worth reading.
6. GitHub/Hugging Face highlights.
7. Watchlist-specific updates.
8. Items to read later.

The digest should be generated once per day, preferably in the morning.

### 11.10 Alerts

The system should support alert rules.

Example alert rules:

- If MU has a high-impact AI-related news item, notify me.
- If MRVL moves more than 5% and there is related AI news, notify me.
- If “agent harness” appears in multiple high-quality sources within 24 hours, notify me.
- If a new AI coding tool becomes highly discussed on Product Hunt, HN, or X, notify me.
- If Xiaohongshu has a new viral AI product trend, notify me.

MVP alerts can be shown in the dashboard. Email, Telegram, Discord, Slack, or browser push can be added later.

---

## 12. Non-Functional Requirements

### 12.1 Performance

For personal use:

- Dashboard initial load: under 3 seconds for recent items.
- Search response: under 5 seconds for normal queries.
- Ingestion latency:
  - news/blog/RSS: 15–60 minutes
  - finance news: 5–30 minutes
  - social media: 15–60 minutes
  - research sources: daily or every few hours
- Daily digest generation: under 5 minutes.

### 12.2 Reliability

The system should tolerate source failures.

If one source fails:

- The ingestion job should not crash the entire pipeline.
- The error should be logged.
- The source should retry later.
- The dashboard should show source health.

### 12.3 Maintainability

Each source connector should be modular.

The system should make it easy to:

- Add a new source.
- Disable a source.
- Change polling frequency.
- Change keywords.
- Change API keys.
- Update parsing logic.

### 12.4 Cost Control

The system should minimize API and LLM cost.

Cost-control mechanisms:

- Deduplicate before LLM summarization.
- Use cheaper models for classification.
- Use stronger models only for important items.
- Cache LLM outputs.
- Batch LLM requests.
- Limit social API calls.
- Use RSS where possible.
- Summarize only high-relevance content.

### 12.5 Privacy

The product is personal and should protect user preferences.

The system should not expose:

- User stock holdings.
- User reading history.
- User notes.
- API keys.
- Private source configuration.

API keys should be stored in environment variables or an encrypted secrets manager.

### 12.6 Compliance

The system should:

- Respect source terms of service.
- Avoid scraping private or restricted content.
- Store source URLs and attribution.
- Avoid republishing full copyrighted articles.
- Use summaries and short excerpts only where allowed.
- Support deletion of stored content.
- Avoid presenting outputs as financial advice.

---

## 13. LLM and Compute Requirements

### 13.1 MacBook M3 Feasibility

A MacBook with an M3 chip should be enough for the MVP if most LLM work uses API-based models.

Recommended local workload:

- Backend server.
- Database.
- Scheduler.
- Lightweight parsing.
- Embedding generation with small local models, optional.
- Basic frontend.
- Development environment.

The project does not require a local GPU unless the user wants to run larger local LLMs.

### 13.2 Recommended LLM Strategy

Use API models for higher-quality tasks:

- Summarization.
- Event clustering explanations.
- Market impact reasoning.
- Daily digest generation.
- Natural language search.

Use cheaper or local models for:

- Deduplication.
- Embeddings.
- Simple classification.
- Language detection.
- Keyword extraction.

### 13.3 Suggested Model Pipeline

For each item:

1. Rule-based prefilter.
2. Embedding similarity filter.
3. Cheap LLM classifier.
4. Deduplication.
5. Stronger LLM summary only if relevant.
6. Event clustering.
7. Ranking.
8. Display.

### 13.4 Hardware Requirement

MVP local development:

- MacBook M3.
- 16GB RAM minimum preferred.
- 512GB storage preferred.
- Docker optional.
- No dedicated GPU required.

Small deployment:

- Cloud VM with 2–4 vCPU.
- 4–8GB RAM.
- PostgreSQL.
- Background worker.
- Optional object storage.

---

## 14. Recommended Technical Architecture

### 14.1 Frontend

Recommended:

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui or similar component library

Main pages:

- Dashboard
- AI Trends
- AI Stocks
- AI Products
- Research
- Chinese Trends
- Saved Items
- Search
- Settings
- Source Health

### 14.2 Backend

Recommended:

- Python FastAPI

Reasons:

- Strong ecosystem for data ingestion.
- Good LLM API support.
- Good financial data API support.
- Good background job support.
- Easy integration with ML/embedding libraries.

Alternative:

- Node.js / TypeScript backend if the user wants full-stack TypeScript.

### 14.3 Database

Recommended:

- PostgreSQL
- pgvector extension for embeddings

Tables:

- sources
- raw_items
- normalized_items
- event_clusters
- summaries
- tickers
- topics
- user_preferences
- source_runs
- alerts
- daily_digests

### 14.4 Background Jobs

Recommended:

- Celery + Redis
- or RQ + Redis
- or APScheduler for simpler MVP

Jobs:

- Fetch source data.
- Normalize items.
- Run classification.
- Run summarization.
- Update event clusters.
- Generate digest.
- Check alerts.

### 14.5 Storage

For MVP:

- Store text and metadata in PostgreSQL.
- Avoid storing large images or videos.
- Store original URLs instead.

Optional later:

- S3-compatible storage for screenshots or archived pages, only where legally permitted.

---

## 15. Data Model

### 15.1 Source

```text
Source {
  id
  name
  type
  access_method
  base_url
  auth_required
  rate_limit
  polling_interval
  enabled
  priority
  terms_notes
  created_at
  updated_at
}
```

### 15.2 Raw Item

```text
RawItem {
  id
  source_id
  external_id
  url
  raw_title
  raw_text
  raw_author
  raw_metadata
  fetched_at
  published_at
  content_hash
}
```

### 15.3 Normalized Item

```text
NormalizedItem {
  id
  raw_item_id
  title
  url
  source_name
  author
  language
  published_at
  text
  category
  subcategory
  tickers
  companies
  products
  topics
  sentiment
  relevance_score
  importance_score
  novelty_score
  source_quality_score
  stock_impact_score
  summary_short
  summary_detailed
  why_it_matters
  created_at
}
```

### 15.4 Event Cluster

```text
EventCluster {
  id
  title
  canonical_summary
  category
  tickers
  companies
  topics
  first_seen_at
  last_updated_at
  source_count
  importance_score
  market_impact_score
  status
}
```

### 15.5 User Preference

```text
UserPreference {
  id
  watched_topics
  watched_tickers
  watched_companies
  preferred_sources
  blocked_sources
  language_preferences
  ranking_weights
  alert_rules
}
```

### 15.6 Stock Watchlist Item

```text
StockWatchlistItem {
  id
  user_id
  ticker
  company_name
  exchange
  sector
  industry
  priority
  group_name
  is_pinned
  is_holding
  shares
  average_cost
  related_keywords
  related_companies
  related_ai_themes
  notes
  created_at
  updated_at
}
```

---

## 16. MVP Feature List

### 16.1 Must Have

- Source ingestion from:
  - arXiv
  - Hacker News
  - selected RSS feeds
  - Alpha Vantage or Finnhub
  - Product Hunt
  - GitHub search
- Dashboard feed.
- Topic and ticker watchlists.
- AI Stock Watchlist.
- LLM classification.
- LLM summarization.
- Daily digest.
- Basic search.
- Save/hide item.
- Source health page.
- Manual URL submission.

### 16.2 Should Have

- Hugging Face trending models and Spaces.
- Event clustering.
- Stock-news timeline.
- Alert rules.
- Chinese keyword support.
- Basic Xiaohongshu connector research/prototype.

### 16.3 Could Have

- X/Twitter integration.
- Reddit integration.
- WeChat public account integration.
- Email digest.
- Telegram bot.
- Browser extension.
- Multi-user support.
- Personalized recommendation learning.

### 16.4 Won’t Have in MVP

- Automated trading.
- Public social features.
- Payment.
- Full mobile app.
- Large-scale crawling.
- Custom LLM training.

---

## 17. User Stories

### 17.1 AI Trend Monitoring

As a user, I want to see the most important AI technical trends today, so that I can quickly understand what people in AI are discussing.

Acceptance criteria:

- The dashboard shows a ranked list of AI trend items.
- Each item has a summary and “why it matters.”
- The user can filter by topic.
- The user can save important items.

### 17.2 Stock Watch

As a user, I want to monitor AI-related news about selected stocks, so that I can understand whether any company event may affect stocks I care about.

Acceptance criteria:

- The system supports an editable stock watchlist.
- The system tracks watched tickers.
- The system links news to tickers.
- The system shows price movement around news time.
- The system labels possible market impact.
- The system includes a disclaimer that it is not financial advice.

### 17.3 Product Discovery

As a user, I want to discover new AI products, so that I can understand what AI tools are becoming popular.

Acceptance criteria:

- The system collects products from Product Hunt, HN, GitHub, Hugging Face, and selected social sources.
- Each product item includes what the product does.
- The system identifies whether the product is for coding, productivity, media, search, education, business, or entertainment.
- The system ranks products by novelty and traction.

### 17.4 Research Discovery

As a user, I want to see important AI papers without reading all arXiv submissions, so that I can follow technical development efficiently.

Acceptance criteria:

- The system collects arXiv papers by category and keyword.
- The system summarizes each paper.
- The system identifies key contribution, method, and relevance.
- The system ranks papers by topic match and potential impact.

### 17.5 Chinese Social Trend Monitoring

As a user, I want to monitor Chinese AI product trends on Xiaohongshu, so that I can understand consumer adoption signals in China.

Acceptance criteria:

- The system supports Chinese keywords.
- The system stores public post metadata where legally available.
- The system summarizes Chinese posts in English.
- The system identifies product names and use cases.
- The system marks this connector as optional or experimental until access is stable.

---

## 18. Ranking and Scoring Details

### 18.1 Relevance Score

Measures whether the item matches the user’s interests.

Inputs:

- Topic match.
- Ticker match.
- Company match.
- Product category match.
- User feedback history.

### 18.2 Importance Score

Measures objective importance.

Inputs:

- Source credibility.
- Cross-source confirmation.
- Company size.
- Technical novelty.
- Social engagement.
- Financial materiality.
- Research significance.

### 18.3 Novelty Score

Measures whether the item is new rather than a repeated version of old news.

Inputs:

- Similarity to previous items.
- First-seen time.
- Number of duplicate sources.
- Event cluster status.

### 18.4 Stock Impact Score

Measures potential market relevance.

Inputs:

- Ticker match.
- Event type.
- Source type.
- Mention of revenue, guidance, supply, demand, capex, earnings, partnership, regulation, or analyst rating.
- Price movement.
- Volume movement.
- Historical sensitivity if available.

### 18.5 Social Signal Score

Measures early social traction.

Inputs:

- Likes.
- Reposts.
- Comments.
- Upvotes.
- GitHub stars.
- Product Hunt votes.
- HN points.
- Frequency of mentions.
- Growth rate.

---

## 19. LLM Prompting Requirements

### 19.1 Classification Prompt Output

The classifier should return structured JSON.

Example:

```json
{
  "is_ai_related": true,
  "category": "stock_company_event",
  "subcategory": "semiconductor_ai_infrastructure",
  "related_tickers": ["MRVL"],
  "related_companies": ["Marvell Technology"],
  "related_topics": ["AI data center", "custom silicon"],
  "sentiment": "positive",
  "market_impact": "potentially_positive",
  "confidence": 0.78,
  "reason": "The article discusses AI data center demand and Marvell's custom silicon business."
}
```

### 19.2 Summary Prompt Output

The summarizer should return:

```json
{
  "one_line_summary": "...",
  "bullet_summary": ["...", "...", "..."],
  "why_it_matters": "...",
  "technical_relevance": "...",
  "market_relevance": "...",
  "uncertainties": ["...", "..."]
}
```

### 19.3 Market Impact Prompt Output

For stock-related news:

```json
{
  "related_tickers": ["MU"],
  "event_type": "earnings_or_guidance",
  "possible_impact": "positive",
  "confidence": 0.72,
  "already_priced_in": "unknown",
  "key_evidence": ["...", "..."],
  "risk_factors": ["...", "..."],
  "not_financial_advice": true
}
```

---

## 20. UI Requirements

### 20.1 Item Card

Each item card should show:

- Title.
- Source and time.
- Category badge.
- Related tickers.
- Related topics.
- One-line summary.
- Why it matters.
- Importance score.
- Buttons:
  - open source
  - save
  - hide
  - mark important
  - show details

### 20.2 Event Cluster Page

Each event page should show:

- Event summary.
- Timeline.
- Related sources.
- Related tickers.
- Related topics.
- Price chart for related ticker.
- LLM-generated explanation.
- Uncertainty notes.

### 20.3 Stock Watchlist Page

The Stock Watchlist page should show:

- Watched stocks.
- Current price.
- Daily movement.
- Latest AI-related event.
- AI news count.
- High-impact news count.
- Sentiment.
- Priority.
- Group.
- Pin status.
- Last updated time.

### 20.4 Stock Detail Page

Each watched stock should have a detail page showing:

- Company overview.
- Recent AI-related news.
- Price chart.
- News timeline.
- Event clusters.
- Most-mentioned topics.
- Recent sentiment.
- Watchlist notes.

### 20.5 Topic Page

Each topic page should show:

- Topic definition.
- Recent items.
- Trending sources.
- Related papers.
- Related products.
- Related companies.
- Timeline of activity.

---

## 21. Development Roadmap

### Phase 0: Source Validation

Goal: Confirm which sources are technically and legally feasible.

Tasks:

- Test arXiv API.
- Test Hacker News API.
- Test GitHub API.
- Test Product Hunt API.
- Test Alpha Vantage or Finnhub.
- Test RSS ingestion.
- Research X API cost.
- Research Xiaohongshu access options.
- Decide which sources enter MVP.

Deliverable:

- Source feasibility table.
- API key list.
- Cost estimate.
- Risk notes.

### Phase 1: MVP Backend

Goal: Build ingestion and storage.

Tasks:

- Set up FastAPI backend.
- Set up PostgreSQL.
- Define database schema.
- Build source connector interface.
- Implement arXiv connector.
- Implement HN connector.
- Implement RSS connector.
- Implement finance news connector.
- Implement stock watchlist backend.
- Implement basic scheduler.
- Implement raw item and normalized item storage.

Deliverable:

- Backend can collect and store items from core sources.

### Phase 2: LLM Processing

Goal: Add intelligence layer.

Tasks:

- Implement AI relevance classifier.
- Implement category classifier.
- Implement ticker/topic extraction.
- Implement stock-event classifier.
- Implement summarizer.
- Implement deduplication.
- Implement ranking.
- Implement daily digest generation.

Deliverable:

- Backend can produce ranked, summarized AI intelligence feed.

### Phase 3: Frontend Dashboard

Goal: Build usable web interface.

Tasks:

- Build Next.js frontend.
- Build dashboard page.
- Build category pages.
- Build AI Stock Watchlist page.
- Build stock detail page.
- Build search.
- Build item detail page.
- Build settings page.
- Build source health page.

Deliverable:

- User can browse, search, save, and manage AI intelligence items.

### Phase 4: Alerts and Personalization

Goal: Make the product personally useful.

Tasks:

- Add alert rules.
- Add user feedback.
- Add personalized ranking weights.
- Add daily digest page.
- Add optional email digest.
- Add manual URL submission.

Deliverable:

- System adapts to the user’s watched topics and stocks.

### Phase 5: Advanced Sources

Goal: Add noisier but high-signal sources.

Tasks:

- Add X/Twitter if cost is acceptable.
- Add Reddit if access is approved.
- Add Hugging Face trending.
- Add Xiaohongshu experimental connector if compliant.
- Add more finance sources.
- Add more company blogs.

Deliverable:

- System covers both mainstream news and early social signals.

---

## 22. Technical Risks

### 22.1 Source Access Risk

Some platforms may limit API access, change pricing, or block scraping.

Mitigation:

- Use official APIs where possible.
- Keep each connector modular.
- Avoid depending on one source.
- Support manual URL submission.
- Store source health status.

### 22.2 LLM Cost Risk

Summarizing too much content may become expensive.

Mitigation:

- Filter before summarization.
- Deduplicate before summarization.
- Use cheap models for simple tasks.
- Cache outputs.
- Summarize only relevant items.

### 22.3 Noise Risk

Social media data may be noisy.

Mitigation:

- Use source credibility scores.
- Require cross-source confirmation for high-impact labels.
- Separate “early signal” from “confirmed event.”
- Let user hide bad sources.

### 22.4 Financial Interpretation Risk

The system may overstate market impact.

Mitigation:

- Use conservative labels.
- Show confidence and uncertainty.
- Avoid buy/sell recommendations.
- Include financial disclaimer.
- Show original sources.

### 22.5 Compliance Risk

Some sources may not allow scraping or content storage.

Mitigation:

- Respect terms of service.
- Store metadata and summaries rather than full articles where appropriate.
- Do not bypass access controls.
- Attribute sources.
- Allow deletion.

---

## 23. Success Metrics

### 23.1 MVP Success Metrics

The MVP is successful if:

- It collects useful AI-related items every day.
- At least 70% of displayed items are relevant.
- Daily digest is useful enough that the user reads it regularly.
- Stock watch page captures major AI-related company news.
- User can maintain an editable AI Stock Watchlist.
- User can find important AI product launches without manually checking many websites.
- The system runs on the user’s MacBook or a low-cost cloud server.

### 23.2 Quality Metrics

Track:

- Relevance precision.
- Duplicate rate.
- Summary quality.
- Source failure rate.
- Digest usefulness.
- Alert usefulness.
- User save/hide ratio.
- Number of high-value items found per day.

### 23.3 Cost Metrics

Track:

- API cost per month.
- LLM cost per month.
- Number of LLM calls per item.
- Cost per daily digest.
- Cost per alert.

---

## 24. Recommended MVP Stack

### 24.1 Local Development

- Frontend: Next.js + TypeScript.
- Backend: FastAPI + Python.
- Database: PostgreSQL + pgvector.
- Scheduler: APScheduler first, Celery later if needed.
- Cache/Queue: Redis.
- LLM: OpenAI / Anthropic / Gemini API, configurable.
- Embeddings: API embeddings or local sentence-transformer.
- Deployment: local Docker Compose first.

### 24.2 Minimal Cloud Deployment

- Render, Railway, Fly.io, or a small VPS.
- Managed PostgreSQL if possible.
- Environment variables for API keys.
- Cron or background worker for ingestion.

---

## 25. Initial MVP Source Set

The recommended first implementation should use:

1. arXiv API.
2. Hacker News API.
3. GitHub API.
4. Product Hunt API.
5. Hugging Face Hub API.
6. RSS feeds from selected AI company blogs.
7. Alpha Vantage or Finnhub for stock/company news.
8. Manual URL submission.

X/Twitter and Xiaohongshu should be added after validating cost, access, and compliance.

---

## 26. Example Daily Digest Output

# Daily AI Intelligence Brief

## Top Technical Trends

1. Agent harness systems are receiving more attention in open-source agent frameworks.
2. New coding-agent repositories are gaining traction on GitHub.
3. Multiple papers discuss tool-use evaluation and long-horizon agent reliability.

## Stock Watch

### MU
Recent AI infrastructure news mentions memory demand from data centers. No direct company-specific event detected today.

### MRVL
Several sources discuss custom silicon demand for AI data centers. Monitor for analyst commentary and earnings guidance.

### SNDK
No major AI-related event detected today.

## Product Watch

1. A new AI coding assistant launched on Product Hunt.
2. A Hugging Face Space for video generation is trending.
3. Several Xiaohongshu posts discuss AI photo editing workflows.

## Research Watch

1. New arXiv paper on agent evaluation.
2. New arXiv paper on tool-use reliability.
3. New arXiv paper on efficient inference.

## Suggested Reading

- One technical blog.
- One research paper.
- One stock/company article.
- One product launch.

---

## 27. Final Recommendation

The project is feasible on a MacBook with M3 chips if the system uses API-based LLMs and avoids local large-model inference.

The most important design decision is to build a strong, modular source layer first. The MVP should prioritize stable APIs and RSS feeds, then gradually add expensive or unstable sources such as X/Twitter and Xiaohongshu.

The best first version should be a personal AI intelligence dashboard with:

- reliable ingestion,
- strong deduplication,
- LLM-based summarization,
- topic and stock watchlists,
- AI Stock Watchlist,
- daily digest,
- and source health monitoring.

The product should optimize for personal usefulness rather than scale.
