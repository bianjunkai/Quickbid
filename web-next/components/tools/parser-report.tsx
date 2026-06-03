"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

/**
 * 解析报告 4-tab 视图。
 *  - K01-K14：14 个关键字段
 *  - 标记扫描：by_symbol + by_page
 *  - 风险条款：5 个优先级分组
 *  - 结构化数据：8 个模块折叠
 */
export function ParserReport({ data }: { data: any }) {
  const [tab, setTab] = useState<"k" | "markers" | "risks" | "schema">("k");

  return (
    <div>
      {/* Tabs */}
      <div className="flex border-b border-border bg-paper">
        {[
          { id: "k", label: "K01-K14" },
          { id: "markers", label: "标记扫描" },
          { id: "risks", label: "风险条款" },
          { id: "schema", label: "结构化数据" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as any)}
            className={cn(
              "px-4 py-2 text-xs uppercase tracking-wider transition-colors",
              tab === t.id
                ? "text-ink border-b-2 border-amber"
                : "text-stone hover:text-ink"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4 max-h-[600px] overflow-y-auto">
        {tab === "k" && <KFields data={data} />}
        {tab === "markers" && <Markers data={data} />}
        {tab === "risks" && <Risks data={data} />}
        {tab === "schema" && <Schema data={data} />}
      </div>
    </div>
  );
}

function KFields({ data }: { data: any }) {
  const kfields = Object.keys(data)
    .filter((k) => /^K\d{2}_/.test(k))
    .sort();
  if (kfields.length === 0) {
    return <Empty text="无 K01-K14 字段" />;
  }
  return (
    <div className="space-y-2">
      {kfields.map((k) => {
        const v = data[k];
        const isArr = Array.isArray(v);
        return (
          <div key={k} className="border-b border-border pb-2 last:border-0">
            <div className="flex items-baseline gap-3">
              <span className="font-mono text-[10px] text-stone w-12 shrink-0 pt-1">
                {k.split("_")[0]}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[10px] text-stone mb-1">{k.split("_").slice(1).join("_")}</div>
                {isArr ? (
                  <div className="flex flex-wrap gap-1">
                    {v.map((item: any, i: number) => (
                      <span
                        key={i}
                        className="text-xs px-2 py-0.5 bg-amber-light text-amber rounded-sm"
                      >
                        {typeof item === "string" ? item.slice(0, 50) : JSON.stringify(item).slice(0, 50)}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-ink">{String(v ?? "—")}</div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Markers({ data }: { data: any }) {
  const sum = data.marker_extractions?.extraction_summary;
  const bySymbol = data._marker_summary?.by_symbol || sum?.by_symbol;
  const byPage = data._marker_summary?.by_page;

  if (!bySymbol && !byPage) {
    return <Empty text="无标记数据（manual 模式可能为空）" />;
  }
  return (
    <div className="space-y-4">
      {sum && (
        <div className="grid grid-cols-3 gap-2 text-center">
          <Stat label="总标记" value={sum.total_marker_occurrences ?? 0} />
          <Stat label="已映射" value={sum.total_mapped ?? 0} />
          <Stat label="未映射" value={sum.unmapped_count ?? 0} />
        </div>
      )}
      {bySymbol && (
        <div>
          <h4 className="text-[10px] uppercase tracking-wider text-stone mb-2">按符号</h4>
          <div className="space-y-1">
            {Object.entries(bySymbol)
              .sort((a: any, b: any) => Number(b[1]) - Number(a[1]))
              .map(([sym, n]) => {
                const nNum = Number(n);
                const maxNum = Math.max(
                  ...Object.values(bySymbol).map((v) => Number(v))
                );
                return (
                  <div key={sym} className="flex items-center gap-2 text-xs">
                    <span className="font-mono w-8">{sym}</span>
                    <div className="flex-1 h-2 bg-paper rounded-sm overflow-hidden">
                      <div
                        className="h-full bg-amber"
                        style={{ width: `${(nNum / maxNum) * 100}%` }}
                      />
                    </div>
                    <span className="text-stone w-8 text-right">{nNum}</span>
                  </div>
                );
              })}
          </div>
        </div>
      )}
      {byPage && Object.keys(byPage).length > 0 && (
        <div>
          <h4 className="text-[10px] uppercase tracking-wider text-stone mb-2">按页码（top 10）</h4>
          <div className="flex flex-wrap gap-1">
            {Object.entries(byPage)
              .sort((a: any, b: any) => Number(b[1]) - Number(a[1]))
              .slice(0, 10)
              .map(([p, n]) => (
                <span key={p} className="text-[10px] px-1.5 py-0.5 bg-paper rounded-sm">
                  p{p}: {Number(n)}
                </span>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Risks({ data }: { data: any }) {
  const groups = [
    { key: "fatal_items", label: "FATAL", color: "bg-red-100 text-red-700" },
    { key: "critical_items", label: "CRITICAL", color: "bg-amber-light text-amber" },
    { key: "high_items", label: "HIGH", color: "bg-amber-light text-amber" },
    { key: "medium_items", label: "MEDIUM", color: "bg-paper text-stone" },
    { key: "low_items", label: "LOW", color: "bg-paper text-stone" },
  ];
  const hasAny = groups.some((g) => (data.marker_extractions?.[g.key] || []).length > 0);
  if (!hasAny) return <Empty text="无风险条款（LLM 模式填充）" />;
  return (
    <div className="space-y-3">
      {groups.map((g) => {
        const items = data.marker_extractions?.[g.key] || [];
        if (items.length === 0) return null;
        return (
          <details key={g.key} open={g.key === "fatal_items"} className="border border-border rounded-sm">
            <summary className="px-3 py-2 cursor-pointer hover:bg-paper/50 flex items-center gap-2">
              <span className={cn("text-[10px] px-1.5 py-0.5 rounded-sm", g.color)}>
                {g.label}
              </span>
              <span className="text-xs text-stone">{items.length} 项</span>
            </summary>
            <div className="p-2 space-y-2 border-t border-border">
              {items.map((it: any, i: number) => (
                <div key={i} className="bg-paper p-2 rounded-sm">
                  <div className="flex items-center gap-2 mb-1 text-[10px] text-stone">
                    <span className="font-mono">{it.marker}</span>
                    {it.source_page && <span>p.{it.source_page}</span>}
                    {it.semantic && <span className="text-ink-light">· {it.semantic}</span>}
                  </div>
                  <div className="text-xs text-ink whitespace-pre-wrap font-mono leading-5">
                    {it.raw_text}
                  </div>
                </div>
              ))}
            </div>
          </details>
        );
      })}
    </div>
  );
}

function Schema({ data }: { data: any }) {
  const modules = [
    "base",
    "qualification",
    "rejection",
    "scoring",
    "tech",
    "commercial",
    "templates",
    "logistics",
  ];
  const present = modules.filter((m) => data[m]);
  if (present.length === 0) return <Empty text="无结构化数据" />;
  return (
    <div className="space-y-2">
      {present.map((m) => (
        <details key={m} className="border border-border rounded-sm">
          <summary className="px-3 py-2 cursor-pointer hover:bg-paper/50 text-xs font-medium text-ink">
            {m}{" "}
            <span className="text-stone font-normal">
              ({Object.keys(data[m]).length} keys)
            </span>
          </summary>
          <div className="p-3 border-t border-border bg-paper">
            <JsonView value={data[m]} />
          </div>
        </details>
      ))}
    </div>
  );
}

function JsonView({ value }: { value: any }) {
  if (value === null || value === undefined) return <span className="text-stone">null</span>;
  if (typeof value === "string") return <span className="text-ink">{value}</span>;
  if (typeof value === "number" || typeof value === "boolean")
    return <span className="text-amber font-mono">{String(value)}</span>;
  if (Array.isArray(value)) {
    return (
      <div className="space-y-1 pl-3 border-l border-border">
        {value.map((v, i) => (
          <div key={i} className="text-xs">
            <span className="text-stone font-mono mr-2">[{i}]</span>
            <JsonView value={v} />
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === "object") {
    return (
      <div className="space-y-1 pl-3 border-l border-border">
        {Object.entries(value).map(([k, v]) => (
          <div key={k} className="text-xs">
            <span className="text-ink-light font-mono mr-2">{k}:</span>
            <JsonView value={v} />
          </div>
        ))}
      </div>
    );
  }
  return <span>{String(value)}</span>;
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-paper border border-border rounded-sm p-2">
      <div className="text-[9px] text-stone uppercase tracking-wider">{label}</div>
      <div className="text-lg font-display text-ink mt-1">{value}</div>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="text-xs text-stone text-center py-8 border border-dashed border-border rounded-sm">
      {text}
    </div>
  );
}
