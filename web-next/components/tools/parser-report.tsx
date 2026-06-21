"use client";

import { useState } from "react";
import { ChevronRight, Copy, Check, BarChart3, AlertTriangle, FileCode2, Layers, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { Schema } from "./parser-schema";

const TABS = [
  { id: "k", label: "K01–K14", icon: Layers, num: "01" },
  { id: "markers", label: "标记统计", icon: BarChart3, num: "02" },
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
  // K 字段可能两种 shape：
  //   旧：标量字符串 / 数组 string[]
  //   新：标量 {value, source_page} / 数组 {items, source_pages}
  // helper 统一从两种 shape 提取 (value, page, items-with-pages)
  const readKField = (raw: any) => {
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
      const items = Array.isArray(raw.items) ? raw.items : null;
      const pages = Array.isArray(raw.source_pages) ? raw.source_pages : [];
      if (items) {
        return items
          .map((it: any, i: number) => ({
            text: typeof it === "string" ? it : JSON.stringify(it),
            page: typeof pages[i] === "number" && pages[i] > 0 ? pages[i] : null,
          }))
          .filter((x: { text: string }) => x.text);
      }
      const value = raw.value;
      const page = typeof raw.source_page === "number" && raw.source_page > 0 ? raw.source_page : null;
      if (value === undefined || value === null || value === "") return { kind: "empty" as const };
      if (Array.isArray(value)) {
        return {
          kind: "array" as const,
          items: value.map((it: any) => ({
            text: typeof it === "string" ? it : JSON.stringify(it),
            page: null as number | null,
          })),
        };
      }
      return { kind: "scalar" as const, text: String(value), page };
    }
    if (Array.isArray(raw)) {
      return {
        kind: "array" as const,
        items: raw
          .map((it: any) => (typeof it === "string" ? it : JSON.stringify(it)))
          .filter(Boolean)
          .map((text) => ({ text, page: null as number | null })),
      };
    }
    if (raw === undefined || raw === null || raw === "") return { kind: "empty" as const };
    return { kind: "scalar" as const, text: String(raw), page: null };
  };

  const kfields = Object.keys(data)
    .filter((k) => /^K\d{2}_/.test(k))
    .sort();
  if (kfields.length === 0) {
    return <Empty text="无 K01-K14 字段" />;
  }

  const PageBadge = ({ page }: { page: number | null }) =>
    page ? (
      <span
        className="inline-flex items-center gap-0.5 text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-[var(--color-paper-warm)] text-[var(--color-ink-mute)] border border-[var(--color-line)]/60"
        title={`来源页码 ${page}`}
      >
        <FileText className="w-2.5 h-2.5" />
        P.{page}
      </span>
    ) : null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {kfields.map((k) => {
        const field = readKField(data[k]);
        const headerPage = field.kind === "scalar" ? field.page : null;
        return (
          <div key={k} className="card-soft p-4 hover:shadow-md transition-shadow relative">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-mono text-[var(--color-primary)] font-semibold">
                {k.split("_")[0]}
              </span>
              <span className="text-[11px] text-[var(--color-ink-mute)] font-mono truncate">
                {k.split("_").slice(1).join("_")}
              </span>
              {headerPage && (
                <span className="ml-auto shrink-0">
                  <PageBadge page={headerPage} />
                </span>
              )}
            </div>
            {field.kind === "empty" && (
              <div className="text-[13.5px] text-[var(--color-ink-mute)] leading-relaxed">—</div>
            )}
            {field.kind === "scalar" && (
              <div className="text-[13.5px] text-[var(--color-ink)] leading-relaxed">
                {field.text}
              </div>
            )}
            {field.kind === "array" && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {field.items.slice(0, 6).map((it: { text: string; page: number | null }, i: number) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)] rounded-full"
                  >
                    <span className="truncate max-w-[200px]">{it.text.slice(0, 30)}</span>
                    {it.page && (
                      <span className="inline-flex items-center gap-0.5 text-[9px] font-mono text-[var(--color-ink-mute)] border-l border-[var(--color-primary-deep)]/20 pl-1">
                        P.{it.page}
                      </span>
                    )}
                  </span>
                ))}
                {field.items.length > 6 && (
                  <span className="text-[11px] text-[var(--color-ink-mute)]">+{field.items.length - 6}</span>
                )}
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
            open={g.key === "fatal_items" || g.key === "critical_items" || g.key === "high_items"}
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
              {items.map((it: any, i: number) => {
                const riskText = readRiskText(it);
                const meta = readRiskMeta(it);
                return (
                  <div key={i} className="px-4 py-3">
                    <div className="flex items-center gap-2 mb-2 text-[10px] text-[var(--color-ink-mute)] font-mono flex-wrap">
                      {it.marker && (
                        <span className="text-[var(--color-primary)] font-semibold">{it.marker}</span>
                      )}
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
                    {meta.length > 0 && (
                      <div className="mb-2 flex flex-wrap gap-1.5">
                        {meta.map((m) => (
                          <span
                            key={m.label}
                            className="inline-flex max-w-full items-center gap-1 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-0.5 text-[10px] text-[var(--color-ink-mute)]"
                            title={m.value}
                          >
                            <span className="font-medium text-[var(--color-ink-soft)]">{m.label}</span>
                            <span className="truncate max-w-[240px]">{m.value}</span>
                          </span>
                        ))}
                      </div>
                    )}
                    <pre className="text-[12px] text-[var(--color-ink)] font-mono whitespace-pre-wrap break-words leading-[1.7] bg-[var(--color-paper-warm)] p-3 rounded-lg overflow-x-auto">
                      {riskText || "未返回原文，可在“数据”页查看完整解析 JSON。"}
                    </pre>
                  </div>
                );
              })}
            </div>
          </details>
        );
      })}
    </div>
  );
}

function readRiskText(item: any): string {
  const candidates = [
    item?.raw_text,
    item?.original_text,
    item?.source_text,
    item?.condition,
    item?.requirement,
    item?.content,
    item?.text,
    item?.description,
    item?.semantic,
  ];
  for (const value of candidates) {
    const text = stringifyRiskValue(value);
    if (text) return text;
  }
  return "";
}

function readRiskMeta(item: any): Array<{ label: string; value: string }> {
  const fields: Array<[string, any]> = [
    ["映射", item?.maps_to_field ?? item?.target_field ?? item?.field],
    ["类型", item?.type ?? item?.risk_type],
    ["严重度", item?.severity ?? item?.priority],
    ["条款", item?.clause_no ?? item?.clause],
  ];
  return fields
    .map(([label, value]) => ({ label, value: stringifyRiskValue(value) }))
    .filter((entry) => entry.value);
}

function stringifyRiskValue(value: any): string {
  if (value === undefined || value === null || value === "") return "";
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
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
