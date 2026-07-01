"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Calculator, FileSearch, Loader2, X } from "lucide-react";
import { calculatePrice, getPriceCalculatorDefaults } from "@/lib/api";
import { cn } from "@/lib/utils";

type Props = {
  projectId: number;
  open: boolean;
  onClose: () => void;
};

const FIELD_LABELS = {
  lowest_price: "最低报价",
  main_price: "主标报价",
  competitor_price: "竞争对手报价",
} as const;

export function PriceCalculatorDialog({ projectId, open, onClose }: Props) {
  const [values, setValues] = useState<Record<string, string>>({
    lowest_price: "",
    main_price: "",
    competitor_price: "",
  });
  const [defaults, setDefaults] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [defaultsLoading, setDefaultsLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDefaultsLoading(true);
    setError(null);
    getPriceCalculatorDefaults(projectId)
      .then(setDefaults)
      .catch((e: any) => setError(e.message || "读取价格参数失败"))
      .finally(() => setDefaultsLoading(false));
  }, [open, projectId]);

  if (!open) return null;

  const setField = (key: string, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  };

  const numberValue = (key: string) => {
    const raw = values[key].trim();
    if (!raw) return undefined;
    const n = Number(raw);
    return Number.isFinite(n) ? n : undefined;
  };

  const handleSubmit = async () => {
    setError(null);
    setResult(null);
    const required = ["lowest_price", "main_price", "competitor_price"];
    const missing = required.filter((key) => numberValue(key) === undefined);
    if (missing.length > 0) {
      setError(`请填写${missing.map((key) => FIELD_LABELS[key as keyof typeof FIELD_LABELS]).join("、")}`);
      return;
    }
    setLoading(true);
    try {
      const data = await calculatePrice(projectId, {
        lowest_price: numberValue("lowest_price")!,
        main_price: numberValue("main_price")!,
        competitor_price: numberValue("competitor_price")!,
      });
      setResult(data);
    } catch (e: any) {
      setError(e.message || "计算失败");
    } finally {
      setLoading(false);
    }
  };

  const rows = result?.rows ?? [];
  const missingDefaults = defaults?.missing ?? [];

  return (
    <div className="fixed inset-0 z-50 bg-black/20 flex items-center justify-center p-4">
      <div className="w-full max-w-5xl max-h-[calc(100vh-32px)] rounded-2xl bg-[var(--color-surface)] shadow-2xl border border-[var(--color-border)] overflow-hidden flex flex-col">
        <div className="flex items-center gap-3 px-5 py-4 border-b border-[var(--color-border)]">
          <div className="w-8 h-8 rounded-lg bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)] flex items-center justify-center">
            <Calculator className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[14px] font-semibold text-[var(--color-ink)]">价格计算器</div>
            <div className="text-[11px] text-[var(--color-ink-mute)]">最高限价、低价比例、价格分满分来自招标文件解析。</div>
          </div>
          <button
            onClick={onClose}
            className="ml-auto w-8 h-8 rounded-lg text-[var(--color-ink-mute)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] flex items-center justify-center"
            aria-label="关闭价格计算器"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[340px_1fr] overflow-y-auto">
          <div className="p-5 border-b lg:border-b-0 lg:border-r border-[var(--color-border)] space-y-4">
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-sunk)] p-3">
              <div className="mb-3 flex items-center gap-2">
                <FileSearch className="w-3.5 h-3.5 text-[var(--color-primary)]" />
                <span className="text-[12px] font-semibold text-[var(--color-ink)]">招标文件解析参数</span>
                {defaultsLoading && <Loader2 className="ml-auto w-3.5 h-3.5 animate-spin text-[var(--color-ink-mute)]" />}
              </div>
              <div className="space-y-2">
                <ParsedParam label="最高限价" value={defaults?.highest_limit_display ?? "—"} missing={hasMissing(missingDefaults, "highest_limit")} />
                <ParsedParam label="低价比例" value={defaults?.low_price_ratio_display ?? "—"} missing={hasMissing(missingDefaults, "low_price_ratio")} />
                <ParsedParam label="价格分满分" value={defaults?.price_score_max_display ?? "—"} missing={hasMissing(missingDefaults, "price_score_max")} />
              </div>
              {missingDefaults.length > 0 && (
                <div className="mt-3 rounded-lg bg-[var(--color-warning-bg)] px-3 py-2 text-[11.5px] leading-relaxed text-[var(--color-warning)]">
                  未解析到：{missingDefaults.map((m: any) => m.label).filter(Boolean).join("、")}。请先在解析报告中修正对应字段，再进行测算。
                </div>
              )}
            </div>
            <PriceInput label="最低报价（万元）" value={values.lowest_price} onChange={(v) => setField("lowest_price", v)} required />
            <PriceInput label="主标报价（万元）" value={values.main_price} onChange={(v) => setField("main_price", v)} required />
            <PriceInput label="竞争对手报价（万元）" value={values.competitor_price} onChange={(v) => setField("competitor_price", v)} required />
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading || defaultsLoading || missingDefaults.length > 0}
              className="w-full h-10 rounded-xl bg-[var(--color-ink-button)] text-[var(--color-paper)] text-[13px] font-semibold hover:bg-[var(--color-ink-button-soft)] transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              开始计算
            </button>
            {error && (
              <div className="rounded-lg bg-[var(--color-danger-bg)] text-[var(--color-danger)] px-3 py-2 text-[12px] leading-relaxed">
                {error}
              </div>
            )}
          </div>

          <div className="p-5 min-h-[420px] overflow-x-hidden">
            {!result ? (
              <div className="h-full min-h-[360px] rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface-sunk)] flex items-center justify-center px-6 text-center text-[12px] text-[var(--color-ink-mute)]">
                输入三类报价后展示价格得分、低价线和相对主标分差。
              </div>
            ) : (
              <div className="space-y-4">
                {!result.ok ? (
                  <div className="rounded-xl border border-[var(--color-warning)] bg-[var(--color-warning-bg)] px-4 py-3 text-[12px] text-[var(--color-warning)] leading-relaxed">
                    缺少解析参数：{(result.missing ?? []).map((m: any) => m.label).filter(Boolean).join("、") || "请检查解析报告"}。
                  </div>
                ) : null}
                {result.ok && (
                  <>
                <div className="grid grid-cols-2 xl:grid-cols-5 gap-2">
                  <Metric label="最高限价" value={result.highest_limit_display ?? "-"} />
                  <Metric label="低价比例" value={result.low_price_ratio_display ?? "-"} />
                  <Metric label="低价阈值" value={result.low_price_threshold_display ?? "-"} danger={result.any_low_price_risk} />
                  <Metric label="基准价" value={result.benchmark_price_display ?? "-"} />
                  <Metric label="价格分" value={`${result.price_score_max ?? "-"} 分`} />
                </div>
                {result.any_low_price_risk && (
                  <div className="flex items-start gap-2 rounded-lg bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-warning)]">
                    <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                    有报价触发异常低价线，请核对招标文件低价审核条款。
                  </div>
                )}
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[680px] text-left border-separate border-spacing-0">
                    <thead>
                      <tr className="text-[11px] text-[var(--color-ink-mute)]">
                        <th className="py-2 pr-3 font-medium">对象</th>
                        <th className="py-2 px-3 font-medium">报价</th>
                        <th className="py-2 px-3 font-medium">得分</th>
                        <th className="py-2 px-3 font-medium">相对主标</th>
                        <th className="py-2 pl-3 font-medium">低价</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row: any) => (
                        <tr key={row.key ?? row.label}>
                          <td className="py-2.5 pr-3 text-[12px] font-semibold text-[var(--color-ink)]">{row.label}</td>
                          <td className="py-2.5 px-3 text-[12px] font-mono text-[var(--color-ink)]">{row.price_display}</td>
                          <td className="py-2.5 px-3 text-[12px] font-mono text-[var(--color-ink)]">{row.score_display}</td>
                          <td className="py-2.5 px-3 text-[12px] font-mono text-[var(--color-ink)]">{formatSigned(row.score_diff_to_main)}</td>
                          <td className="py-2.5 pl-3">
                            <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium", row.triggers_low_price ? "bg-[var(--color-danger-bg)] text-[var(--color-danger)]" : "bg-[var(--color-success-bg)] text-[var(--color-success)]")}>
                              {row.triggers_low_price ? "触发" : "未触发"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="rounded-lg bg-[var(--color-surface-sunk)] border border-[var(--color-border)] px-3 py-2 text-[12px] text-[var(--color-ink-soft)] leading-relaxed">
                  {result.formula}
                </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ParsedParam({ label, value, missing = false }: { label: string; value: string; missing?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2">
      <span className="text-[11px] text-[var(--color-ink-mute)]">{label}</span>
      <span className={cn("text-[12px] font-semibold font-mono", missing ? "text-[var(--color-warning)]" : "text-[var(--color-ink)]")}>
        {missing ? "未解析到" : value}
      </span>
    </div>
  );
}

function hasMissing(missing: Array<{ field?: string }>, field: string) {
  return missing.some((item) => item.field === field);
}

function PriceInput({
  label,
  value,
  onChange,
  placeholder,
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-medium text-[var(--color-ink-mute)]">
        {label}{required ? " *" : ""}
      </span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        inputMode="decimal"
        placeholder={placeholder}
        className="w-full h-9 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-sunk)] px-3 text-[13px] text-[var(--color-ink)] outline-none focus:border-[var(--color-primary)]"
      />
    </label>
  );
}

function Metric({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-sunk)] px-3 py-2">
      <div className="text-[10.5px] text-[var(--color-ink-mute)] mb-1">{label}</div>
      <div className={cn("text-[12px] font-semibold truncate", danger ? "text-[var(--color-danger)]" : "text-[var(--color-ink)]")}>
        {value}
      </div>
    </div>
  );
}

function formatSigned(value?: number | null) {
  if (value === null || value === undefined) return "-";
  if (Math.abs(value) < 0.0001) return "0.0000";
  return `${value > 0 ? "+" : ""}${value.toFixed(4)}`;
}
