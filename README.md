# BiasLens

A tool for detecting cognitive biases in trading histories. Upload a trade log as a CSV, get quantified scores for overtrading, loss aversion, and revenge trading, visualize the patterns, simulate what your P&L would look like without the biased trades, and get an AI-generated coaching report.

> 🏆 1st Place — National Bank of Canada Bias Detection Challenge, QHacks 2026

## What it does

Upload a CSV of trades. BiasLens runs three rule-based detectors and an XGBoost classifier over the trade history and produces:

- **Bias scores (0–100)** for overtrading, loss aversion, revenge trading, and a composite discipline score
- **Per-trade flagging** — each trade labeled with the biases it triggered
- **Counterfactual simulator** — remove flagged trades and see the adjusted P&L
- **Coaching report** — Gemini-generated behavioral analysis with a 7-day action plan
- **News context** — Google Search-grounded headlines from the trading period to explain potential emotional triggers

Three analysis modes let you choose how much weight to give the rule engine vs. the ML model:

| Mode | Scoring |
|------|---------|
| Rules Only | 100% hand-tuned detectors |
| Mixed (default) | 60% rules + 40% XGBoost |
| ML Only | 100% XGBoost predictions |

## Tech stack

**Backend:** Python, FastAPI, Pandas, XGBoost, SHAP, Google Gemini 2.5 Flash  
**Frontend:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Recharts  
**ML:** XGBoost 4-class classifier (calm / overtrading / loss_aversion / revenge_trading)

## Running locally

**Prerequisites:** Python 3.11+, Node.js 18+, a [Gemini API key](https://aistudio.google.com/)

```bash
git clone https://github.com/Alpin-A/BIasLens.git
cd BiasLens

cp .env.example .env
# edit .env and set GEMINI_API_KEY=your_key_here

# backend
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000

# frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Use `synthetic_trades.csv` in the repo root to try it immediately.

## CSV format

Required columns — common broker export aliases are auto-detected:

| Column | Accepted aliases |
|--------|-----------------|
| `timestamp` | time, date, datetime, executed_at |
| `side` | direction, type, action, buy_sell |
| `symbol` | asset, ticker, instrument, stock |
| `quantity` | qty, size, amount, volume, shares |
| `price` | entry_price, exec_price, fill_price |
| `pnl` | profit_loss, profit, realized_pnl, gain |

`hold_minutes` is optional but improves loss aversion detection accuracy. If absent, hold time is inferred from the gap between consecutive trades on the same symbol.

## How the bias detection works

**Overtrading** — measures trades/day against a threshold, burst trades within 60-second windows, and rapid buy↔sell flips on the same symbol within 5 minutes. Score = 45% frequency + 30% bursts + 25% switching.

**Loss aversion** — measures the ratio of how long losing trades are held vs. winning trades, and whether average losses exceed average wins in size. Score = 50% hold-time ratio + 50% size ratio.

**Revenge trading** — detects re-entries within 15 minutes of a loss with position size ≥1.25×, and size increases following 2+ consecutive losses.

**XGBoost model** — trained on four synthetic datasets (10K trades each) built to encode each bias pattern. Features include trading frequency, burst counts, PnL distribution, hold-time proxies, size-after-loss ratios, and balance drawdown. Prediction windows are 50 trades with stride 25, and probabilities are averaged across all windows.

In **mixed mode**, per-trade flagging uses intersection logic — a trade is only tagged if both the rule engine and the ML model agree. This reduces false positives at the cost of some recall.

## Notable implementation details

**Rate limiting** — Gemini calls are serialized through a global lock with a minimum 4-second gap between requests, keeping usage within free-tier RPM limits without requiring the caller to manage backoff.

**Column mapping** — The CSV loader tries the user-provided mapping first, then falls back to alias matching across 40+ common broker export column names. The upload form also lets users manually remap columns before submitting.

**Passthrough columns** — `entry_price`, `exit_price`, and `balance` are preserved through the pipeline even when they get renamed during column normalization, so downstream ML features that need them still work.

**SHAP explainability** — the `/api/shap-explain` endpoint runs a SHAP TreeExplainer over the XGBoost model and returns per-window feature attributions, which the frontend renders as a stacked bar chart.

## Retrain the model

```bash
python -m backend.ml.train_xgboost
```

Saves to `backend/ml/saved_models/bias_xgb.joblib`. The four synthetic datasets in `trading_datasets/` are used for training.

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | POST | Upload CSV → bias detection + ML scoring |
| `/api/counterfactual` | POST | Simulate removing biased trades |
| `/api/report` | POST | Generate Gemini coaching report |
| `/api/news` | GET | Fetch headlines + Gemini context |
| `/api/trade-insights` | POST | Per-trade Gemini analysis |
| `/api/chat` | POST | Multi-turn chat with analysis context |
| `/api/shap-explain` | POST | SHAP feature attributions for ML predictions |
| `/health` | GET | Health check |

## Project structure

```
backend/
  api/                  FastAPI route handlers
  core/                 Analysis engine + Pydantic schemas
  detectors/            Rule-based bias detectors
  ml/                   XGBoost model, feature extraction, training scripts
  llm/                  Gemini client + prompts
  utils/                CSV loading, column mapping, config
  tests/                Unit tests for detectors
frontend/
  app/                  Next.js App Router pages
  components/           UI components (charts, tables, panels)
  lib/                  API client, utilities
  types/                TypeScript interfaces
shared/                 Cross-stack constants
synthetic_datasets/     Scripts used to generate the training data
trading_datasets/       Sample datasets for testing
```

## Running tests

```bash
python -m pytest backend/tests/ -v
```

## License

MIT
