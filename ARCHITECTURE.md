# BiasLens — Architecture Guide

> **AI-powered trading behavior analysis.**
> Detect cognitive biases in trading logs, simulate behavioral corrections, and get personalized AI coaching.

---

## Table of Contents

1. [High-Level Overview](#1-high-level-overview)
2. [Directory Structure](#2-directory-structure)
3. [Backend (Python / FastAPI)](#3-backend-python--fastapi)
   - [Entry Point & Configuration](#31-entry-point--configuration)
   - [API Layer](#32-api-layer)
   - [Core Analysis Engine](#33-core-analysis-engine)
   - [Bias Detectors](#34-bias-detectors)
   - [Machine Learning Pipeline](#35-machine-learning-pipeline)
   - [SHAP Explainability](#36-shap-explainability)
   - [LLM Integration (Gemini)](#37-llm-integration-gemini)
   - [Utilities](#38-utilities)
   - [Schemas & Type Safety](#39-schemas--type-safety)
4. [Frontend (Next.js / TypeScript)](#4-frontend-nextjs--typescript)
   - [App Shell & Routing](#41-app-shell--routing)
   - [Components](#42-components)
   - [API Client](#43-api-client)
   - [Type Definitions](#44-type-definitions)
   - [Styling System](#45-styling-system)
5. [Shared Module](#5-shared-module)
6. [Machine Learning Deep-Dive](#6-machine-learning-deep-dive)
   - [Feature Engineering (18 Features)](#61-feature-engineering-18-features)
   - [Training Pipeline](#62-training-pipeline)
   - [Model Architecture & Performance](#63-model-architecture--performance)
7. [Bias Detection Algorithms](#7-bias-detection-algorithms)
   - [Overtrading Detector](#71-overtrading-detector)
   - [Loss Aversion Detector](#72-loss-aversion-detector)
   - [Revenge Trading Detector](#73-revenge-trading-detector)
   - [Score Fusion (Heuristic + ML)](#74-score-fusion-heuristic--ml)
8. [Data Flow](#8-data-flow)
9. [Infrastructure & DevOps](#9-infrastructure--devops)
   - [Docker](#91-docker)
   - [Modal (Cloud Deployment)](#92-modal-cloud-deployment)
   - [CI/CD](#93-cicd)
   - [Environment Variables](#94-environment-variables)
10. [API Reference](#10-api-reference)
11. [Testing](#11-testing)
12. [Getting Started](#12-getting-started)

---

## 1. High-Level Overview

BiasLens is a full-stack application that analyzes trading behavior to detect cognitive biases and provide AI-driven coaching:

| Bias | Description | Detection Method |
|------|-------------|-----------------|
| **Calm** | Disciplined, low-bias trading behavior | Inverse of worst bias + ML calm confidence |
| **Overtrading** | Excessive trade frequency and burst patterns | Trades/day + rolling burst windows |
| **Loss Aversion** | Holding losers longer than winners | Hold-time ratio analysis |
| **Revenge Trading** | Rapid, larger re-entries after losses | Time + size pattern matching |

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Next.js Frontend (port 3000)                │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐   │   │
│  │  │CSV Upload│ │Dashboard │ │ Insights │ │ Coaching  │   │   │
│  │  │(Dropzone)│ │(Stats)   │ │ (Charts) │ │ (Gemini)  │   │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘   │   │
│  │       │             │            │              │         │   │
│  │       └─────────────┴────────────┴──────────────┘         │   │
│  │                         │ fetch()                         │   │
│  └─────────────────────────┼────────────────────────────────┘   │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │ HTTP / JSON
┌────────────────────────────┼─────────────────────────────────────┐
│                    FastAPI Backend (port 8000)                    │
│  ┌─────────────────────────┼────────────────────────────────┐    │
│  │                    API Router Layer                       │    │
│  │  POST /api/analyze     POST /api/counterfactual            │    │
│  │  POST /api/report     GET  /api/news                      │    │
│  │  POST /api/chat       POST /api/shap-explain              │    │
│  │  POST /api/trade-insights                                 │    │
│  └─────────┬───────────────┬────────────────────────────────┘    │
│            │               │                                      │
│  ┌─────────▼───────┐  ┌───▼──────────────┐  ┌──────────────┐    │
│  │ Analysis Engine │  │ Counterfactual   │  │ Gemini LLM   │    │
│  │ ┌─────────────┐ │  │ Simulator        │  │ Client       │    │
│  │ │ Overtrading  │ │  └──────────────────┘  └──────────────┘    │
│  │ │ Loss Aversion│ │                                             │
│  │ │ Revenge      │ │  ┌──────────────────┐                      │
│  │ └──────┬──────┘ │  │ XGBoost ML Model │                      │
│  │        │        │  │ (18 features,    │                      │
│  │        ├────────┤  │  4 classes)      │                      │
│  │        ▼        │  └──────────────────┘                      │
│  │  Score Fusion   │                                             │
│  │  (60% heuristic │  ┌──────────────────┐                      │
│  │   + 40% ML)     │  │ SHAP Explainer   │                      │
│  └─────────────────┘  │ (TreeExplainer)  │                      │
│                        └──────────────────┘                      │
└──────────────────────────────────────────────────────────────────┘
```

**Tech Stack:**

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, TailwindCSS, shadcn/ui, Recharts, TanStack Table |
| Backend | Python 3.11+, FastAPI, Pydantic v2, pandas, NumPy |
| ML | XGBoost, scikit-learn, SHAP, joblib |
| LLM | Google Gemini 1.5 Flash (via REST API) |
| DevOps | Docker, docker-compose, Modal (serverless), GitHub Actions CI |

---

## 2. Directory Structure

```
QHacks_2026/
├── .env.example                    # Environment variable template
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI pipeline
├── docker-compose.yml              # Multi-service orchestration
├── modal_app.py                    # Modal serverless deployment config
├── requirements.txt                # Python dependencies
├── trading_datasets/               # Training data (4 CSVs × 10K trades)
│   ├── calm_trader.csv
│   ├── overtrader.csv
│   ├── loss_averse_trader.csv
│   └── revenge_trader.csv
│
├── backend/
│   ├── Dockerfile                  # Python backend container
│   ├── main.py                     # FastAPI app factory
│   ├── __init__.py
│   │
│   ├── api/                        # REST endpoint handlers
│   │   ├── analyze.py              # POST /api/analyze
│   │   ├── chat.py                 # POST /api/chat (multi-turn AI chatbot)
│   │   ├── counterfactual.py       # POST /api/counterfactual
│   │   ├── news.py                 # GET  /api/news
│   │   ├── report.py               # POST /api/report
│   │   ├── shap_explain.py         # POST /api/shap-explain
│   │   └── trade_insights.py       # POST /api/trade-insights
│   │
│   ├── core/                       # Business logic
│   │   ├── schemas.py              # Pydantic v2 request/response models
│   │   └── analysis_engine.py      # Orchestrates detectors + ML + scoring
│   │
│   ├── detectors/                  # Heuristic bias detection
│   │   ├── common.py               # score_to_severity() helper
│   │   ├── overtrading.py          # Trade frequency / burst analysis
│   │   ├── loss_aversion.py        # Hold-time ratio analysis
│   │   └── revenge_trading.py      # Re-entry pattern detection
│   │
│   ├── ml/                         # Machine learning pipeline
│   │   ├── features.py             # 18-feature extraction + windowing
│   │   ├── model.py                # BiasMLClassifier (load + predict)
│   │   ├── shap_explainer.py       # SHAP TreeExplainer wrapper + singleton
│   │   ├── train_xgboost.py        # Training script (run standalone)
│   │   └── saved_models/
│   │       ├── bias_xgb.joblib     # Trained XGBoost model artifact
│   │       └── training_report.json # CV accuracy, feature importances
│   │
│   ├── llm/                        # LLM integration
│   │   ├── gemini_client.py        # Gemini API wrapper + coaching/news
│   │   └── prompts.py              # System/coaching/news prompt templates
│   │
│   ├── utils/                      # Shared utilities
│   │   ├── config.py               # pydantic-settings env loader
│   │   ├── data_loader.py          # CSV parsing + column auto-detection
│   │   └── logger.py               # Logging configuration
│   │
│   └── tests/
│       └── test_detectors.py       # 6 unit tests for all 3 detectors
│
├── frontend/
│   ├── Dockerfile                  # Multi-stage Next.js container
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   │
│   ├── app/                        # Next.js App Router
│   │   ├── layout.tsx              # Root layout (header, container)
│   │   ├── page.tsx                # Main page (upload → dashboard)
│   │   └── globals.css             # Tailwind base + CSS variables
│   │
│   ├── components/                 # React components
│   │   ├── csv-upload.tsx          # Drag-and-drop CSV with auto-mapping
│   │   ├── bias-scorecards.tsx     # 4 expandable bias cards with SHAP charts
│   │   ├── shap-stacked-chart.tsx  # Diverging stacked bar SHAP visualization
│   │   ├── trade-table.tsx         # Sortable/filterable trade log
│   │   ├── insights-charts.tsx     # Time-bucketed charts (4 panels)
│   │   ├── counterfactual-panel.tsx# What-if simulation UI
│   │   ├── coaching-tab.tsx        # Gemini coaching report
│   │   ├── news-tab.tsx            # News context lookup
│   │   └── ui/                     # shadcn/ui primitives
│   │       ├── badge.tsx
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       └── tabs.tsx
│   │
│   ├── lib/                        # Utility functions
│   │   ├── api.ts                  # Backend API client (fetch wrappers)
│   │   └── utils.ts                # cn(), formatCurrency(), formatPercent()
│   │
│   ├── types/
│   │   └── index.ts                # TypeScript interfaces (mirrors schemas.py)
│   │
│   └── hooks/
│       └── use-analysis.ts         # React hook for analysis state
│
└── shared/
    ├── constants.py                # Shared constants (bias names, defaults)
    ├── contracts/                  # API contract definitions (placeholder)
    └── types.ts                    # Shared TS types (placeholder)
```

---

## 3. Backend (Python / FastAPI)

### 3.1 Entry Point & Configuration

**`backend/main.py`** — App factory pattern:

```python
def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="BiasLens API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, ...)
    app.include_router(analyze_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(counterfactual_router, prefix="/api")
    app.include_router(report_router, prefix="/api")
    app.include_router(news_router, prefix="/api")
    app.include_router(shap_explain_router, prefix="/api")
    app.include_router(trade_insights_router, prefix="/api")
    return app
```

**`backend/utils/config.py`** — Uses `pydantic-settings` to load environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | `None` | Google Gemini API key for coaching/news |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model to use |
| `NEWS_API_KEY` | `None` | NewsAPI.org key for headlines |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

Run with: `uvicorn backend.main:app --reload`

### 3.2 API Layer

Seven routers, all prefixed with `/api`:

#### `POST /api/analyze`
- **Input**: Multipart form with CSV file + optional JSON `mapping` string, OR JSON body with `csv_content`/`trades`
- **Processing**: CSV → DataFrame → run 3 detectors + optional ML → score fusion
- **Output**: `AnalyzeResponse` with bias_scores, flagged_trades, evidence, feature_stats, normalized_trades

#### `POST /api/counterfactual`
- **Input**: JSON `{ trades: [...], rules: { cooldown_minutes_after_loss, max_trades_per_day, cap_size_after_loss } }`
- **Processing**: Replays trade sequence applying behavioral rules, removes/modifies trades
- **Output**: `CounterfactualResponse` with original vs. simulated PnL, trade-level details

#### `POST /api/report`
- **Input**: JSON `{ analysis: { bias_scores, feature_stats, ... }, bias_event?, include_headlines? }`
- **Processing**: Constructs prompt → calls Gemini → extracts numbered coaching plan
- **Output**: `ReportResponse` with markdown report + coaching_plan steps

#### `GET /api/news?date=YYYY-MM-DD&bias=`
- **Input**: Query params for date and optional bias filter
- **Processing**: Fetches headlines from NewsAPI (or returns placeholder if no key), then optionally calls Gemini for context
- **Output**: `NewsResponse` with date + headline items

#### `POST /api/chat`
- **Input**: JSON `{ messages: [{ role, text }], analysis_context: { bias_scores, flagged_trades, ... } }`
- **Processing**: Builds condensed context summary from analysis data, sends multi-turn conversation to Gemini
- **Output**: `ChatResponse` with `reply` string
- **Context window**: Caps flagged trades at 30 and omits full normalized_trades to keep prompt size manageable

#### `POST /api/shap-explain`
- **Input**: JSON `{ trades: [...], mapping?: { ... } }`
- **Processing**: Converts trades to DataFrame, extracts windowed features, runs SHAP TreeExplainer on XGBoost model
- **Output**: `ShapExplainResponse` with per-window SHAP values, feature names, base values, and predictions
- **Availability**: Returns 503 if SHAP library or trained model is not available

#### `POST /api/trade-insights`
- **Input**: JSON `{ flagged_trades, bias_scores, normalized_trades, symbols?, date_range? }`
- **Processing**: Auto-extracts symbols/dates, searches ticker news via Gemini with Google Search grounding, generates per-trade AI explanations
- **Output**: `TradeInsightsResponse` with per-trade insights, summary, and market context
- **Graceful degradation**: Returns fallback message on Gemini rate-limit (429)

### 3.3 Core Analysis Engine

**`backend/core/analysis_engine.py`** orchestrates the full analysis pipeline:

```
Input DataFrame + analysis_mode (rules_only | ml_only | mixed)
      │
      ├──→ detect_overtrading(df)      → score, flags, evidence, stats
      ├──→ detect_loss_aversion(df)    → score, flags, evidence, stats
      ├──→ detect_revenge_trading(df)  → score, flags, evidence, stats
      │
      ├──→ (ml_only/mixed) BiasMLClassifier — windowed predictions (50-trade windows, stride 25)
      │
      ├──→ Score Fusion (mode-dependent):
      │      rules_only: final_score = heuristic_score
      │      ml_only:    final_score = ml_probability × 100
      │      mixed:      final_score = 0.6 × heuristic + 0.4 × ML
      │
      ├──→ Flag aggregation (mode-dependent):
      │      rules_only: rule flags only
      │      ml_only:    ML per-trade tags (threshold ≥ 0.3)
      │      mixed:      intersection of rule flags AND ML tags
      │
      ├──→ Calm score: inverse of worst bias, blended with ML calm probability
      │
      └──→ compute_feature_stats(df)   → aggregate stats
```

**Analysis Modes:**

| Mode | Score Source | Trade Flagging | Use Case |
|------|-------------|----------------|----------|
| `rules_only` | Heuristic detectors only | Rule-based flags | Interpretable, no model needed |
| `ml_only` | XGBoost probabilities only | ML per-trade tags (prob ≥ 0.3) | Pure ML classification |
| `mixed` (default) | 60% heuristic + 40% ML | Intersection (both must agree) | Best of both — high precision |

**Score to Severity mapping** (`detectors/common.py`):
- `≥ 70` → **high**
- `≥ 40` → **medium**
- `< 40` → **low**

### 3.4 Bias Detectors

Each detector returns a standardized dict:
```python
{
    "score": float,          # 0–100
    "flags": list[int],      # trade indices flagged
    "evidence": list[dict],  # metric/value/note items
    "stats": dict,           # detector-specific statistics
}
```

#### Overtrading Detector
- **Metrics**: avg trades/day, max trades/day, max burst trades
- **Burst window**: Rolling 10-minute window; counts trades within window
- **Scoring formula**: `score = clip((0.6 × day_component + 0.4 × burst_component) × 50, 0, 100)`
  - `day_component = min(avg_trades_per_day / 15, 2.0)`
  - `burst_component = min(max_burst / 5, 2.0)`
- **Flagging**: Trades on high-activity days OR within burst windows

#### Loss Aversion Detector
- **Metrics**: avg winner hold time, avg loser hold time, loser-to-winner hold ratio
- **Scoring formula**: `score = clip((hold_ratio - 1.0) × 60, 0, 100)`
  - A ratio of 1.0 (equal hold times) → score 0
  - A ratio of 2.67+ → score 100
- **Flagging**: Losing trades held > 1.5× the average winner hold time
- **Hold time source**: `hold_minutes` column if available, otherwise inferred from next-trade timestamps

#### Revenge Trading Detector
- **Metrics**: revenge event count, event rate (events per trade)
- **Detection**: For each loss, checks next 5 trades within 15-min window for entries ≥ 1.25× the loss position size
- **Scoring formula**: `score = clip(event_rate × 400, 0, 100)`
  - 25% event rate → score 100
- **Flagging**: The specific re-entry trades identified as revenge

### 3.5 Machine Learning Pipeline

See [Section 6](#6-machine-learning-deep-dive) for detailed ML documentation.

### 3.6 SHAP Explainability

**`backend/ml/shap_explainer.py`** — Wraps `shap.TreeExplainer` around the XGBoost model:

- **Module-level singleton**: `get_explainer()` returns a cached `ShapExplainer` instance to avoid re-creating on every request
- **Guarded imports**: `import shap` is wrapped in try/except; `is_available` property returns `False` if SHAP or model is missing
- **`explain_windows(df)`**: Extracts windowed features (same 50/25 windowing as analysis engine), computes SHAP values per window per class
- **Output**: Feature names, class labels, base values, and per-window SHAP value arrays with predictions
- **NaN/Inf sanitization**: Replaces non-finite SHAP values with 0.0

**`backend/api/shap_explain.py`** — REST endpoint (`POST /api/shap-explain`):
- Accepts trade list, converts to DataFrame, delegates to `ShapExplainer.explain_windows()`
- Returns `ShapExplainResponse` schema

### 3.7 LLM Integration (Gemini)

**`backend/llm/gemini_client.py`** — REST client for Google's Gemini API:

- **Model**: `gemini-1.5-flash` (configurable)
- **Authentication**: API key passed as query parameter
- **System prompt**: "You are a behavioral trading coach. Ground your answers in provided data or headlines. Do not hallucinate."
- **Graceful degradation**: Returns placeholder message when API key not configured

**Two LLM functions:**

1. **`generate_coaching_report(analysis, counterfactual)`** → `(markdown, plan_steps[])`
   - Sends bias scores + counterfactual results to Gemini
   - Requests markdown report + 7-day correction plan
   - Falls back to hardcoded 4-step plan if Gemini output doesn't contain numbered steps

2. **`generate_news_context(date, bias)`** → `{ headlines, context }`
   - Fetches headlines from NewsAPI
   - Sends headlines to Gemini for behavioral interpretation

### 3.8 Utilities

#### Data Loader (`utils/data_loader.py`)
- **`csv_to_dataframe(csv_content, mapping)`** — Parses CSV string into a clean DataFrame
- **Column auto-detection**: If default mapping fails, tries `COLUMN_ALIASES` dictionary to guess columns:
  ```python
  COLUMN_ALIASES = {
      "timestamp": ["timestamp", "time", "date", "datetime", ...],
      "symbol":    ["symbol", "asset", "ticker", "instrument", ...],
      "price":     ["price", "entry_price", "exec_price", ...],
      "pnl":       ["pnl", "profit_loss", "profit", "pl", ...],
      ...
  }
  ```
- **Coercion**: Timestamps → UTC datetime, sides → lowercase, symbols → uppercase, numerics → float
- **Hold-time inference**: When `hold_minutes` is missing, estimates from time-to-next-trade per symbol

### 3.9 Schemas & Type Safety

All request/response models use **Pydantic v2** with strict validation:

| Schema | Purpose |
|--------|---------|
| `ColumnMapping` | Maps CSV headers to internal field names |
| `TradeInput` | Single trade with side normalization validator |
| `AnalyzeRequest` | CSV or JSON trade input |
| `AnalyzeResponse` | Full analysis result |
| `BiasScore` | score (0–100) + severity + rationale |
| `BiasFlag` | Flagged trade with index, tags, reason |
| `EvidenceItem` | metric + value + note |
| `CounterfactualRules` | Cooldown/max-trades/cap-size parameters |
| `CounterfactualRequest/Response` | What-if simulation I/O |
| `ReportRequest/Response` | Coaching report I/O |
| `NewsItem/NewsResponse` | News headline data |
| `ChatMessage/ChatRequest/ChatResponse` | Multi-turn chatbot I/O |
| `ShapWindowData` | Per-window SHAP values + predictions |
| `ShapExplainResponse` | Full SHAP explanation (all windows) |
| `TradeInsight` | Per-trade AI insight with market context |
| `TradeInsightsRequest/Response` | Trade insights I/O |

---

## 4. Frontend (Next.js / TypeScript)

### 4.1 App Shell & Routing

The frontend uses **Next.js 14 App Router** with a single-page architecture:

**`app/layout.tsx`** — Root layout:
- Sticky header with glassmorphism backdrop blur
- Gradient logo badge ("B" for BiasLens)
- Max-width 1400px container
- Inter font (sans-serif)

**`app/page.tsx`** — Main page with two states:

1. **Upload State** (`data === null`): Centered upload area with branding
2. **Dashboard State** (`data !== null`):
   - 7-column stat strip (Total Trades, PnL, Win Rate, Avg PnL, Best Trade, Worst Trade, Flagged)
   - 3 bias score cards
   - 5-tab interface: Insights → Timeline → What-If → Coaching → News

### 4.2 Components

#### `csv-upload.tsx` — File Upload
- **react-dropzone** for drag-and-drop
- Reads CSV headers, auto-detects column mapping using `FIELD_ALIASES` dictionary
- 4-column mapping grid with dropdowns for manual override
- Shows auto-detection success indicator
- Gradient "Analyze Trades" button

#### `bias-scorecards.tsx` — Score Display
- 4-column grid (calm + 3 biases, responsive to 1 on mobile)
- Each card: gradient background per bias type, emoji badge, score (0-100), severity label, progress bar, rationale
- Color coding: green (calm), orange (overtrading), red (loss aversion), purple (revenge trading)
- Progress bar: green (< 30), amber (30–50), red (> 50)
- **Expandable**: Click a card to expand it full-width and show the SHAP stacked bar chart for that bias class
- SHAP data is fetched once on first card click via `POST /api/shap-explain`, then cached in component state

#### `shap-stacked-chart.tsx` — SHAP Feature Visualization
- **Diverging stacked bar chart** (Recharts) showing per-window SHAP feature contributions
- Displays top 8 features by average absolute SHAP value + "Other" bucket for remaining features
- Bars above zero push the score **toward** the bias; bars below push **away**
- SHAP values are scaled to score space (0-100) so bar heights correspond to window scores
- X-axis shows window dates; custom tooltip shows per-feature SHAP breakdown
- 8 distinct feature colors + slate gray for "Other"

#### `insights-charts.tsx` — Time-Series Analysis
- **Time granularity selector**: 1 Min / 5 Min / 15 Min / 1 Hour / 1 Day
- **Auto-detects** best granularity from data time span
- 4-panel grid:
  1. **Trade Frequency** — Bar chart of trades per time bucket
  2. **Cumulative PnL** — Area chart with gradient fill
  3. **PnL per Period** — Bar chart with green/red coloring
  4. **Key Evidence** — Scrollable list of bias evidence metrics
- Uses **Recharts** (`BarChart`, `AreaChart`, `ResponsiveContainer`)
- Dynamic X-axis: adjusts label angle and interval based on data density

#### `trade-table.tsx` — Trade Log
- **TanStack Table** with global text filter, sortable columns
- Columns: Time, Side (buy/sell badges), Symbol, Qty, Price, PnL (colored), Biases (destructive badges)
- Flagged rows highlighted with red tint
- Monospace font for numeric values
- Max height 480px with sticky headers

#### `counterfactual-panel.tsx` — What-If Simulation
- 3 rule inputs: cooldown after loss (min), max trades/day, cap size multiplier
- "Run Counterfactual Simulation" button → calls `/api/counterfactual`
- Results: Summary card (original vs. counterfactual PnL, delta, kept/removed/modified counts)
- PnL comparison bar chart (red vs. green)
- Expandable trade-level detail table

#### `coaching-tab.tsx` — AI Coaching
- Empty state with icon and description
- "Generate Report" button → calls `/api/report` → Gemini
- Renders markdown report via `react-markdown`
- Numbered action plan with circle badges

#### `news-tab.tsx` — News Context
- Date picker + bias filter dropdown
- "Get Insights" button → calls `/api/news`
- Card-based headline list with source and publish time
- Links open in new tab

### 4.3 API Client

**`lib/api.ts`** — Thin fetch wrappers:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

analyzeCSV(file, mapping?, mode?)  → POST /api/analyze         (FormData)
fetchCounterfactual(trades, rules) → POST /api/counterfactual   (JSON)
fetchReport(payload)               → POST /api/report           (JSON)
fetchNews(date, bias, symbols?)    → GET  /api/news             (query params)
fetchShapExplain(trades)           → POST /api/shap-explain     (JSON)
fetchTradeInsights(payload)        → POST /api/trade-insights   (JSON)
sendChatMessage(messages, context) → POST /api/chat             (JSON)
```

### 4.4 Type Definitions

**`types/index.ts`** — TypeScript interfaces that mirror backend Pydantic schemas:

```
Trade, BiasScore, BiasFlag, EvidenceItem
AnalyzeResponse, CounterfactualRules, CounterfactualTrade, CounterfactualResponse
CoachingResponse, NewsItem, NewsResponse, ColumnMapping
ShapWindowData, ShapExplainResponse
TradeInsight, TradeInsightsResponse
```

### 4.5 Styling System

**CSS Variables** (`globals.css`):
- Light/dark theme via CSS custom properties
- Custom variables: `--success`, `--warning`, `--info`
- Custom scrollbar styling
- Utility classes: `.text-gradient`, `.glass`, `.animate-in`, `.animate-slide-up`
- Animations: `fadeIn` (opacity + translateY), `slideUp` (larger translateY)

**shadcn/ui Components** (`components/ui/`):
- `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`
- `Button` (with variants)
- `Badge` (default, destructive, secondary)
- `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` (Radix UI primitives)

---

## 5. Shared Module

**`shared/constants.py`**:
```python
BIAS_NAMES = ["Overtrading", "Loss Aversion", "Revenge Trading"]
DEFAULT_COOLDOWN_MINUTES = 30
DEFAULT_MAX_TRADES_PER_DAY = 20
DEFAULT_CAP_POSITION_SIZE = 1.0
```

**`shared/types.ts`** — Placeholder for shared TypeScript types.

**`shared/contracts/`** — Placeholder for API contract definitions (e.g., OpenAPI specs).

---

## 6. Machine Learning Deep-Dive

### 6.1 Feature Engineering (18 Features)

The feature pipeline (`backend/ml/features.py`) extracts 18 behavioral features from a window of trades:

| # | Feature | Category | Description |
|---|---------|----------|-------------|
| 1 | `trades_per_hour` | Frequency | Trade rate normalized by time span |
| 2 | `mean_time_between_trades_sec` | Frequency | Average inter-trade interval |
| 3 | `std_time_between_trades_sec` | Frequency | Variability of trade timing |
| 4 | `burst_count_60s` | Frequency | Trades within 60s of each other |
| 5 | `pnl_mean` | Performance | Average PnL per trade |
| 6 | `pnl_std` | Performance | PnL volatility |
| 7 | `pnl_total` | Performance | Total PnL in window |
| 8 | `win_rate` | Performance | Fraction of profitable trades |
| 9 | `avg_quantity` | Size | Mean position size |
| 10 | `std_quantity` | Size | Position size variability |
| 11 | `avg_trade_value` | Size | Mean quantity × price |
| 12 | `loss_hold_to_win_hold_ratio` | Loss Aversion | Proxy hold time ratio (loser/winner) |
| 13 | `avg_size_after_loss_ratio` | Revenge | Position size change after losses |
| 14 | `reentry_after_loss_mean_sec` | Revenge | Average time to re-enter after a loss |
| 15 | `consecutive_loss_streak_max` | Behavior | Longest consecutive loss streak |
| 16 | `side_switch_rate` | Behavior | How often trader flips buy/sell |
| 17 | `unique_symbols` | Diversity | Number of distinct instruments traded |
| 18 | `balance_drawdown_pct` | Risk | Maximum balance drawdown percentage |

**Windowing**: `extract_windowed_features(df, window_size=50, stride=25)` slides a window over the trade log, producing one feature vector per window.

### 6.2 Training Pipeline

**`backend/ml/train_xgboost.py`** — Standalone training script:

```bash
python -m backend.ml.train_xgboost [--window-size 50] [--stride 25] [--folds 5]
```

**Training data** (`trading_datasets/`):

| File | Label | Trades | Description |
|------|-------|--------|-------------|
| `calm_trader.csv` | calm | 10,000 | Normal trading behavior |
| `overtrader.csv` | overtrading | 10,000 | High frequency, burst patterns |
| `loss_averse_trader.csv` | loss_aversion | 10,000 | Extended hold on losers |
| `revenge_trader.csv` | revenge_trading | 10,000 | Rapid larger re-entries after losses |

**Process:**
1. Load all 4 CSVs
2. Extract windowed features (window=50, stride=25) → ~1,560 total samples
3. Train XGBoost multi-class classifier
4. 5-fold stratified cross-validation
5. Save model to `saved_models/bias_xgb.joblib`
6. Save report to `saved_models/training_report.json`

### 6.3 Model Architecture & Performance

**XGBoost Configuration:**
```python
XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    objective="multi:softprob",
    num_class=4,
    eval_metric="mlogloss",
)
```

**Performance:**
- **5-fold CV Accuracy**: 83.5% ± ~2%
- **4 classes**: calm, overtrading, loss_aversion, revenge_trading
- Custom attribute `model.bias_classes_` stored on the saved model for label decoding

**Inference** (`backend/ml/model.py`):
- `BiasMLClassifier` loads the joblib model at initialization
- `predict_bias_probabilities(feature_vector)` → `{class: probability}`
- **Fallback**: When no model file exists, uses heuristic probability formulas

---

## 7. Bias Detection Algorithms

### 7.1 Overtrading Detector

```
Input: DataFrame with timestamp column
  │
  ├── Group by date → trades_per_day series
  │   └── avg_trades_per_day, max_trades_per_day
  │
  ├── Rolling 10-min window → burst_count per trade
  │   └── max_burst_trades
  │
  ├── Score = clip((0.6 × day_ratio + 0.4 × burst_ratio) × 50, 0, 100)
  │   where day_ratio = min(avg_trades_per_day / 15, 2.0)
  │         burst_ratio = min(max_burst / 5, 2.0)
  │
  └── Flag trades on high-activity days OR in burst windows
```

### 7.2 Loss Aversion Detector

```
Input: DataFrame with pnl and hold_minutes columns
  │
  ├── Split into winners (pnl > 0) and losers (pnl < 0)
  │
  ├── avg_winner_hold = mean(winners.hold_minutes)
  ├── avg_loser_hold  = mean(losers.hold_minutes)
  ├── hold_ratio      = avg_loser_hold / avg_winner_hold
  │
  ├── Score = clip((hold_ratio - 1.0) × 60, 0, 100)
  │
  └── Flag losing trades held > 1.5× avg_winner_hold
```

### 7.3 Revenge Trading Detector

```
Input: DataFrame sorted by timestamp
  │
  ├── For each losing trade:
  │   ├── Look at next 5 trades within 15-min window
  │   ├── Find entries with quantity ≥ 1.25× the loss trade's quantity
  │   └── If found → count as revenge event, flag the re-entry trade
  │
  ├── event_rate = revenge_events / total_trades
  ├── Score = clip(event_rate × 400, 0, 100)
  │
  └── Flag identified revenge re-entry trades
```

### 7.4 Score Fusion (Heuristic + ML)

The fusion strategy depends on the `analysis_mode` parameter:

```
rules_only:  final_score = heuristic_score
ml_only:     final_score = ml_probability × 100
mixed:       final_score = 0.6 × heuristic_score + 0.4 × (ml_probability × 100)
```

**Per-trade flagging** also varies by mode:
- `rules_only`: Only trades flagged by heuristic detectors
- `ml_only`: Trades where averaged window ML probability ≥ 0.3 for a bias class
- `mixed`: **Intersection** — only trades flagged by both heuristics AND ML (high precision)

**Calm score**: Computed as `100 - max_bias_score`, blended with ML calm probability in mixed/ml_only modes using the same 60/40 ratio.

---

## 8. Data Flow

### Upload → Analysis Flow

```
                        CSV File (user upload)
                              │
                    ┌─────────▼──────────┐
                    │  Frontend: CSVUpload │
                    │  - Parse headers     │
                    │  - Auto-detect cols  │
                    │  - Build FormData    │
                    └─────────┬──────────┘
                              │ POST /api/analyze
                    ┌─────────▼──────────┐
                    │  Backend: analyze.py │
                    │  - Parse mapping     │
                    │  - csv_to_dataframe  │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────────┐
                    │  data_loader.py          │
                    │  - Auto-detect columns   │
                    │  - Rename → standard     │
                    │  - Coerce types          │
                    │  - Infer hold_minutes    │
                    └─────────┬──────────────┘
                              │ Clean DataFrame
                    ┌─────────▼──────────────┐
                    │  analysis_engine.py      │
                    │  - Run 3 detectors       │
                    │  - (Optional) ML predict │
                    │  - Fuse scores           │
                    │  - Aggregate flags       │
                    │  - Compute stats         │
                    └─────────┬──────────────┘
                              │ AnalyzeResponse JSON
                    ┌─────────▼──────────────┐
                    │  Frontend: page.tsx      │
                    │  - setData(response)     │
                    │  - Render dashboard      │
                    │  - Compute client stats  │
                    │  - Display charts/table  │
                    └────────────────────────┘
```

### Counterfactual Simulation Flow

```
Normalized trades + Rules
         │
         ▼
  Replay trade sequence chronologically
         │
         ├── Rule 1: max_trades_per_day exceeded? → REMOVE trade
         ├── Rule 2: within cooldown after loss?  → REMOVE trade
         └── Rule 3: position size > cap?         → MODIFY (scale PnL)
         │
         ▼
  Compare original_pnl vs counterfactual_pnl
  Return per-trade status (kept/removed/modified)
```

---

## 9. Infrastructure & DevOps

### 9.1 Docker

**Backend Dockerfile** (`backend/Dockerfile`):
- Base: `python:3.11-slim`
- Installs `requirements.txt`
- Copies `backend/` and `shared/`
- Runs: `uvicorn main:app --host 0.0.0.0 --port 8000`

**Frontend Dockerfile** (`frontend/Dockerfile`):
- Multi-stage build (deps → builder → runner)
- Base: `node:20-alpine`
- Stage 1: `npm ci` for dependencies
- Stage 2: `npm run build` for production build
- Stage 3: Minimal runner with non-root `nextjs` user
- Runs: `node server.js` on port 3000

**docker-compose.yml**:
```yaml
services:
  backend:   port 8000, reads .env, hot-reloads backend/ volume
  frontend:  port 3000, sets NEXT_PUBLIC_API_URL, depends_on backend
```

### 9.2 Modal (Cloud Deployment)

**`modal_app.py`** — Serverless deployment of the FastAPI backend on [Modal](https://modal.com):

```python
app = modal.App("biaslens-backend")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("fastapi", "pydantic", "pandas", "xgboost", "shap", ...)
    .add_local_dir("backend", remote_path="/root/backend")
    .add_local_dir("shared", remote_path="/root/shared")
)

@app.function(image=image, secrets=[modal.Secret.from_name("biaslens-secrets")],
              cpu=4.0, memory=8192, timeout=300, scaledown_window=120)
@modal.concurrent(max_inputs=10)
@modal.asgi_app()
def serve():
    from backend.main import app as fastapi_app
    return fastapi_app
```

**Key configuration:**

| Setting | Value | Description |
|---------|-------|-------------|
| CPU | 4 cores | Enough for XGBoost + SHAP computation |
| Memory | 8 GB | Accommodates model + SHAP in-memory |
| Timeout | 300s | Max request duration |
| Scaledown window | 120s | Keep warm for 2 min after last request |
| Max concurrent inputs | 10 | Parallel requests per container |
| Secrets | `biaslens-secrets` | Modal secret group (GEMINI_API_KEY, etc.) |

**Deploy:**
```bash
modal deploy modal_app.py        # Production deployment
modal serve modal_app.py         # Dev mode with hot-reload
```

The frontend (Next.js) can be deployed to **Vercel** or any static hosting, with `NEXT_PUBLIC_API_URL` pointing to the Modal endpoint URL.

### 9.3 CI/CD

**GitHub Actions** (`.github/workflows/ci.yml`):

```
Triggers: push/PR to main

Jobs:
  backend:
    - Python 3.11
    - pip install requirements + pytest
    - pytest tests/ -v

  frontend:
    - Node 20
    - npm ci
    - npm run lint (non-blocking)
    - npm run build
```

### 9.4 Environment Variables

Copy `.env.example` → `.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | For coaching/news | Google AI Studio API key |
| `NEWS_API_KEY` | For news tab | newsapi.org API key |
| `NEXT_PUBLIC_API_URL` | For Docker | Backend URL (default: `http://localhost:8000`) |

---

## 10. API Reference

### `POST /api/analyze`

Analyze a trading log for behavioral biases.

**Multipart Form:**
| Field | Type | Description |
|-------|------|-------------|
| `file` | File | CSV file upload |
| `mapping` | string (JSON) | Optional column mapping override |

**JSON Body Alternative:**
```json
{
  "csv_content": "timestamp,side,...",
  "trades": [{ "timestamp": "...", "side": "buy", ... }],
  "mapping": { "timestamp": "time", "symbol": "asset" },
  "use_ml": false
}
```

**Response** (`AnalyzeResponse`):
```json
{
  "bias_scores": {
    "overtrading": { "score": 78.5, "severity": "high", "rationale": "..." },
    "loss_aversion": { "score": 61.3, "severity": "medium", "rationale": "..." },
    "revenge_trading": { "score": 55.0, "severity": "medium", "rationale": "..." }
  },
  "flagged_trades": [
    { "trade_index": 42, "timestamp": "...", "symbol": "BTCUSD", "pnl": -520.0, "tags": ["revenge_trading"], "reason": "..." }
  ],
  "bias_evidence": { "overtrading": [{ "metric": "...", "value": 26.4, "note": "..." }] },
  "feature_stats": { "trade_count": 350, "pnl_total": 2410.5, ... },
  "normalized_trades": [{ "timestamp": "...", "side": "buy", "symbol": "BTCUSD", ... }]
}
```

### `POST /api/counterfactual`

Simulate trading with behavioral rules applied.

**Request:**
```json
{
  "trades": [{ "timestamp": "...", "side": "buy", "symbol": "...", "price": 100, "quantity": 10, "pnl": -50 }],
  "rules": {
    "cooldown_minutes_after_loss": 30,
    "max_trades_per_day": 20,
    "cap_size_after_loss": 1.0
  }
}
```

**Response:**
```json
{
  "original_pnl": -1200.50,
  "counterfactual_pnl": -340.20,
  "pnl_delta": 860.30,
  "kept_trades": 280,
  "removed_trades": 45,
  "modified_trades": 25,
  "modified_trade_list": [{ "trade_index": 5, "status": "removed", "reason": "Within 30-min cooldown..." }]
}
```

### `POST /api/report`

Generate an AI coaching report.

**Request:**
```json
{
  "analysis": { "bias_scores": {...}, "feature_stats": {...}, "flagged_count": 45 },
  "include_headlines": true
}
```

**Response:**
```json
{
  "report_markdown": "# Trading Behavior Report\n...",
  "coaching_plan": ["Day 1-2: Review flagged trades...", "Day 3-4: Set max trade limits..."]
}
```

### `GET /api/news?date=2025-03-01&bias=Overtrading`

Fetch market news context for a trading day.

**Response:**
```json
{
  "date": "2025-03-01",
  "headlines": [
    { "title": "Fed raises rates...", "source": "Reuters", "published_at": "2025-03-01T14:30:00Z", "url": "https://..." }
  ]
}
```

### `POST /api/chat`

Multi-turn AI chatbot about the user's analysis.

**Request:**
```json
{
  "messages": [
    { "role": "user", "text": "Why was trade #42 flagged?" },
    { "role": "model", "text": "Trade #42 was flagged because..." },
    { "role": "user", "text": "How can I avoid this pattern?" }
  ],
  "analysis_context": {
    "bias_scores": {...},
    "flagged_trades": [...],
    "feature_stats": {...},
    "normalized_trades": [...]
  }
}
```

**Response:**
```json
{
  "reply": "To avoid revenge trading patterns, consider implementing a mandatory cooldown..."
}
```

### `POST /api/shap-explain`

Compute SHAP feature explanations for bias predictions.

**Request:**
```json
{
  "trades": [{ "timestamp": "...", "side": "buy", "symbol": "BTCUSD", "price": 100, "quantity": 10, "pnl": -50 }],
  "mapping": { "timestamp": "timestamp", "side": "side" }
}
```

**Response:**
```json
{
  "feature_names": ["trades_per_hour", "mean_time_between_trades_sec", ...],
  "classes": ["calm", "loss_aversion", "overtrading", "revenge_trading"],
  "n_windows": 3,
  "base_values": { "calm": 0.25, "overtrading": 0.25, ... },
  "windows": [
    {
      "window_index": 0,
      "trade_range": [0, 50],
      "feature_values": [12.5, 288.0, ...],
      "predictions": { "calm": 0.1, "overtrading": 0.6, ... },
      "shap_values": { "calm": [0.01, -0.03, ...], "overtrading": [0.15, 0.08, ...] }
    }
  ]
}
```

### `POST /api/trade-insights`

Generate per-flagged-trade AI insights with market news context.

**Request:**
```json
{
  "flagged_trades": [{ "trade_index": 42, "timestamp": "...", "symbol": "BTCUSD", "pnl": -520, "tags": ["revenge_trading"], "reason": "..." }],
  "bias_scores": { "overtrading": { "score": 78.5, "severity": "high", "rationale": "..." } },
  "normalized_trades": [...],
  "symbols": ["BTCUSD"],
  "date_range": ["2025-01-01", "2025-03-31"]
}
```

**Response:**
```json
{
  "insights": [
    {
      "trade_index": 42,
      "timestamp": "...",
      "symbol": "BTCUSD",
      "side": "buy",
      "pnl": -520,
      "tags": ["revenge_trading"],
      "reason": "...",
      "market_context": "BTC was experiencing high volatility following Fed announcement...",
      "gemini_explanation": "This trade shows classic revenge trading behavior...",
      "related_headlines": ["Fed raises rates...", "Bitcoin drops 5%..."]
    }
  ],
  "summary": "Analyzed 1 flagged trade(s) across 1 symbol(s). Detected bias patterns: revenge_trading.",
  "market_context": "Fed raises rates; Bitcoin drops 5%..."
}
```

### `GET /health`

Health check. Returns `{ "status": "ok" }`.

---

## 11. Testing

### Backend Tests

**`backend/tests/test_detectors.py`** — 6 unit tests:

| Test | What it validates |
|------|-------------------|
| `test_overtrading_empty` | Empty DataFrame → score 0, no flags |
| `test_overtrading_basic` | Synthetic high-frequency data → score > 0, flags present |
| `test_loss_aversion_empty` | Empty DataFrame → score 0 |
| `test_loss_aversion_basic` | Losers held 3× longer → high score |
| `test_revenge_trading_empty` | Empty DataFrame → score 0 |
| `test_revenge_trading_basic` | Rapid larger re-entry → events detected |

Run tests:
```bash
cd backend && python -m pytest tests/ -v
```

### Frontend Verification

```bash
cd frontend && npm run build  # TypeScript type checking + build
cd frontend && npm run lint   # ESLint
```

---

## 12. Getting Started

### Prerequisites

- Python 3.11+ with pip
- Node.js 20+ with npm
- (Optional) Docker & docker-compose
- (Optional) Gemini API key, NewsAPI key

### Local Development

```bash
# 1. Clone
git clone https://github.com/AlpinSchool/QHacks_2026.git
cd QHacks_2026

# 2. Backend
cp .env.example .env
# Edit .env with your API keys
pip install -r requirements.txt
uvicorn backend.main:app --reload  # http://localhost:8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev  # http://localhost:3000

# 4. (Optional) Train ML model
python -m backend.ml.train_xgboost

# 5. (Optional) Run tests
cd backend && python -m pytest tests/ -v
cd frontend && npm run build
```

### Docker

```bash
cp .env.example .env
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

### Modal (Cloud)

```bash
# 1. Install Modal CLI
pip install modal
modal setup  # Authenticate with Modal

# 2. Create secrets in Modal dashboard (or CLI)
modal secret create biaslens-secrets GEMINI_API_KEY=your-key NEWS_API_KEY=your-key

# 3. Deploy backend
modal deploy modal_app.py
# → Prints a public URL like https://your-workspace--biaslens-backend-serve.modal.run

# 4. Point frontend to Modal backend
NEXT_PUBLIC_API_URL=https://your-workspace--biaslens-backend-serve.modal.run npm run build
```

### Usage

1. Open http://localhost:3000
2. Upload a CSV with columns: `timestamp, side, symbol, quantity, price` (and optionally `pnl`, `hold_minutes`)
3. Column auto-detection handles common aliases (`asset` → `symbol`, `entry_price` → `price`, etc.)
4. View bias scores, explore insights charts (adjust time granularity), browse flagged trades
5. Run What-If simulations to see impact of behavioral rules
6. Generate AI coaching report (requires Gemini API key)
7. Look up market news context for specific trading days (requires NewsAPI key)
