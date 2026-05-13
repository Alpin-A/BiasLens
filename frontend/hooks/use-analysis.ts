"use client";

import { useState, useCallback } from "react";
import type { AnalyzeResponse, ColumnMapping } from "@/types";
import { analyzeCSV } from "@/lib/api";

export function useAnalysis() {
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(async (file: File, mapping?: ColumnMapping) => {
    setLoading(true);
    setError(null);
    try {
      const res = await analyzeCSV(file, mapping as any);
      if (!res.ok) {
        const errData = await res
          .json()
          .catch(() => ({ detail: res.statusText }));
        throw new Error(errData.detail || "Analysis failed");
      }
      const result: AnalyzeResponse = await res.json();
      setData(result);
      return result;
    } catch (err: any) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, analyze };
}
