"use client";

import { useState, useMemo } from "react";
import type { AnalyzeResponse, NewsResponse, NewsItem } from "@/types";
import { fetchNews } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  analysisData?: AnalyzeResponse | null;
}

export default function NewsTab({ analysisData }: Props) {
  const [result, setResult] = useState<NewsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [manualDate, setManualDate] = useState("");
  const [bias, setBias] = useState("");

  // Auto-extract symbols and date range from trade data
  const tradeContext = useMemo(() => {
    if (!analysisData?.normalized_trades?.length) return null;
    const trades = analysisData.normalized_trades;
    const symbols = [...new Set(trades.map((t) => String(t.symbol || "").toUpperCase()).filter(Boolean))];
    const timestamps = trades
      .map((t) => t.timestamp as string)
      .filter(Boolean)
      .sort();
    const dateFrom = timestamps[0]?.slice(0, 10) || "";
    const dateTo = timestamps[timestamps.length - 1]?.slice(0, 10) || dateFrom;
    return { symbols, dateFrom, dateTo };
  }, [analysisData]);

  const search = async () => {
    setLoading(true);
    try {
      const date = tradeContext?.dateFrom || manualDate;
      const dateTo = tradeContext?.dateTo;
      const symbols = tradeContext?.symbols;
      if (!date) return;

      const res = await fetchNews(date, bias, symbols, dateTo);
      if (res.ok) {
        const data: NewsResponse = await res.json();
        setResult(data);
      }
    } finally {
      setLoading(false);
    }
  };

  // Group headlines by symbol
  const groupedHeadlines = useMemo(() => {
    if (!result?.headlines) return {};
    const groups: Record<string, NewsItem[]> = {};
    for (const item of result.headlines) {
      const key = item.symbol || "MARKET";
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    }
    return groups;
  }, [result]);

  const symbolCount = tradeContext?.symbols?.length || 0;

  return (
    <Card className="border-0 shadow-md">
      <CardHeader className="pb-3 pt-4 px-4">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          📰 Market News &amp; Context
          {tradeContext && (
            <span className="text-[10px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
              {symbolCount} ticker{symbolCount !== 1 ? "s" : ""} detected
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 px-4 pb-4">
        {/* Controls */}
        <div className="flex gap-2 items-end flex-wrap">
          {tradeContext ? (
            <div className="flex items-center gap-3 flex-wrap">
              <div className="space-y-1">
                <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                  Symbols
                </label>
                <div className="flex gap-1 flex-wrap">
                  {tradeContext.symbols.slice(0, 8).map((s) => (
                    <span
                      key={s}
                      className="text-[11px] px-2 py-0.5 rounded-md bg-violet-100 text-violet-700 font-mono font-medium"
                    >
                      {s}
                    </span>
                  ))}
                  {tradeContext.symbols.length > 8 && (
                    <span className="text-[11px] px-2 py-0.5 rounded-md bg-muted text-muted-foreground">
                      +{tradeContext.symbols.length - 8} more
                    </span>
                  )}
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                  Date Range
                </label>
                <p className="text-xs text-foreground font-mono">
                  {tradeContext.dateFrom} → {tradeContext.dateTo}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground">
                Date
              </label>
              <input
                type="date"
                value={manualDate}
                onChange={(e) => setManualDate(e.target.value)}
                className="border border-border/50 rounded-lg px-3 py-1.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring/20 transition-all"
              />
            </div>
          )}
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-muted-foreground">
              Bias Filter
            </label>
            <select
              value={bias}
              onChange={(e) => setBias(e.target.value)}
              className="border border-border/50 rounded-lg px-3 py-1.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring/20 transition-all"
            >
              <option value="">All biases</option>
              <option value="Overtrading">Overtrading</option>
              <option value="Loss Aversion">Loss Aversion</option>
              <option value="Revenge Trading">Revenge Trading</option>
            </select>
          </div>
          <Button
            onClick={search}
            disabled={loading || (!tradeContext?.dateFrom && !manualDate)}
            size="sm"
            className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium px-6"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin">⏳</span> Fetching…
              </span>
            ) : (
              "🔍 Fetch News"
            )}
          </Button>
        </div>

        {/* Gemini Market Context */}
        {result?.context && (
          <div className="animate-slide-up rounded-xl bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/50 p-4">
            <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-blue-100 flex items-center justify-center text-xs">🤖</span>
              AI Market Context
            </h4>
            <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
              {result.context}
            </p>
          </div>
        )}

        {/* Grouped Headlines */}
        {result && Object.keys(groupedHeadlines).length > 0 && (
          <div className="animate-slide-up space-y-4">
            {Object.entries(groupedHeadlines).map(([symbol, items]) => (
              <div key={symbol}>
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={`text-[11px] px-2 py-0.5 rounded-md font-mono font-semibold ${
                      symbol === "MARKET"
                        ? "bg-gray-100 text-gray-600"
                        : "bg-violet-100 text-violet-700"
                    }`}
                  >
                    {symbol}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {items.length} headline{items.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="space-y-1.5 ml-1">
                  {items.map((item: NewsItem, i: number) => {
                    const hasValidUrl =
                      item.url &&
                      item.url.startsWith("https://") &&
                      !item.url.includes("vertexaisearch") &&
                      !item.url.includes("localhost");
                    return (
                      <div
                        key={i}
                        className="p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors border border-transparent hover:border-border/30"
                      >
                        {hasValidUrl ? (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-medium text-sm hover:text-blue-600 hover:underline transition-colors leading-snug"
                          >
                            {item.title}
                          </a>
                        ) : (
                          <p className="font-medium text-sm leading-snug">
                            {item.title}
                          </p>
                        )}
                        <p className="text-[11px] text-muted-foreground mt-1">
                          {item.source}
                          {item.published_at &&
                            ` · ${item.published_at.slice(0, 10)}`}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!result && (
          <div className="text-center py-6">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-100 to-indigo-100 flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl">📰</span>
            </div>
            <p className="text-sm text-muted-foreground max-w-sm mx-auto">
              {tradeContext
                ? `Fetch market news for your ${symbolCount} traded symbol${symbolCount !== 1 ? "s" : ""} to understand what drove your trading decisions.`
                : "Select a date to find relevant market news and context."}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
