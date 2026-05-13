"use client";

import { useState } from "react";
import type {
  AnalyzeResponse,
  CounterfactualResponse,
  CoachingResponse,
  TradeInsightsResponse,
  TradeInsight,
} from "@/types";
import { fetchReport, fetchTradeInsights } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import ReactMarkdown from "react-markdown";
import { formatCurrency } from "@/lib/utils";

interface Props {
  analysisData: AnalyzeResponse;
  counterfactual: CounterfactualResponse | null;
}

function TradeAccordion({
  insight,
  biasTagColor,
}: {
  insight: TradeInsight;
  biasTagColor: Record<string, string>;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-xl border border-border/50 overflow-hidden transition-all hover:border-border">
      {/* Clickable header */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span
            className={`flex-shrink-0 w-5 h-5 rounded-md text-[10px] font-bold flex items-center justify-center transition-transform ${
              open ? "rotate-90" : ""
            } bg-muted text-muted-foreground`}
          >
            ▶
          </span>
          <span className="text-xs font-mono font-semibold bg-violet-100 text-violet-700 px-2 py-0.5 rounded-md flex-shrink-0">
            {insight.symbol}
          </span>
          <span
            className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded flex-shrink-0 ${
              insight.side === "buy"
                ? "bg-emerald-100 text-emerald-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {insight.side}
          </span>
          <span className="text-[11px] text-muted-foreground flex-shrink-0">
            #{insight.trade_index}
          </span>
          {/* Bias tags inline */}
          <div className="flex gap-1 flex-shrink-0">
            {insight.tags.map((tag) => (
              <span
                key={tag}
                className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${
                  biasTagColor[tag] || "bg-gray-100 text-gray-600"
                }`}
              >
                {tag.replace("_", " ")}
              </span>
            ))}
          </div>
        </div>
        <span
          className={`text-sm font-mono font-semibold flex-shrink-0 ${
            insight.pnl >= 0 ? "text-emerald-600" : "text-red-500"
          }`}
        >
          {formatCurrency(insight.pnl)}
        </span>
      </button>

      {/* Expandable body */}
      {open && (
        <div className="px-4 pb-4 pt-1 space-y-3 border-t border-border/30 animate-slide-up">
          {/* Flag reason */}
          <div className="p-2.5 rounded-lg bg-amber-50/50 border border-amber-100/50">
            <p className="text-[11px] font-medium text-amber-700 mb-0.5">
              ⚠️ Flag Reason
            </p>
            <p className="text-xs text-muted-foreground">{insight.reason}</p>
          </div>

          {/* AI Explanation */}
          {insight.gemini_explanation && (
            <div className="p-2.5 rounded-lg bg-blue-50/50 border border-blue-100/50">
              <p className="text-[11px] font-medium text-blue-700 mb-0.5">
                🤖 AI Analysis
              </p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {insight.gemini_explanation}
              </p>
            </div>
          )}

          {/* Market Context */}
          {insight.market_context && (
            <div className="p-2.5 rounded-lg bg-gray-50/50 border border-gray-100/50">
              <p className="text-[11px] font-medium text-gray-600 mb-0.5">
                📊 Market Context
              </p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {insight.market_context}
              </p>
              {insight.related_headlines.length > 0 && (
                <div className="mt-2 space-y-1">
                  {insight.related_headlines.map((h, hi) => (
                    <p
                      key={hi}
                      className="text-[10px] text-muted-foreground pl-2 border-l-2 border-blue-200"
                    >
                      {h}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function CoachingTab({ analysisData, counterfactual }: Props) {
  const [report, setReport] = useState<CoachingResponse | null>(null);
  const [tradeInsights, setTradeInsights] =
    useState<TradeInsightsResponse | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [loadingInsights, setLoadingInsights] = useState(false);

  const generate = async () => {
    setLoadingReport(true);
    try {
      const analysis: Record<string, any> = {
        bias_scores: analysisData.bias_scores,
        feature_stats: analysisData.feature_stats,
        flagged_count: analysisData.flagged_trades.length,
      };
      if (counterfactual) {
        analysis.counterfactual = {
          original_pnl: counterfactual.original_pnl,
          counterfactual_pnl: counterfactual.counterfactual_pnl,
          pnl_delta: counterfactual.pnl_delta,
          removed_trades: counterfactual.removed_trades,
        };
      }
      const res = await fetchReport({ analysis });
      if (res.ok) {
        const data: CoachingResponse = await res.json();
        setReport(data);
      }
    } finally {
      setLoadingReport(false);
    }
  };

  const generateInsights = async () => {
    setLoadingInsights(true);
    try {
      const res = await fetchTradeInsights({
        flagged_trades: analysisData.flagged_trades,
        bias_scores: analysisData.bias_scores,
        normalized_trades: analysisData.normalized_trades,
      });
      if (res.ok) {
        const data: TradeInsightsResponse = await res.json();
        setTradeInsights(data);
      }
    } finally {
      setLoadingInsights(false);
    }
  };

  const biasTagColor: Record<string, string> = {
    overtrading: "bg-orange-100 text-orange-700",
    loss_aversion: "bg-red-100 text-red-700",
    revenge_trading: "bg-purple-100 text-purple-700",
  };

  return (
    <div className="space-y-4">
      {/* Coaching Report Card */}
      <Card className="border-0 shadow-md">
        <CardHeader className="pb-3 pt-4 px-4">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            🧠 AI Coaching Report
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 px-4 pb-4">
          {!report && (
            <div className="text-center py-6">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-100 to-teal-100 flex items-center justify-center mx-auto mb-3">
                <span className="text-2xl">🧠</span>
              </div>
              <p className="text-sm text-muted-foreground mb-4">
                Generate a personalized coaching report powered by Gemini AI
              </p>
              <Button
                onClick={generate}
                disabled={loadingReport}
                className="rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-medium px-8"
              >
                {loadingReport ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin">⏳</span> Generating…
                  </span>
                ) : (
                  "Generate Report"
                )}
              </Button>
            </div>
          )}
          {report && (
            <div className="animate-slide-up space-y-4">
              <div className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-foreground prose-p:text-muted-foreground prose-strong:text-foreground">
                <ReactMarkdown>{report.report_markdown}</ReactMarkdown>
              </div>
              {report.coaching_plan.length > 0 && (
                <div className="bg-muted/30 rounded-xl p-4">
                  <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                    📋 Action Plan
                  </h4>
                  <ol className="space-y-2">
                    {report.coaching_plan.map((step, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-3 text-sm"
                      >
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-[11px] font-bold">
                          {i + 1}
                        </span>
                        <span className="text-muted-foreground pt-0.5">
                          {step}
                        </span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Trade-Level Insights Card — Accordion style */}
      <Card className="border-0 shadow-md">
        <CardHeader className="pb-3 pt-4 px-4">
          <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            🔍 Per-Trade AI Insights
            {analysisData.flagged_trades.length > 0 && (
              <span className="text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">
                {analysisData.flagged_trades.length} flagged trade
                {analysisData.flagged_trades.length !== 1 ? "s" : ""}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 px-4 pb-4">
          {!tradeInsights && (
            <div className="text-center py-6">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-100 to-purple-100 flex items-center justify-center mx-auto mb-3">
                <span className="text-2xl">🔍</span>
              </div>
              <p className="text-sm text-muted-foreground mb-1">
                Get AI-powered explanations for each flagged trade
              </p>
              <p className="text-[11px] text-muted-foreground mb-4">
                Click each trade below to see bias flags, AI analysis, and
                market context.
              </p>
              <Button
                onClick={generateInsights}
                disabled={
                  loadingInsights || analysisData.flagged_trades.length === 0
                }
                className="rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-medium px-8"
              >
                {loadingInsights ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin">⏳</span> Analyzing trades…
                  </span>
                ) : (
                  "Analyze Flagged Trades"
                )}
              </Button>
            </div>
          )}

          {tradeInsights && (
            <div className="animate-slide-up space-y-3">
              {/* Summary */}
              <div className="rounded-xl bg-gradient-to-r from-violet-50 to-purple-50 border border-violet-200/50 p-4">
                <p className="text-sm text-muted-foreground">
                  {tradeInsights.summary}
                </p>
              </div>

              {/* Accordion trade list */}
              <div className="space-y-2">
                {tradeInsights.insights.map((insight, i) => (
                  <TradeAccordion
                    key={i}
                    insight={insight}
                    biasTagColor={biasTagColor}
                  />
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
