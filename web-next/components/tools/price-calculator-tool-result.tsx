"use client";

import { useState } from "react";
import { AlertOctagon, AlertTriangle, Calculator, ChevronDown, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type PriceRow = {
  key?: string;
  label?: string;
  price_display?: string;
  score_display?: string;
  score_diff_to_main?: number | null;
  price_diff_to_main?: number | null;
  triggers_low_price?: boolean;
};

type Props = {
  state: string;
  input?: { projectId?: number };
  output?: {
    ok?: boolean;
    message?: string;
    method?: string;
    formula?: string;
    price_score_max?: number;
    highest_limit_display?: string;
    low_price_ratio_display?: string;
    low_price_threshold_display?: string;
    benchmark_price_display?: string;
    rows?: PriceRow[];
    pairwise_score_diff?: Record<string, number>;
    any_low_price_risk?: boolean;
    missing?: Array<{ field?: string; label?: string }>;
    action_hint?: string;
  };
  errorText?: string;
};

export function PriceCalculatorToolResult({ state, input, output, errorText }: Props) {
  const [expanded, setExpanded] = useState(true);

  if (errorText) {
    return (
      <div className="card-soft p-4 border border-[var(--color-danger)]">
        <div className="flex items-center gap-2 mb-2">
          <AlertOctagon className="w-4 h-4 text-[var(--color-danger)]" />
          <span className="text-[12px] font-semibold text-[var(--color-danger)] uppercase tracking-wider">
            价格测算失败
          </span>
        </div>
        <div className="text-[13px] text-[var(--color-ink)] font-mono">{errorText}</div>
      </div>
    );
  }

  if (state === "input-available" || state === "input-streaming") {
    return (
      <div className="card-soft p-4">
        <div className="flex items-center gap-3">
          <Loader2 className="w-4 h-4 text-[var(--color-primary)] animate-spin" />
          <div className="flex-1">
            <div className="text-[12px] font-semibold text-[var(--color-ink)]">正在测算价格得分…</div>
            <div className="text-[11px] text-[var(--color-ink-mute)] font-mono mt-0.5">
              project=#{String(input?.projectId ?? 0).padStart(3, "0")}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (state !== "output-available" || !output) return null;

  const rows = output.rows ?? [];
  const hasRisk = Boolean(output.any_low_price_risk);

  return (
    <div className="card-soft overflow-hidden">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[var(--color-paper-warm)] transition-colors"
        aria-expanded={expanded}
      >
        <ChevronDown
          className={cn(
            "w-3.5 h-3.5 text-[var(--color-ink-mute)] transition-transform",
            !expanded && "-rotate-90"
          )}
        />
        <Calculator className="w-3.5 h-3.5 text-[var(--color-primary)]" />
        <span className="text-[13px] font-semibold text-[var(--color-ink)]">价格测算</span>
        <span className="text-[11px] text-[var(--color-ink-mute)] font-mono tabular-nums">
          · {output.price_score_max ?? "—"} 分 · 低价线 {output.low_price_ratio_display ?? "—"}
        </span>
        {hasRisk && <AlertTriangle className="ml-auto w-3.5 h-3.5 text-[var(--color-warning)]" />}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4">
          {!output.ok ? (
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-paper-warm)] px-3 py-2">
              <div className="text-[12px] font-semibold text-[var(--color-ink)] mb-1">缺少参数</div>
              <div className="text-[12px] text-[var(--color-ink-mute)] leading-relaxed">
                {(output.missing ?? []).map((m) => m.label).filter(Boolean).join("、") || "请补充报价和评分参数"}
              </div>
              {output.action_hint && (
                <div className="mt-2 text-[12px] text-[var(--color-primary-deep)] leading-relaxed">
                  {output.action_hint}
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <Metric label="最高限价" value={output.highest_limit_display ?? "—"} />
                <Metric label="低价阈值" value={output.low_price_threshold_display ?? "—"} danger={hasRisk} />
                <Metric label="评标基准价" value={output.benchmark_price_display ?? "—"} />
                <Metric label="计算办法" value={output.method ?? "—"} />
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[620px] text-left border-separate border-spacing-0">
                  <thead>
                    <tr className="text-[11px] text-[var(--color-ink-mute)]">
                      <th className="py-2 pr-3 font-medium">对象</th>
                      <th className="py-2 px-3 font-medium">报价</th>
                      <th className="py-2 px-3 font-medium">价格得分</th>
                      <th className="py-2 px-3 font-medium">相对主标分差</th>
                      <th className="py-2 pl-3 font-medium">异常低价</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.key ?? row.label} className="border-t border-[var(--color-border)]">
                        <td className="py-2.5 pr-3 text-[12px] font-semibold text-[var(--color-ink)]">{row.label}</td>
                        <td className="py-2.5 px-3 text-[12px] text-[var(--color-ink)] font-mono">{row.price_display}</td>
                        <td className="py-2.5 px-3 text-[12px] text-[var(--color-ink)] font-mono">{row.score_display}</td>
                        <td className="py-2.5 px-3 text-[12px] font-mono text-[var(--color-ink)]">
                          {formatSigned(row.score_diff_to_main)}
                        </td>
                        <td className="py-2.5 pl-3">
                          <span
                            className={cn(
                              "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium",
                              row.triggers_low_price
                                ? "bg-[var(--color-danger-bg)] text-[var(--color-danger)]"
                                : "bg-[var(--color-success-bg)] text-[var(--color-success)]"
                            )}
                          >
                            {row.triggers_low_price ? "触发" : "未触发"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-paper-warm)] px-3 py-2">
                <div className="text-[11px] font-semibold text-[var(--color-ink-mute)] mb-1">公式</div>
                <div className="text-[12px] text-[var(--color-ink)] leading-relaxed">{output.formula}</div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-paper-warm)] px-3 py-2">
      <div className="text-[10.5px] text-[var(--color-ink-mute)] mb-1">{label}</div>
      <div className={cn("text-[12px] font-semibold truncate", danger ? "text-[var(--color-danger)]" : "text-[var(--color-ink)]")}>
        {value}
      </div>
    </div>
  );
}

function formatSigned(value?: number | null) {
  if (value === null || value === undefined) return "—";
  if (Math.abs(value) < 0.0001) return "0.0000";
  return `${value > 0 ? "+" : ""}${value.toFixed(4)}`;
}
