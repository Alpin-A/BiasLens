"use client";

import { useState } from "react";
import type { CounterfactualRules, CounterfactualResponse, CounterfactualTrade } from "@/types";
import { fetchCounterfactual } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";

interface Props {
  trades: Record<string, any>[];
  onResult?: (result: CounterfactualResponse) => void;
}

export default function CounterfactualPanel({ trades, onResult }: Props) {
  const [rules, setRules] = useState<CounterfactualRules>({
    cooldown_minutes_after_loss: 30,
    max_trades_per_day: 20,
    cap_size_after_loss: 1.0,
  });
  const [result, setResult] = useState<CounterfactualResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const res = await fetchCounterfactual(trades, rules);
      if (res.ok) {
        const data: CounterfactualResponse = await res.json();
        setResult(data);
        onResult?.(data);
      }
    } finally {
      setLoading(false);
    }
  };

  const chartData = result
    ? [
        { name: "Original", pnl: result.original_pnl },
        { name: "Counterfactual", pnl: result.counterfactual_pnl },
      ]
    : [];

  const statusColor = (status: string) => {
    if (status === "kept") return "default" as const;
    if (status === "removed") return "destructive" as const;
    return "secondary" as const;
  };

  return (
    <div className="space-y-4">
      <Card className="border-0 shadow-md">
        <CardHeader className="pb-3 pt-4 px-4">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            🔮 Behavioral Rules
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 px-4 pb-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground">
                Cooldown after loss (min)
              </label>
              <input
                type="number"
                value={rules.cooldown_minutes_after_loss}
                onChange={(e) =>
                  setRules((r) => ({
                    ...r,
                    cooldown_minutes_after_loss: +e.target.value,
                  }))
                }
                className="border border-border/50 rounded-lg px-3 py-1.5 w-full text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring/20 transition-all"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground">
                Max trades/day
              </label>
              <input
                type="number"
                value={rules.max_trades_per_day}
                onChange={(e) =>
                  setRules((r) => ({
                    ...r,
                    max_trades_per_day: +e.target.value,
                  }))
                }
                className="border border-border/50 rounded-lg px-3 py-1.5 w-full text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring/20 transition-all"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground">
                Cap size after loss (multiplier)
              </label>
              <input
                type="number"
                step="0.1"
                value={rules.cap_size_after_loss}
                onChange={(e) =>
                  setRules((r) => ({
                    ...r,
                    cap_size_after_loss: +e.target.value,
                  }))
                }
                className="border border-border/50 rounded-lg px-3 py-1.5 w-full text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring/20 transition-all"
              />
            </div>
          </div>
          <Button
            onClick={run}
            disabled={loading}
            className="w-full h-10 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-medium"
          >
            {loading ? "Simulating…" : "Run Counterfactual Simulation"}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-slide-up">
          <Card className="border-0 shadow-md">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Results Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 px-4 pb-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Original PnL</span>
                <span className="font-semibold font-mono text-sm">
                  {formatCurrency(result.original_pnl)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Counterfactual PnL</span>
                <span className="font-semibold font-mono text-sm text-emerald-600">
                  {formatCurrency(result.counterfactual_pnl)}
                </span>
              </div>
              <div className="flex justify-between items-center border-t pt-2">
                <span className="text-sm font-medium">Delta</span>
                <span
                  className={`font-bold font-mono ${
                    result.pnl_delta >= 0 ? "text-emerald-600" : "text-red-500"
                  }`}
                >
                  {result.pnl_delta >= 0 ? "+" : ""}
                  {formatCurrency(result.pnl_delta)}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 pt-2">
                <div className="text-center p-2 bg-muted/30 rounded-lg">
                  <p className="text-lg font-bold text-emerald-600">{result.kept_trades}</p>
                  <p className="text-[10px] text-muted-foreground">Kept</p>
                </div>
                <div className="text-center p-2 bg-muted/30 rounded-lg">
                  <p className="text-lg font-bold text-red-500">{result.removed_trades}</p>
                  <p className="text-[10px] text-muted-foreground">Removed</p>
                </div>
                <div className="text-center p-2 bg-muted/30 rounded-lg">
                  <p className="text-lg font-bold text-amber-500">{result.modified_trades}</p>
                  <p className="text-[10px] text-muted-foreground">Modified</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-md">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                PnL Comparison
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData} barCategoryGap="30%">
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 10 }} width={50} tickFormatter={(v) => `$${v}`} />
                  <Tooltip
                    formatter={(v: number) => [`$${v.toFixed(2)}`, "PnL"]}
                    contentStyle={{ borderRadius: "8px", fontSize: "12px", border: "1px solid hsl(var(--border))" }}
                  />
                  <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell
                        key={i}
                        fill={i === 0 ? "hsl(0 84% 60%)" : "hsl(142 76% 36%)"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Trade-level detail */}
          {result.modified_trade_list.length > 0 && (
            <Card className="md:col-span-2 border-0 shadow-md">
              <CardHeader className="pb-2 pt-4 px-4">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Trade Details
                </CardTitle>
              </CardHeader>
              <CardContent className="px-0 pb-3">
                <div className="max-h-[250px] overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/30 sticky top-0 text-left">
                      <tr>
                        <th className="px-4 py-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">#</th>
                        <th className="px-4 py-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Symbol</th>
                        <th className="px-4 py-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Side</th>
                        <th className="px-4 py-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">PnL</th>
                        <th className="px-4 py-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                        <th className="px-4 py-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.modified_trade_list.map((t) => (
                        <tr key={t.trade_index} className="border-t border-border/30 hover:bg-muted/20">
                          <td className="px-4 py-2 font-mono text-xs">{t.trade_index}</td>
                          <td className="px-4 py-2 font-semibold text-xs">{t.symbol}</td>
                          <td className="px-4 py-2 text-xs">{t.side}</td>
                          <td
                            className={`px-4 py-2 font-mono text-xs font-semibold ${
                              t.pnl >= 0 ? "text-emerald-600" : "text-red-500"
                            }`}
                          >
                            ${t.pnl.toFixed(2)}
                          </td>
                          <td className="px-4 py-2">
                            <Badge
                              variant={statusColor(t.status)}
                              className="text-[9px] px-1.5 py-0 h-4"
                            >
                              {t.status}
                            </Badge>
                          </td>
                          <td className="px-4 py-2 text-[11px] text-muted-foreground max-w-[200px] truncate">
                            {t.reason || "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
