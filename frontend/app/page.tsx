"use client";

import { useState, useMemo } from "react";
import type {
  AnalyzeResponse,
  ColumnMapping,
  CounterfactualResponse,
} from "@/types";
import { analyzeCSV, type AnalysisMode } from "@/lib/api";
import CSVUpload from "@/components/csv-upload";
import BiasScoreCards from "@/components/bias-scorecards";
import TradeTable from "@/components/trade-table";
import InsightsCharts from "@/components/insights-charts";
import CounterfactualPanel from "@/components/counterfactual-panel";
import CoachingTab from "@/components/coaching-tab";
import NewsTab from "@/components/news-tab";
import ChatPanel from "@/components/chat-panel";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";

export default function Home() {
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [counterfactual, setCounterfactual] =
    useState<CounterfactualResponse | null>(null);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("mixed");

  const handleUpload = async (file: File, mapping?: ColumnMapping) => {
    setLoading(true);
    setError(null);
    try {
      const res = await analyzeCSV(file, mapping as any, analysisMode);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errData.detail || "Analysis failed");
      }
      const result: AnalyzeResponse = await res.json();
      setData(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const stats = useMemo(() => {
    if (!data) return null;
    const trades = data.normalized_trades;
    const totalPnl = trades.reduce((s, t) => s + Number(t.pnl ?? 0), 0);
    const wins = trades.filter((t) => Number(t.pnl ?? 0) > 0).length;
    const losses = trades.filter((t) => Number(t.pnl ?? 0) < 0).length;
    const winRate = trades.length > 0 ? wins / trades.length : 0;
    const avgPnl = trades.length > 0 ? totalPnl / trades.length : 0;
    const maxWin = Math.max(...trades.map((t) => Number(t.pnl ?? 0)));
    const maxLoss = Math.min(...trades.map((t) => Number(t.pnl ?? 0)));
    const bestTrade = trades.reduce((best, t) => {
      if (!best) return t;
      return Number(t.pnl ?? 0) > Number(best.pnl ?? 0) ? t : best;
    }, null as any);
    const worstTrade = trades.reduce((worst, t) => {
      if (!worst) return t;
      return Number(t.pnl ?? 0) < Number(worst.pnl ?? 0) ? t : worst;
    }, null as any);
    return { totalPnl, wins, losses, winRate, avgPnl, maxWin, maxLoss, bestTrade, worstTrade };
  }, [data]);

  const formatDateTime = (value?: string) => {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  };

  if (loading && !data) {
    return (
      <div className="space-y-5 animate-in">
        {/* Loading skeleton */}
        <div className="flex items-center justify-center gap-3 py-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center animate-pulse">
            <span className="text-white font-bold">B</span>
          </div>
          <div>
            <p className="text-lg font-bold">Analyzing your trades…</p>
            <p className="text-xs text-muted-foreground">Running bias detection, ML predictions & generating insights</p>
          </div>
        </div>
        {/* Stat cards skeleton */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className={`rounded-xl border border-border/50 bg-card p-3 shadow-sm animate-slide-up stagger-${i + 1}`}>
              <div className="skeleton h-3 w-16 mb-2" />
              <div className="skeleton h-6 w-20" />
            </div>
          ))}
        </div>
        {/* Bias cards skeleton */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className={`rounded-xl border border-border/50 bg-card p-4 shadow-sm animate-slide-up stagger-${i + 3}`}>
              <div className="skeleton h-10 w-10 rounded-full mb-3" />
              <div className="skeleton h-4 w-24 mb-2" />
              <div className="skeleton h-8 w-16 mb-2" />
              <div className="skeleton h-2 w-full rounded-full" />
            </div>
          ))}
        </div>
        {/* Tab area skeleton */}
        <div className="rounded-xl border border-border/50 bg-card p-6 shadow-sm animate-slide-up stagger-7">
          <div className="flex gap-2 mb-6">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="skeleton h-9 w-20 rounded-lg" />
            ))}
          </div>
          <div className="space-y-3">
            <div className="skeleton h-4 w-3/4" />
            <div className="skeleton h-4 w-1/2" />
            <div className="skeleton h-48 w-full rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-4rem)]">
        <div className="w-full max-w-xl space-y-8 animate-in">
          <div className="text-center space-y-3">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center mx-auto mb-4">
              <span className="text-white text-2xl font-bold">B</span>
            </div>
            <h1 className="text-4xl font-bold tracking-tight">
              Bias<span className="text-gradient">Lens</span>
            </h1>
            <p className="text-muted-foreground text-base max-w-md mx-auto">
              Upload your trade log to detect behavioral biases, simulate
              corrections, and get AI-powered coaching.
            </p>
          </div>
          {/* Analysis Mode Selector */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground text-center uppercase tracking-wider">Analysis Method</p>
            <div className="flex rounded-xl bg-muted/50 p-1 gap-1">
              {([
                { value: "rules_only", label: "📏 Rules Only", desc: "Hand-tuned detectors" },
                { value: "mixed", label: "⚖️ Mixed", desc: "60% Rules + 40% ML" },
                { value: "ml_only", label: "🤖 ML Only", desc: "XGBoost model" },
              ] as const).map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setAnalysisMode(opt.value)}
                  className={`flex-1 rounded-lg px-3 py-2 text-center transition-all ${
                    analysisMode === opt.value
                      ? "bg-background shadow-sm ring-1 ring-border/50"
                      : "hover:bg-background/50"
                  }`}
                >
                  <span className={`text-sm font-semibold block ${analysisMode === opt.value ? "text-foreground" : "text-muted-foreground"}`}>{opt.label}</span>
                  <span className="text-[10px] text-muted-foreground">{opt.desc}</span>
                </button>
              ))}
            </div>
          </div>
          <CSVUpload onUpload={handleUpload} isLoading={loading} />
          {error && (
            <Card className="border-destructive/50 bg-destructive/5">
              <CardContent className="py-3 text-sm text-destructive">
                {error}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    );
  }

  const handleReset = () => {
    setData(null);
    setCounterfactual(null);
    setError(null);
    setAnalysisMode("mixed");
  };

  return (
    <div className="space-y-5 animate-in">
      {/* Header with reset */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center">
            <span className="text-white text-sm font-bold">B</span>
          </div>
          <h1 className="text-xl font-bold tracking-tight">
            Bias<span className="text-gradient">Lens</span>
          </h1>
        </div>
        <button
          onClick={handleReset}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-muted/50 hover:bg-muted border border-border/50 transition-all hover:shadow-sm active:scale-[0.98]"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
          New Analysis
        </button>
      </div>

      {/* Summary stats strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <StatCard
          label="Total Trades"
          value={String(data.normalized_trades.length)}
        />
        <StatCard
          label="Total PnL"
          value={formatCurrency(stats!.totalPnl)}
          color={stats!.totalPnl >= 0 ? "text-emerald-600" : "text-red-500"}
        />
        <StatCard
          label="Win Rate"
          value={`${(stats!.winRate * 100).toFixed(1)}%`}
          color={stats!.winRate >= 0.5 ? "text-emerald-600" : "text-amber-500"}
        />
        <StatCard
          label="Avg PnL"
          value={formatCurrency(stats!.avgPnl)}
          color={stats!.avgPnl >= 0 ? "text-emerald-600" : "text-red-500"}
        />
        <StatCard
          label="Best Trade"
          value={formatCurrency(stats!.maxWin)}
          color="text-emerald-600"
          detail={formatDateTime(stats!.bestTrade?.timestamp)}
        />
        <StatCard
          label="Worst Trade"
          value={formatCurrency(stats!.maxLoss)}
          color="text-red-500"
          detail={formatDateTime(stats!.worstTrade?.timestamp)}
        />
        <StatCard
          label="Flagged"
          value={`${data.flagged_trades.length}`}
          color={data.flagged_trades.length > 0 ? "text-amber-500" : "text-emerald-600"}
        />
      </div>

      {/* Analysis Mode Badge */}
      {(() => {
        const mode = data.feature_stats?.analysis_mode || "mixed";
        const mlActive = data.feature_stats?.ml_active;
        const configs: Record<string, { label: string; desc: string; color: string; border: string; dot: string; ping: string }> = {
          rules_only: { label: "📏 Rules Only", desc: "Scores from hand-tuned rule-based detectors", color: "text-blue-700", border: "bg-blue-50 border-blue-200/50", dot: "bg-blue-500", ping: "bg-blue-400" },
          ml_only: { label: "🤖 ML Only", desc: "Scores from XGBoost model predictions", color: "text-violet-700", border: "bg-violet-50 border-violet-200/50", dot: "bg-violet-500", ping: "bg-violet-400" },
          mixed: { label: "⚖️ Mixed", desc: "Scores blend 60% rule-based + 40% ML predictions", color: "text-emerald-700", border: "bg-emerald-50 border-emerald-200/50", dot: "bg-emerald-500", ping: "bg-emerald-400" },
        };
        const c = configs[mode] || configs.mixed;
        return (
          <div className="flex items-center gap-2 px-1">
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border ${c.border}`}>
              <span className="relative flex h-2 w-2">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${c.ping} opacity-75`}></span>
                <span className={`relative inline-flex rounded-full h-2 w-2 ${c.dot}`}></span>
              </span>
              <span className={`text-[11px] font-semibold ${c.color}`}>{c.label}{mlActive ? " + ML Active" : ""}</span>
            </div>
            <span className="text-[10px] text-muted-foreground">{c.desc}</span>
          </div>
        );
      })()}
      <BiasScoreCards scores={data.bias_scores} trades={data.normalized_trades} />

      {/* Tabbed views */}
      <Tabs defaultValue="insights" className="w-full">
        <TabsList className="w-full justify-start gap-1 bg-muted/50 p-1 rounded-xl h-auto flex-wrap">
          <TabsTrigger value="insights" className="rounded-lg text-xs sm:text-sm px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            📊 Insights
          </TabsTrigger>
          <TabsTrigger value="timeline" className="rounded-lg text-xs sm:text-sm px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            📋 Timeline
          </TabsTrigger>
          <TabsTrigger value="counterfactual" className="rounded-lg text-xs sm:text-sm px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            🔮 What-If
          </TabsTrigger>
          <TabsTrigger value="coaching" className="rounded-lg text-xs sm:text-sm px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            🧠 Coaching
          </TabsTrigger>
          <TabsTrigger value="news" className="rounded-lg text-xs sm:text-sm px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            📰 News
          </TabsTrigger>
        </TabsList>

        <TabsContent value="insights" className="mt-4 animate-slide-up">
          <InsightsCharts
            trades={data.normalized_trades}
            featureStats={data.feature_stats}
            biasEvidence={data.bias_evidence}
          />
        </TabsContent>

        <TabsContent value="timeline" className="mt-4 animate-slide-up">
          <TradeTable
            trades={data.normalized_trades}
            flaggedTrades={data.flagged_trades}
          />
        </TabsContent>

        <TabsContent value="counterfactual" className="mt-4 animate-slide-up">
          <CounterfactualPanel
            trades={data.normalized_trades}
            onResult={setCounterfactual}
          />
        </TabsContent>

        <TabsContent value="coaching" className="mt-4 animate-slide-up">
          <CoachingTab
            analysisData={data}
            counterfactual={counterfactual}
          />
        </TabsContent>

        <TabsContent value="news" className="mt-4 animate-slide-up">
          <NewsTab analysisData={data} />
        </TabsContent>
      </Tabs>

      {/* Floating AI Chat */}
      <ChatPanel analysisData={data} />
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
  detail,
}: {
  label: string;
  value: string;
  color?: string;
  detail?: string;
}) {
  return (
    <div className="rounded-xl border border-border/50 bg-card p-3 shadow-sm">
      <p className="text-[11px] font-medium text-muted-foreground truncate">
        {label}
      </p>
      <p className={`text-lg font-bold tracking-tight mt-0.5 ${color || ""}`}>
        {value}
      </p>
      {detail ? (
        <p className="text-[11px] text-muted-foreground mt-0.5 truncate">
          {detail}
        </p>
      ) : null}
    </div>
  );
}
