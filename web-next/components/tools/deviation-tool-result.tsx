"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertOctagon, ChevronDown, ClipboardCheck, Edit3, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  state: string;
  input?: { projectId?: number; tenderType?: string };
  output?: {
    business_items?: string[];
    technical_items?: string[];
    format_requirement?: string;
    message?: string;
    action_hint?: string;
  };
  errorText?: string;
};

export function DeviationToolResult({ state, input, output, errorText }: Props) {
  const [expanded, setExpanded] = useState(true);
  const router = useRouter();

  if (errorText) {
    return (
      <div className="card-soft p-4 border border-[var(--color-danger)]">
        <div className="flex items-center gap-2 mb-2">
          <AlertOctagon className="w-4 h-4 text-[var(--color-danger)]" />
          <span className="text-[12px] font-semibold text-[var(--color-danger)] uppercase tracking-wider">
            偏离表确认失败
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
            <div className="text-[12px] font-semibold text-[var(--color-ink)]">正在整理偏离表条目…</div>
            <div className="text-[11px] text-[var(--color-ink-mute)] font-mono mt-0.5">
              project=#{String(input?.projectId ?? 0).padStart(3, "0")} · {input?.tenderType ?? "main"}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (state !== "output-available" || !output) return null;

  const business = output.business_items ?? [];
  const technical = output.technical_items ?? [];

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
        <ClipboardCheck className="w-3.5 h-3.5 text-[var(--color-primary)]" />
        <span className="text-[13px] font-semibold text-[var(--color-ink)]">偏离表确认</span>
        <span className="text-[11px] text-[var(--color-ink-mute)] font-mono tabular-nums">
          · 商务 {business.length} 条 · 技术 {technical.length} 条
        </span>
        {input?.projectId && (
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation();
              router.push(`/projects/${input.projectId}?doc=deviation`);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                e.stopPropagation();
                router.push(`/projects/${input.projectId}?doc=deviation`);
              }
            }}
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1 text-[11px] font-medium text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)]"
          >
            <Edit3 className="w-3 h-3" />
            Markdown 编辑
          </span>
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4">
          <DeviationList title="商务条款偏离表" items={business} emptyText="未解析到可逐条响应的商务条款" />
          <DeviationList title="技术条款偏离表" items={technical} emptyText="未解析到可逐条响应的技术条款" />
          {output.action_hint && (
            <div className="text-[12px] text-[var(--color-ink-mute)] leading-relaxed border-t border-[var(--color-border)] pt-3">
              {output.action_hint}
              <div className="mt-1 text-[11.5px] text-[var(--color-ink-mute)]">
                确认并生成后，可在右侧「主标」顶层文件中打开「商务/技术偏离表（deviation.md）」。
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DeviationList({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: string[];
  emptyText: string;
}) {
  return (
    <div>
      <div className="text-[12px] font-semibold text-[var(--color-ink)] mb-2">{title}</div>
      {items.length === 0 ? (
        <div className="text-[12px] text-[var(--color-warning)] rounded-lg border border-[var(--color-border)] px-3 py-2">
          {emptyText}
        </div>
      ) : (
        <ol className="space-y-1.5">
          {items.map((item, index) => (
            <li
              key={`${title}-${index}-${item.slice(0, 16)}`}
              className="grid grid-cols-[32px_1fr] gap-2 rounded-lg border border-[var(--color-border)] px-3 py-2"
            >
              <span className="text-[11px] text-[var(--color-ink-mute)] font-mono tabular-nums">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="text-[12px] text-[var(--color-ink)] leading-relaxed">{item}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
