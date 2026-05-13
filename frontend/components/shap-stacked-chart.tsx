"use client";

import { useMemo } from "react";
import type { ShapExplainResponse } from "@/types";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  shapData: ShapExplainResponse;
  biasClass: string;
  trades: Record<string, any>[];
}

const FEATURE_DISPLAY_NAMES: Record<string, string> = {
  trades_per_hour: "Trades/Hour",
  mean_time_between_trades_sec: "Avg Time Between Trades",
  std_time_between_trades_sec: "Time Variability",
  burst_count_60s: "Burst Count (60s)",
  pnl_mean: "Avg PnL",
  pnl_std: "PnL Volatility",
  pnl_total: "Total PnL",
  win_rate: "Win Rate",
  avg_quantity: "Avg Position Size",
  std_quantity: "Size Variability",
  avg_trade_value: "Avg Trade Value",
  loss_hold_to_win_hold_ratio: "Loss/Win Hold Ratio",
  avg_size_after_loss_ratio: "Size After Loss Ratio",
  reentry_after_loss_mean_sec: "Re-entry After Loss",
  consecutive_loss_streak_max: "Max Loss Streak",
  side_switch_rate: "Side Switch Rate",
  unique_symbols: "Unique Symbols",
  balance_drawdown_pct: "Balance Drawdown %",
};

// 8 distinct colors for top features + gray for "Other"
const FEATURE_COLORS = [
  "#6366f1", // indigo
  "#f59e0b", // amber
  "#10b981", // emerald
  "#ef4444", // red
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#f97316", // orange
  "#ec4899", // pink
];
const OTHER_COLOR = "#94a3b8"; // slate-400

function displayName(raw: string): string {
  return FEATURE_DISPLAY_NAMES[raw] || raw.replace(/_/g, " ");
}

function formatWindowDate(trades: Record<string, any>[], tradeIndex: number): string {
  if (tradeIndex >= trades.length) tradeIndex = trades.length - 1;
  if (tradeIndex < 0) return "";
  const ts = trades[tradeIndex]?.timestamp;
  if (!ts) return "";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return "";
  const year = d.getFullYear();
  const month = d.toLocaleString(undefined, { month: "short" });
  const day = d.getDate();
  return `${year} ${month} ${day}`;
}

export default function ShapStackedChart({ shapData, biasClass, trades }: Props) {
  const { topFeatures, chartData } = useMemo(() => {
    const { feature_names, windows } = shapData;
    const nFeatures = feature_names.length;

    // Calculate average absolute SHAP for each feature across all windows
    const avgAbsShap = feature_names.map((_, fi) => {
      const total = windows.reduce(
        (sum, w) => sum + Math.abs(w.shap_values[biasClass]?.[fi] ?? 0),
        0
      );
      return total / windows.length;
    });

    // Get top 8 feature indices sorted by avg absolute SHAP
    const indexed = avgAbsShap.map((v, i) => ({ idx: i, val: v }));
    indexed.sort((a, b) => b.val - a.val);
    const top8 = indexed.slice(0, 8);
    const topIndices = new Set(top8.map((t) => t.idx));

    const topFeats = top8.map((t) => ({
      idx: t.idx,
      name: feature_names[t.idx],
      display: displayName(feature_names[t.idx]),
    }));

    // Build chart data: one entry per window
    // Normalize SHAP values to score space (0-100) so bar heights = window scores
    const data = windows.map((w) => {
      const score = (w.predictions[biasClass] ?? 0) * 100;
      const shapVals = w.shap_values[biasClass] ?? [];

      // Sum of absolute SHAP values for normalization
      const totalAbsShap = shapVals.reduce((sum, v) => sum + Math.abs(v), 0);
      const scaleFactor = totalAbsShap > 0 ? score / totalAbsShap : 0;

      // X-axis: date from the start trade of this window
      const dateLabel = formatWindowDate(trades, w.trade_range[0]);

      const entry: Record<string, any> = {
        window: dateLabel || `W${w.window_index + 1}`,
        tradeRange: `Trades ${w.trade_range[0] + 1}\u2013${w.trade_range[1]}`,
        dateRange: dateLabel,
        score,
      };

      // Add each top feature as positive/negative split keys (scaled to score space)
      topFeats.forEach((f, rank) => {
        const rawShap = shapVals[f.idx] ?? 0;
        const scaled = rawShap * scaleFactor;
        entry[`pos_${rank}`] = scaled > 0 ? scaled : 0;
        entry[`neg_${rank}`] = scaled < 0 ? scaled : 0;
        entry[`raw_${rank}`] = scaled;
        entry[`featVal_${rank}`] = w.feature_values[f.idx] ?? 0;
      });

      // "Other" bucket: sum of remaining features split by sign (scaled)
      let otherPos = 0;
      let otherNeg = 0;
      for (let i = 0; i < nFeatures; i++) {
        if (topIndices.has(i)) continue;
        const scaled = (shapVals[i] ?? 0) * scaleFactor;
        if (scaled > 0) otherPos += scaled;
        else otherNeg += scaled;
      }
      entry["pos_other"] = otherPos;
      entry["neg_other"] = otherNeg;

      return entry;
    });

    return { topFeatures: topFeats, chartData: data };
  }, [shapData, biasClass, trades]);

  if (chartData.length === 0) return null;

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;
    const entry = payload[0]?.payload;
    if (!entry) return null;

    return (
      <div className="bg-card border rounded-lg px-3 py-2 shadow-lg text-xs max-w-xs">
        <p className="font-semibold mb-1">
          {entry.tradeRange}
          {entry.dateRange && (
            <span className="text-muted-foreground font-normal ml-1">({entry.dateRange})</span>
          )}
        </p>
        <p className="text-muted-foreground mb-2">
          Window Score: <span className="font-mono font-bold">{entry.score.toFixed(1)}</span>
          <span className="text-[10px] ml-1">/100</span>
        </p>
        <div className="space-y-0.5">
          {topFeatures.map((f, rank) => {
            const raw = entry[`raw_${rank}`] as number;
            if (Math.abs(raw) < 0.01) return null;
            return (
              <div key={rank} className="flex items-center gap-1.5">
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: FEATURE_COLORS[rank] }}
                />
                <span className="truncate">{f.display}:</span>
                <span
                  className={`font-mono font-bold ml-auto ${raw >= 0 ? "text-emerald-600" : "text-blue-600"}`}
                >
                  {raw >= 0 ? "+" : ""}{raw.toFixed(1)}
                </span>
              </div>
            );
          })}
          {(Math.abs(entry.pos_other) > 0.01 || Math.abs(entry.neg_other) > 0.01) && (
            <div className="flex items-center gap-1.5">
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: OTHER_COLOR }}
              />
              <span>Other:</span>
              <span className="font-mono font-bold ml-auto">
                {(entry.pos_other + entry.neg_other) >= 0 ? "+" : ""}{(entry.pos_other + entry.neg_other).toFixed(1)}
              </span>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <Card className="border-0 shadow-none bg-transparent mt-3">
      <CardHeader className="pb-2 px-0 pt-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          SHAP Feature Contributions Over Time
        </CardTitle>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -10, bottom: 20 }}
            stackOffset="sign"
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
            <XAxis
              dataKey="window"
              tick={{ fontSize: 9 }}
              tickLine={false}
              axisLine={false}
              angle={-35}
              textAnchor="end"
              height={50}
            />
            <YAxis
              tick={{ fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              domain={[
                (min: number) => Math.min(min, 0),
                (max: number) => Math.max(max, 100),
              ]}
              tickFormatter={(v: number) => `${Math.round(v)}`}
              label={{
                value: "Score",
                angle: -90,
                position: "insideLeft",
                offset: 20,
                style: { fontSize: 10, fill: "hsl(var(--muted-foreground))" },
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={0} stroke="hsl(var(--foreground))" strokeWidth={1} strokeOpacity={0.3} />

            {/* Positive stacks */}
            {topFeatures.map((f, rank) => (
              <Bar
                key={`pos_${rank}`}
                dataKey={`pos_${rank}`}
                stackId="stack"
                fill={FEATURE_COLORS[rank]}
                fillOpacity={0.85}
                name={f.display}
                animationDuration={400}
              />
            ))}
            <Bar
              dataKey="pos_other"
              stackId="stack"
              fill={OTHER_COLOR}
              fillOpacity={0.6}
              name="Other"
              animationDuration={400}
            />

            {/* Negative stacks */}
            {topFeatures.map((f, rank) => (
              <Bar
                key={`neg_${rank}`}
                dataKey={`neg_${rank}`}
                stackId="stack"
                fill={FEATURE_COLORS[rank]}
                fillOpacity={0.85}
                name={f.display}
                hide
                animationDuration={400}
              />
            ))}
            <Bar
              dataKey="neg_other"
              stackId="stack"
              fill={OTHER_COLOR}
              fillOpacity={0.6}
              name="Other (neg)"
              hide
              animationDuration={400}
            />
          </BarChart>
        </ResponsiveContainer>

        {/* Legend */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 px-1">
          {topFeatures.map((f, rank) => (
            <div key={rank} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <span
                className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                style={{ backgroundColor: FEATURE_COLORS[rank] }}
              />
              <span>{f.display}</span>
            </div>
          ))}
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <span
              className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
              style={{ backgroundColor: OTHER_COLOR }}
            />
            <span>Other</span>
          </div>
        </div>

        <p className="text-[10px] text-muted-foreground mt-2 px-1">
          Bars above zero push the score <span className="font-semibold">toward</span> this bias.
          Bars below zero push <span className="font-semibold">away</span> from it.
          Total bar height = window score (0-100).
        </p>
      </CardContent>
    </Card>
  );
}
