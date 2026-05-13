"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import type { ColumnMapping } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface Props {
  onUpload: (file: File, mapping?: ColumnMapping) => void;
  isLoading: boolean;
}

const REQUIRED_FIELDS = ["timestamp", "side", "symbol", "quantity", "price"];
const OPTIONAL_FIELDS = ["pnl", "hold_minutes"];

// Common aliases for each field — used for auto-detection
const FIELD_ALIASES: Record<string, string[]> = {
  timestamp: ["timestamp", "time", "date", "datetime", "date_time", "trade_time", "executed_at"],
  side: ["side", "direction", "type", "action", "buy_sell", "buysell", "order_side"],
  symbol: ["symbol", "asset", "ticker", "instrument", "stock", "coin", "pair", "name"],
  quantity: ["quantity", "qty", "size", "amount", "volume", "shares", "lots"],
  price: ["price", "entry_price", "entryprice", "exec_price", "fill_price", "avg_price", "trade_price"],
  pnl: ["pnl", "profit_loss", "profitloss", "profit", "pl", "p_l", "realized_pnl", "realizedpnl", "gain", "return"],
  hold_minutes: ["hold_minutes", "holdminutes", "hold_time", "holdtime", "duration", "hold_duration"],
};

export default function CSVUpload({ onUpload, isLoading }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [autoDetected, setAutoDetected] = useState(false);

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length === 0) return;
    const f = accepted[0];
    setFile(f);

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const firstLine = text.split("\n")[0];
      const cols = firstLine
        .split(",")
        .map((c) => c.trim().replace(/"/g, ""));
      setHeaders(cols);

      // Auto-detect using aliases
      const lowerCols = cols.map((c) => c.toLowerCase().trim());
      const autoMap: Record<string, string> = {};
      const allFields = [...REQUIRED_FIELDS, ...OPTIONAL_FIELDS];
      for (const field of allFields) {
        const aliases = FIELD_ALIASES[field] || [field];
        const match = lowerCols.findIndex((c) =>
          aliases.some((alias) => c === alias || c.replace(/[_\s-]/g, "") === alias.replace(/[_\s-]/g, ""))
        );
        if (match >= 0) autoMap[field] = cols[match];
      }
      setMapping(autoMap);
      setAutoDetected(
        REQUIRED_FIELDS.every((f) => f in autoMap)
      );
    };
    reader.readAsText(f);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"] },
    maxFiles: 1,
  });

  const handleSubmit = () => {
    if (!file) return;
    const hasRequired = REQUIRED_FIELDS.every((f) => mapping[f]);
    const columnMapping: ColumnMapping | undefined = hasRequired
      ? (mapping as unknown as ColumnMapping)
      : undefined;
    onUpload(file, columnMapping);
  };

  return (
    <Card className="w-full border-0 shadow-lg">
      <CardContent className="p-6 space-y-4">
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-200 ${
            isDragActive
              ? "border-blue-500 bg-blue-50/50 scale-[1.01]"
              : "border-border hover:border-blue-400/50 hover:bg-muted/30"
          }`}
        >
          <input {...getInputProps()} />
          {file ? (
            <div className="space-y-1">
              <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-2">
                ✓
              </div>
              <p className="text-sm font-semibold">{file.name}</p>
              <p className="text-xs text-muted-foreground">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="w-12 h-12 rounded-xl bg-muted flex items-center justify-center mx-auto">
                <span className="text-xl">📁</span>
              </div>
              <p className="text-sm font-semibold">
                Drop your CSV here, or click to browse
              </p>
              <p className="text-xs text-muted-foreground">
                Requires: timestamp, side, symbol, quantity, price
              </p>
            </div>
          )}
        </div>

        {headers.length > 0 && (
          <div className="space-y-3 animate-slide-up">
            <h4 className="font-medium text-xs text-muted-foreground uppercase tracking-wider">
              Column Mapping
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {[...REQUIRED_FIELDS, ...OPTIONAL_FIELDS].map((field) => (
                <div key={field} className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground">
                    {field}
                    {REQUIRED_FIELDS.includes(field) && (
                      <span className="text-red-400 ml-0.5">*</span>
                    )}
                  </label>
                  <select
                    className="w-full border border-border/50 rounded-lg px-2 py-1.5 text-xs bg-background focus:outline-none focus:ring-2 focus:ring-ring/20 transition-all"
                    value={mapping[field] || ""}
                    onChange={(e) =>
                      setMapping((prev) => ({
                        ...prev,
                        [field]: e.target.value,
                      }))
                    }
                  >
                    <option value="">-- select --</option>
                    {headers.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
            {autoDetected && (
              <p className="text-xs text-emerald-600 font-medium flex items-center gap-1">
                <span className="w-4 h-4 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-[10px]">
                  ✓
                </span>
                Columns auto-detected successfully
              </p>
            )}
          </div>
        )}

        <Button
          onClick={handleSubmit}
          disabled={!file || isLoading}
          className="w-full h-10 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-700 hover:to-violet-700 text-white font-medium transition-all"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <span className="animate-spin">⏳</span> Analyzing…
            </span>
          ) : (
            "Analyze Trades"
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
