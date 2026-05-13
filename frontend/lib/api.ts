const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type AnalysisMode = "rules_only" | "ml_only" | "mixed";

export async function analyzeCSV(
  file: File,
  mapping?: Record<string, string>,
  analysisMode: AnalysisMode = "mixed"
): Promise<Response> {
  const formData = new FormData();
  formData.append("file", file);
  if (mapping) {
    formData.append("mapping", JSON.stringify(mapping));
  }
  formData.append("analysis_mode", analysisMode);
  return fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: formData,
  });
}

export async function fetchCounterfactual(
  trades: any[],
  rules: any
): Promise<Response> {
  return fetch(`${API_BASE}/api/counterfactual`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trades, rules }),
  });
}

export async function fetchReport(payload: any): Promise<Response> {
  return fetch(`${API_BASE}/api/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function fetchNews(
  date: string,
  bias: string,
  symbols?: string[],
  dateTo?: string
): Promise<Response> {
  const params = new URLSearchParams({ date, bias });
  if (symbols && symbols.length > 0) {
    params.set("symbols", symbols.join(","));
  }
  if (dateTo) {
    params.set("date_to", dateTo);
  }
  return fetch(`${API_BASE}/api/news?${params}`);
}

export async function fetchTradeInsights(payload: {
  flagged_trades: any[];
  bias_scores: Record<string, any>;
  normalized_trades: any[];
  symbols?: string[];
  date_range?: string[];
}): Promise<Response> {
  return fetch(`${API_BASE}/api/trade-insights`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function fetchShapExplain(
  trades: any[]
): Promise<Response> {
  return fetch(`${API_BASE}/api/shap-explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trades }),
  });
}

export async function sendChatMessage(
  messages: { role: string; text: string }[],
  analysisContext: Record<string, any>
): Promise<Response> {
  return fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      analysis_context: analysisContext,
    }),
  });
}
