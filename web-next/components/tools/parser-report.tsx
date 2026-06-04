"use client";

import { useState } from "react";
import { ChevronRight, Copy, Check, BarChart3, AlertTriangle, FileCode2, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "k", label: "K01–K14", icon: Layers, num: "01" },
  { id: "markers", label: "标记", icon: BarChart3, num: "02" },
  { id: "risks", label: "风险", icon: AlertTriangle, num: "03" },
  { id: "schema", label: "数据", icon: FileCode2, num: "04" },
] as const;

export function ParserReport({ data }: { data: any }) {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("k");
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (typeof window === "undefined") return;
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div>
      {/* Header */}
      <div className="px-6 pt-6 pb-4">
        <div className="flex items-end justify-between mb-1">
          <div>
            <div className="text-[11px] text-[var(--color-ink-mute)] uppercase tracking-wider font-medium mb-1">
              解析报告 · {data?._mode?.toUpperCase() || "FULL"}
            </div>
            <h2 className="text-[24px] font-semibold text-[var(--color-ink)] tracking-tight">
              招标文件解析结果
            </h2>
          </div>
          <button
            onClick={handleCopy}
            className="btn-soft"
            aria-label="复制 JSON"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-[var(--color-success)]" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? "已复制" : "复制 JSON"}</span>
          </button>
        </div>
      </div>

      {/* Pill tabs (matches reference) */}
      <div className="px-6 mb-5">
        <div className="inline-flex p-1 bg-[var(--color-paper-warm)] rounded-xl gap-0.5" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              aria-controls={`panel-${t.id}`}
              onClick={() => setTab(t.id)}
              className={cn(
                "flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[12px] font-medium transition-all min-h-[32px]",
                tab === t.id
                  ? "bg-white text-[var(--color-ink)] shadow-sm"
                  : "text-[var(--color-ink-mute)] hover:text-[var(--color-ink)]"
              )}
            >
              <t.icon className="w-3.5 h-3.5" />
              {t.label}
              <span className="text-[10px] text-[var(--color-ink-mute)] font-mono ml-0.5">{t.num}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="px-6 pb-8">
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
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {kfields.map((k) => {
        const v = data[k];
        const isArr = Array.isArray(v);
        return (
          <div key={k} className="card-soft p-4 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-mono text-[var(--color-primary)] font-semibold">
                {k.split("_")[0]}
              </span>
              <span className="text-[11px] text-[var(--color-ink-mute)] font-mono truncate">
                {k.split("_").slice(1).join("_")}
              </span>
            </div>
            {isArr ? (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {v.slice(0, 6).map((item: any, i: number) => (
                  <span
                    key={i}
                    className="text-[11px] px-2 py-0.5 bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)] rounded-full"
                  >
                    {typeof item === "string" ? item.slice(0, 30) : JSON.stringify(item).slice(0, 30)}
                  </span>
                ))}
                {v.length > 6 && (
                  <span className="text-[11px] text-[var(--color-ink-mute)]">+{v.length - 6}</span>
                )}
              </div>
            ) : (
              <div className="text-[13.5px] text-[var(--color-ink)] leading-relaxed">
                {String(v ?? "—")}
              </div>
            )}
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
        <div className="grid grid-cols-3 gap-3">
          <Stat label="总标记" value={sum.total_marker_occurrences ?? 0} />
          <Stat label="已映射" value={sum.total_mapped ?? 0} state="done" />
          <Stat label="未映射" value={sum.unmapped_count ?? 0} state="warning" />
        </div>
      )}
      {bySymbol && (
        <div className="card-soft p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-[14px] font-semibold text-[var(--color-ink)]">按符号分布</h3>
            <span className="text-[11px] text-[var(--color-ink-mute)] font-mono">
              {Object.keys(bySymbol).length} 类
            </span>
          </div>
          <div className="space-y-2.5">
            {Object.entries(bySymbol)
              .sort((a: any, b: any) => Number(b[1]) - Number(a[1]))
              .map(([sym, n], i, arr) => {
                const nNum = Number(n);
                const maxNum = Math.max(...arr.map(([, v]) => Number(v)));
                const pct = maxNum > 0 ? (nNum / maxNum) * 100 : 0;
                return (
                  <div key={sym} className="flex items-center gap-3 text-[12px]">
                    <span className="text-[var(--color-ink-mute)] w-4 tabular-nums text-right font-mono">
                      {i + 1}
                    </span>
                    <span className="text-[var(--color-ink)] w-8 font-mono font-semibold">{sym}</span>
                    <div className="flex-1 h-2 bg-[var(--color-paper-warm)] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-soft)] rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-[var(--color-ink)] w-10 text-right tabular-nums font-mono font-semibold">
                      {nNum}
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}
      {byPage && Object.keys(byPage).length > 0 && (
        <div className="card-soft p-5">
          <h3 className="text-[14px] font-semibold text-[var(--color-ink)] mb-3">按页码 · Top 10</h3>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(byPage)
              .sort((a: any, b: any) => Number(b[1]) - Number(a[1]))
              .slice(0, 10)
              .map(([p, n]) => (
                <span
                  key={p}
                  className="text-[11px] px-2.5 py-1 bg-[var(--color-paper-warm)] text-[var(--color-ink)] rounded-full font-mono tabular-nums"
                >
                  P{String(p).padStart(3, "0")} · {Number(n)}
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
    { key: "fatal_items", label: "FATAL", state: "error" as const },
    { key: "critical_items", label: "CRITICAL", state: "error" as const },
    { key: "high_items", label: "HIGH", state: "warning" as const },
    { key: "medium_items", label: "MEDIUM", state: "warning" as const },
    { key: "low_items", label: "LOW", state: "parsed" as const },
  ];
  const hasAny = groups.some((g) => (data.marker_extractions?.[g.key] || []).length > 0);
  if (!hasAny) return <Empty text="无风险条款（LLM 模式填充）" />;
  return (
    <div className="space-y-2.5">
      {groups.map((g) => {
        const items = data.marker_extractions?.[g.key] || [];
        if (items.length === 0) return null;
        return (
          <details
            key={g.key}
            open={g.key === "fatal_items"}
            className="card-soft overflow-hidden group"
          >
            <summary className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-[var(--color-paper-warm)] transition-colors list-none">
              <ChevronRight className="w-3.5 h-3.5 text-[var(--color-ink-mute)] transition-transform group-open:rotate-90" />
              <span className="pill-soft" data-state={g.state}>
                <span className="dot" />
                {g.label}
              </span>
              <span className="text-[12px] text-[var(--color-ink-mute)]">· {items.length} 项</span>
            </summary>
            <div className="border-t border-[var(--color-border)] divide-y divide-[var(--color-border)]">
              {items.map((it: any, i: number) => (
                <div key={i} className="px-4 py-3">
                  <div className="flex items-center gap-2 mb-2 text-[10px] text-[var(--color-ink-mute)] font-mono">
                    <span className="text-[var(--color-primary)] font-semibold">{it.marker}</span>
                    {it.source_page && (
                      <>
                        <span>·</span>
                        <span>P{String(it.source_page).padStart(3, "0")}</span>
                      </>
                    )}
                    {it.semantic && (
                      <>
                        <span>·</span>
                        <span className="text-[var(--color-ink-soft)]">{it.semantic}</span>
                      </>
                    )}
                  </div>
                  <pre className="text-[12px] text-[var(--color-ink)] font-mono whitespace-pre-wrap leading-[1.7] bg-[var(--color-paper-warm)] p-3 rounded-lg">
                    {it.raw_text}
                  </pre>
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
    <div className="space-y-2.5">
      {present.map((m, i) => (
        <details key={m} className="card-soft overflow-hidden group">
          <summary className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-[var(--color-paper-warm)] transition-colors list-none">
            <ChevronRight className="w-3.5 h-3.5 text-[var(--color-ink-mute)] transition-transform group-open:rotate-90" />
            <span className="text-[12px] font-mono font-semibold text-[var(--color-ink)]">{m}</span>
            <span className="text-[11px] text-[var(--color-ink-mute)] font-mono">
              · {Object.keys(data[m]).length} keys
            </span>
          </summary>
          <div className="border-t border-[var(--color-border)] bg-[var(--color-paper-warm)] p-4">
            <JsonView value={data[m]} />
          </div>
        </details>
      ))}
    </div>
  );
}

function JsonView({ value }: { value: any }) {
  if (value === null || value === undefined)
    return <span className="text-[var(--color-ink-mute)] font-mono text-[12px]">null</span>;
  if (typeof value === "string")
    return <span className="text-[var(--color-success)] font-mono text-[12.5px]">"{value}"</span>;
  if (typeof value === "number" || typeof value === "boolean")
    return <span className="text-[var(--color-primary)] font-mono text-[12.5px] font-semibold">{String(value)}</span>;
  if (Array.isArray(value)) {
    return (
      <div className="space-y-0.5 pl-4 border-l-2 border-[var(--color-border)]">
        {value.map((v, i) => (
          <div key={i} className="text-[12.5px] flex items-baseline gap-2">
            <span className="text-[var(--color-ink-mute)] font-mono text-[10px] shrink-0 w-8 text-right tabular-nums">
              [{i}]
            </span>
            <JsonView value={v} />
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === "object") {
    return (
      <div className="space-y-0.5 pl-4 border-l-2 border-[var(--color-border)]">
        {Object.entries(value).map(([k, v]) => (
          <div key={k} className="text-[12.5px] flex items-baseline gap-2">
            <span className="text-[var(--color-ink)] font-mono text-[12px] font-semibold shrink-0">
              {k}:
            </span>
            <JsonView value={v} />
          </div>
        ))}
      </div>
    );
  }
  return <span className="font-mono">{String(value)}</span>;
}

function Stat({ label, value, state }: { label: string; value: number | string; state?: "done" | "warning" | "error" }) {
  const color =
    state === "done" ? "var(--color-success)" : state === "warning" ? "var(--color-warning)" : state === "error" ? "var(--color-danger)" : "var(--color-ink)";
  return (
    <div className="card-soft p-4">
      <div className="text-[11px] text-[var(--color-ink-mute)] uppercase tracking-wider font-medium mb-1">
        {label}
      </div>
      <div className="text-[32px] font-semibold tabular-nums leading-none" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="card-soft border-dashed py-12 text-center">
      <div className="text-[12px] text-[var(--color-ink-mute)]">{text}</div>
    </div>
  );
}
