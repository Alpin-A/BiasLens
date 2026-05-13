"use client";

import { useState, useRef, useCallback } from "react";
import type { BiasScore, ShapExplainResponse } from "@/types";
import { fetchShapExplain } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import ShapStackedChart from "./shap-stacked-chart";

interface Props {
  scores: Record<string, BiasScore>;
  trades?: Record<string, any>[];
}

const BIAS_CONFIG: Record<
  string,
  { label: string; emoji: string; gradient: string; barColor: string; iconBg: string }
> = {
  calm: {
    label: "Calm / Disciplined",
    emoji: "\u{1F9D8}",
    gradient: "from-emerald-500/10 to-green-500/5",
    barColor: "bg-emerald-500",
    iconBg: "bg-emerald-100 text-emerald-600",
  },
  overtrading: {
    label: "Overtrading",
    emoji: "\u26A1",
    gradient: "from-orange-500/10 to-amber-500/5",
    barColor: "bg-orange-500",
    iconBg: "bg-orange-100 text-orange-600",
  },
  loss_aversion: {
    label: "Loss Aversion",
    emoji: "\u{1F630}",
    gradient: "from-red-500/10 to-rose-500/5",
    barColor: "bg-red-500",
    iconBg: "bg-red-100 text-red-600",
  },
  revenge_trading: {
    label: "Revenge Trading",
    emoji: "\u{1F525}",
    gradient: "from-purple-500/10 to-violet-500/5",
    barColor: "bg-purple-500",
    iconBg: "bg-purple-100 text-purple-600",
  },
};

function getSeverityColor(score: number, isCalm = false) {
  if (isCalm) {
    if (score >= 60) return "text-emerald-500";
    if (score >= 30) return "text-amber-500";
    return "text-red-500";
  }
  if (score > 50) return "text-red-500";
  if (score > 30) return "text-amber-500";
  return "text-emerald-500";
}

function getSeverityBg(score: number, isCalm = false) {
  if (isCalm) {
    if (score >= 60) return "bg-emerald-500";
    if (score >= 30) return "bg-amber-500";
    return "bg-red-500";
  }
  if (score > 50) return "bg-red-500";
  if (score > 30) return "bg-amber-500";
  return "bg-emerald-500";
}

export default function BiasScoreCards({ scores, trades }: Props) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [shapData, setShapData] = useState<ShapExplainResponse | null>(null);
  const [shapLoading, setShapLoading] = useState(false);
  const [shapError, setShapError] = useState<string | null>(null);
  const shapFetched = useRef(false);

  const loadShapData = useCallback(async () => {
    if (shapFetched.current || !trades || trades.length === 0) return;
    shapFetched.current = true;
    setShapLoading(true);
    setShapError(null);
    try {
      const res = await fetchShapExplain(trades);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errData.detail || "SHAP computation failed");
      }
      const data: ShapExplainResponse = await res.json();
      setShapData(data);
    } catch (err: any) {
      setShapError(err.message);
      shapFetched.current = false; // Allow retry
    } finally {
      setShapLoading(false);
    }
  }, [trades]);

  const handleCardClick = (key: string) => {
    if (expandedKey === key) {
      setExpandedKey(null);
      return;
    }
    setExpandedKey(key);
    if (!shapData && !shapLoading) {
      loadShapData();
    }
  };

  // Show calm first, then biases
  const orderedKeys = ["calm", "overtrading", "loss_aversion", "revenge_trading"].filter(k => k in scores);
  // Add any extra keys not in the predefined order
  Object.keys(scores).forEach(k => { if (!orderedKeys.includes(k)) orderedKeys.push(k); });

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
      {orderedKeys.map((key) => {
        const bias = scores[key];
        const isCalm = key === "calm";
        const isExpanded = expandedKey === key;
        const config = BIAS_CONFIG[key] || {
          label: key,
          emoji: "\u{1F4CA}",
          gradient: "from-slate-500/10 to-slate-500/5",
          barColor: "bg-slate-500",
          iconBg: "bg-slate-100 text-slate-600",
        };

        return (
          <Card
            key={key}
            className={`border-0 shadow-md overflow-hidden bg-gradient-to-br ${config.gradient} cursor-pointer transition-all duration-300 ${
              isExpanded ? "md:col-span-4 col-span-1" : ""
            }`}
            onClick={() => handleCardClick(key)}
          >
            <CardContent className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm ${config.iconBg}`}
                  >
                    {config.emoji}
                  </div>
                  <div>
                    <p className="text-sm font-semibold leading-tight">
                      {config.label}
                    </p>
                    <p className="text-[11px] text-muted-foreground capitalize">
                      {isCalm ? (bias.score >= 60 ? "disciplined" : bias.score >= 30 ? "moderate" : "low discipline") : `${bias.severity} severity`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-2xl font-bold tabular-nums ${getSeverityColor(bias.score, isCalm)}`}
                  >
                    {bias.score.toFixed(0)}
                  </span>
                  <svg
                    className={`w-4 h-4 text-muted-foreground transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
              <div className="w-full bg-black/5 rounded-full h-1.5 mb-2">
                <div
                  className={`h-1.5 rounded-full transition-all duration-500 ${getSeverityBg(bias.score, isCalm)}`}
                  style={{ width: `${Math.min(bias.score, 100)}%` }}
                />
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                {bias.rationale}
              </p>

              {/* Expanded SHAP section */}
              {isExpanded && (
                <div className="mt-4 animate-slide-up" onClick={(e) => e.stopPropagation()}>
                  {shapLoading && (
                    <div className="flex items-center justify-center py-8 gap-2">
                      <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      <span className="text-sm text-muted-foreground">Computing SHAP explanations...</span>
                    </div>
                  )}
                  {shapError && (
                    <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                      {shapError}
                    </div>
                  )}
                  {shapData && trades && (
                    <ShapStackedChart shapData={shapData} biasClass={key} trades={trades} />
                  )}
                  {!shapLoading && !shapError && !shapData && !trades?.length && (
                    <p className="text-xs text-muted-foreground text-center py-4">
                      No trade data available for SHAP analysis.
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
