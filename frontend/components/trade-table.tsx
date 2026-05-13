"use client";

import type { BiasFlag } from "@/types";
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  type ColumnFiltersState,
} from "@tanstack/react-table";
import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type TradeRow = Record<string, any> & { _idx: number };

interface Props {
  trades: Record<string, any>[];
  flaggedTrades: BiasFlag[];
}

const columnHelper = createColumnHelper<TradeRow>();

export default function TradeTable({ trades, flaggedTrades }: Props) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  const flagMap = useMemo(() => {
    const map: Record<number, string[]> = {};
    for (const f of flaggedTrades) {
      map[f.trade_index] = f.tags;
    }
    return map;
  }, [flaggedTrades]);

  const data: TradeRow[] = useMemo(
    () => trades.map((t, i) => ({ ...t, _idx: i })),
    [trades]
  );

  const columns = useMemo(
    () => [
      columnHelper.accessor("timestamp", {
        header: "Time",
        cell: (info) => {
          const v = info.getValue();
          return (
            <span className="font-mono text-xs">
              {typeof v === "string" ? v : String(v)}
            </span>
          );
        },
      }),
      columnHelper.accessor("side", {
        header: "Side",
        cell: (info) => {
          const side = String(info.getValue()).toLowerCase();
          return (
            <span
              className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${
                side === "buy"
                  ? "bg-emerald-100 text-emerald-700"
                  : "bg-red-100 text-red-700"
              }`}
            >
              {side}
            </span>
          );
        },
      }),
      columnHelper.accessor("symbol", {
        header: "Symbol",
        cell: (info) => (
          <span className="font-semibold text-xs">{String(info.getValue())}</span>
        ),
      }),
      columnHelper.accessor("quantity", {
        header: "Qty",
        cell: (info) => (
          <span className="font-mono text-xs">
            {Number(info.getValue()).toLocaleString()}
          </span>
        ),
      }),
      columnHelper.accessor("price", {
        header: "Price",
        cell: (info) => (
          <span className="font-mono text-xs">
            ${Number(info.getValue()).toFixed(2)}
          </span>
        ),
      }),
      columnHelper.accessor("pnl", {
        header: "PnL",
        cell: (info) => {
          const val = Number(info.getValue());
          return (
            <span
              className={`font-mono text-xs font-semibold ${
                val >= 0 ? "text-emerald-600" : "text-red-500"
              }`}
            >
              {val >= 0 ? "+" : ""}${val.toFixed(2)}
            </span>
          );
        },
      }),
      columnHelper.display({
        id: "biases",
        header: "Biases",
        cell: (info) => {
          const tags = flagMap[info.row.original._idx] || ["calm"];
          return (
            <div className="flex gap-1 flex-wrap">
              {tags.map((tag) => (
                <Badge
                  key={tag}
                  variant={tag === "calm" ? "secondary" : "destructive"}
                  className={`text-[9px] px-1.5 py-0 h-4 font-medium ${
                    tag === "calm"
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                      : ""
                  }`}
                >
                  {tag.replace(/_/g, " ")}
                </Badge>
              ))}
            </div>
          );
        },
      }),
    ],
    [flagMap]
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnFilters, globalFilter },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <Card className="border-0 shadow-md">
      <CardHeader className="pb-3 pt-4 px-4">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Trade Log
          </CardTitle>
          <input
            placeholder="Search trades…"
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="border border-border/50 rounded-lg px-3 py-1.5 text-xs w-full max-w-[200px] bg-background focus:outline-none focus:ring-2 focus:ring-ring/20 transition-all"
          />
        </div>
      </CardHeader>
      <CardContent className="px-0 pb-3">
        <div className="overflow-auto max-h-[480px]">
          <table className="w-full text-sm">
            <thead className="bg-muted sticky top-0 z-10">
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-4 py-2 text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider cursor-pointer select-none hover:text-foreground transition-colors"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext()
                      )}
                      {{ asc: " ↑", desc: " ↓" }[
                        header.column.getIsSorted() as string
                      ] ?? ""}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => {
                const tags = flagMap[row.original._idx];
                const hasBias = !!tags && tags.length > 0;
                return (
                  <tr
                    key={row.id}
                    className={`border-t border-border/30 transition-colors ${
                      hasBias
                        ? "bg-red-50/50 hover:bg-red-50"
                        : "hover:bg-muted/20"
                    }`}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-2">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="px-4 pt-2">
          <p className="text-[11px] text-muted-foreground">
            {table.getRowModel().rows.length} of {trades.length} trades ·{" "}
            {flaggedTrades.length} flagged
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
