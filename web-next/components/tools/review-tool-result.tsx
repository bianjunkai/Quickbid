"use client";

import { AlertTriangle, CheckCircle2, ShieldCheck, XCircle } from "lucide-react";

type CheckItem = {
  check_id?: string;
  check_name?: string;
  status?: "pass" | "warning" | "fail" | string;
  issue?: string;
  suggestion?: string;
};

type Props = {
  state: string;
  output?: {
    checks?: CheckItem[];
    summary?: {
      high?: number;
      medium?: number;
      low?: number;
    };
    error?: string;
    message?: string;
    tenderType?: string;
    tender_type?: string;
    retries?: number;
  };
  errorText?: string;
};

export function ReviewToolResult({ state, output, errorText }: Props) {
  const checks = output?.checks || [];
  const summary = output?.summary || {};
  const error = errorText || output?.error;
  const failed = summary.high ?? checks.filter((c) => c.status === "fail").length;
  const warnings = summary.medium ?? checks.filter((c) => c.status === "warning").length;
  const passed = summary.low ?? checks.filter((c) => c.status === "pass").length;
  const tenderType = output?.tenderType || output?.tender_type || "main";

  return (
    <div className="card-soft overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-paper-warm)] flex items-center gap-2">
        <ShieldCheck className="w-4 h-4 text-[var(--color-primary)] shrink-0" />
        <div className="min-w-0">
          <div className="text-[12px] font-semibold text-[var(--color-ink)]">
            {tenderType === "sub" ? "陪标终审" : "主标终审"}
          </div>
          <div className="text-[10px] text-[var(--color-ink-mute)] font-mono">
            {state}
            {typeof output?.retries === "number" && output.retries > 0 ? ` · retry ${output.retries}` : ""}
          </div>
        </div>
      </div>

      {error ? (
        <div className="px-4 py-3 bg-[var(--color-danger-bg)] border-b border-[var(--color-danger)]">
          <div className="flex items-center gap-2 text-[12px] font-semibold text-[var(--color-danger)]">
            <XCircle className="w-4 h-4 shrink-0" />
            终审未执行成功
          </div>
          <div className="mt-1 text-[11px] text-[var(--color-danger)] font-mono leading-[1.6]">
            {error}
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-3 divide-x divide-[var(--color-border)] border-b border-[var(--color-border)]">
        <ReviewStat label="失败" value={failed} tone={failed > 0 ? "danger" : "muted"} />
        <ReviewStat label="警告" value={warnings} tone={warnings > 0 ? "warning" : "muted"} />
        <ReviewStat label="通过" value={passed} tone="success" />
      </div>

      {checks.length > 0 ? (
        <div className="divide-y divide-[var(--color-border)] max-h-96 overflow-y-auto">
          {checks.map((check, idx) => (
            <ReviewCheckRow key={`${check.check_id || idx}-${idx}`} check={check} />
          ))}
        </div>
      ) : (
        <div className="px-4 py-3 text-[12px] text-[var(--color-ink-mute)]">
          暂无审查项返回。
        </div>
      )}
    </div>
  );
}

function ReviewStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "danger" | "warning" | "success" | "muted";
}) {
  const color =
    tone === "danger"
      ? "text-[var(--color-danger)]"
      : tone === "warning"
        ? "text-[var(--color-warning)]"
        : tone === "success"
          ? "text-[var(--color-success)]"
          : "text-[var(--color-ink-mute)]";
  return (
    <div className="px-4 py-3">
      <div className={`text-[18px] font-semibold tabular-nums ${color}`}>{value}</div>
      <div className="text-[10px] text-[var(--color-ink-mute)] mt-0.5">{label}</div>
    </div>
  );
}

function ReviewCheckRow({ check }: { check: CheckItem }) {
  const status = check.status || "warning";
  const Icon = status === "pass" ? CheckCircle2 : status === "fail" ? XCircle : AlertTriangle;
  const color =
    status === "pass"
      ? "text-[var(--color-success)]"
      : status === "fail"
        ? "text-[var(--color-danger)]"
        : "text-[var(--color-warning)]";

  return (
    <div className="px-4 py-3">
      <div className="flex items-start gap-2">
        <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${color}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-mono text-[var(--color-ink-mute)]">
              {check.check_id || "CHECK"}
            </span>
            <span className="text-[12px] font-semibold text-[var(--color-ink)]">
              {check.check_name || "审查项"}
            </span>
            <span className={`text-[10px] font-mono uppercase ${color}`}>
              {status}
            </span>
          </div>
          {check.issue ? (
            <div className="mt-1 text-[12px] text-[var(--color-ink-soft)] leading-[1.6]">
              {check.issue}
            </div>
          ) : null}
          {check.suggestion ? (
            <div className="mt-1 text-[11px] text-[var(--color-ink-mute)] leading-[1.6]">
              建议：{check.suggestion}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
