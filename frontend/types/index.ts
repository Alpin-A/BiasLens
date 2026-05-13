// ─── BiasLens frontend types (aligned with backend schemas) ───

export interface Trade {
  timestamp: string;
  side: string;
  symbol: string;
  quantity: number;
  price: number;
  pnl: number;
  hold_minutes?: number | null;
}

export interface EvidenceItem {
  metric: string;
  value: number | string;
  note: string;
}

export interface BiasScore {
  score: number;
  severity: "low" | "medium" | "high";
  rationale: string;
}

export interface BiasFlag {
  trade_index: number;
  timestamp: string;
  symbol: string;
  pnl: number;
  tags: string[];
  reason: string;
}

export interface AnalyzeResponse {
  bias_scores: Record<string, BiasScore>;
  flagged_trades: BiasFlag[];
  bias_evidence: Record<string, EvidenceItem[]>;
  feature_stats: Record<string, any>;
  normalized_trades: Record<string, any>[];
}

export interface CounterfactualRules {
  cooldown_minutes_after_loss: number;
  max_trades_per_day: number;
  cap_size_after_loss: number;
}

export interface CounterfactualTrade {
  trade_index: number;
  timestamp: string;
  symbol: string;
  side: string;
  quantity: number;
  pnl: number;
  status: "kept" | "removed" | "modified";
  reason: string | null;
}

export interface CounterfactualResponse {
  original_pnl: number;
  counterfactual_pnl: number;
  pnl_delta: number;
  kept_trades: number;
  removed_trades: number;
  modified_trades: number;
  modified_trade_list: CounterfactualTrade[];
}

export interface CoachingResponse {
  report_markdown: string;
  coaching_plan: string[];
}

export interface NewsItem {
  title: string;
  source: string;
  published_at: string;
  url: string;
  symbol?: string | null;
}

export interface NewsResponse {
  date: string;
  headlines: NewsItem[];
  context?: string | null;
  symbols?: string[];
}

export interface TradeInsight {
  trade_index: number;
  timestamp: string;
  symbol: string;
  side: string;
  pnl: number;
  tags: string[];
  reason: string;
  market_context: string;
  gemini_explanation: string;
  related_headlines: string[];
}

export interface TradeInsightsResponse {
  insights: TradeInsight[];
  summary: string;
  market_context: string;
}

export interface ColumnMapping {
  timestamp: string;
  side: string;
  symbol: string;
  quantity: string;
  price: string;
  pnl: string;
  hold_minutes?: string;
}

// ─── SHAP Explainability types ───

export interface ShapWindowData {
  window_index: number;
  trade_range: [number, number];
  feature_values: number[];
  predictions: Record<string, number>;
  shap_values: Record<string, number[]>;
}

export interface ShapExplainResponse {
  feature_names: string[];
  classes: string[];
  n_windows: number;
  base_values: Record<string, number>;
  windows: ShapWindowData[];
}

// ─── Chat types ───

export interface ChatMessage {
  role: "user" | "model";
  text: string;
}

export interface ChatResponse {
  reply: string;
}
