"use client";

import { useState } from "react";
import { ChevronDown, AlertOctagon, Loader2, ListTree, Pencil } from "lucide-react";
import { cn } from "@/lib/utils";

const CATEGORY_LABEL: Record<string, string> = {
  "01_公司资质": "公司资质",
  "02_业绩案例": "业绩案例",
  "03_技术方案": "技术方案",
  "04_实施方案": "实施方案",
  "05_商务文件": "商务文件",
  "06_其他": "其他",
};

const SOURCE_LABEL: Record<string, string> = {
  k12: "K12 模板",
  scoring: "K07 评分项",
  materials: "材料库",
  llm_inferred: "AI 推断",
  fallback: "骨架",
};

type Subsection = { id?: string; title?: string };
type Chapter = {
  id?: string;
  no?: number;
  title?: string;
  category?: string;
  subsections?: Subsection[];
  source?: string;
};

export function OutlineToolResult({
  state,
  input,
  output,
  errorText,
}: {
  state: string;
  input?: { projectId?: number; tenderType?: string };
  output?: { outline?: Chapter[]; message?: string; action_hint?: string };
  errorText?: string;
}) {
  const [expanded, setExpanded] = useState(true);

  if (errorText) {
    return (
      <div className="card-soft p-4 border border-[var(--color-danger)]">
        <div className="flex items-center gap-2 mb-2">
          <AlertOctagon className="w-4 h-4 text-[var(--color-danger)]" />
          <span className="text-[12px] font-semibold text-[var(--color-danger)] uppercase tracking-wider">
            大纲生成失败
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
            <div className="text-[12px] font-semibold text-[var(--color-ink)]">正在生成章节大纲…</div>
            <div className="text-[11px] text-[var(--color-ink-mute)] font-mono mt-0.5">
              project=#{String(input?.projectId ?? 0).padStart(3, "0")} · {input?.tenderType ?? "main"}
            </div>
          </div>
        </div>
        <div className="mt-3 h-1 rounded-full bg-[var(--color-paper-warm)] overflow-hidden">
          <div className="h-full w-1/3 bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-soft)] rounded-full animate-pulse" />
        </div>
      </div>
    );
  }

  if (state === "output-available" && output) {
    const outline = output.outline ?? [];
    const total = outline.length;
    const subsTotal = outline.reduce((s, c) => s + (c.subsections?.length ?? 0), 0);

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
          <ListTree className="w-3.5 h-3.5 text-[var(--color-primary)]" />
          <span className="text-[13px] font-semibold text-[var(--color-ink)]">章节大纲</span>
          <span className="text-[11px] text-[var(--color-ink-mute)] font-mono tabular-nums">
            · {total} 章 {subsTotal > 0 && `· ${subsTotal} 小节`}
          </span>
        </button>

        {expanded && (
          <>
            <ol className="border-t border-[var(--color-border)] divide-y divide-[var(--color-border)]">
              {outline.map((ch, i) => (
                <ChapterRow key={ch.id ?? i} chapter={ch} index={i} />
              ))}
            </ol>
            {output.action_hint && (
              <div className="px-4 py-2.5 bg-[var(--color-primary-bg)] border-t border-[var(--color-primary-tint)] flex items-start gap-2">
                <Pencil className="w-3 h-3 text-[var(--color-primary-deep)] mt-0.5 shrink-0" />
                <div className="text-[12px] text-[var(--color-primary-deep)] leading-relaxed">
                  {output.action_hint}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  return null;
}

function ChapterRow({ chapter, index }: { chapter: Chapter; index: number }) {
  const no = chapter.no ?? index + 1;
  const cat = chapter.category ?? "";
  const catLabel = CATEGORY_LABEL[cat] ?? cat;
  const subs = chapter.subsections ?? [];
  const sourceLabel = chapter.source ? SOURCE_LABEL[chapter.source] : null;

  return (
    <li className="px-4 py-3 hover:bg-[var(--color-paper-warm)] transition-colors">
      <div className="flex items-start gap-3">
        <span className="shrink-0 w-6 h-6 rounded-md bg-[var(--color-paper-warm)] text-[var(--color-ink-soft)] text-[11px] font-mono font-semibold flex items-center justify-center tabular-nums mt-0.5">
          {String(no).padStart(2, "0")}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[13.5px] font-semibold text-[var(--color-ink)] leading-snug">
              {chapter.title || `第 ${no} 章`}
            </span>
            {catLabel && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-md bg-[var(--color-surface)] border border-[var(--color-border)] text-[10px] text-[var(--color-ink-soft)] font-medium">
                {catLabel}
              </span>
            )}
            {sourceLabel && (
              <span className="text-[10px] text-[var(--color-ink-mute)] font-mono">
                · {sourceLabel}
              </span>
            )}
          </div>
          {subs.length > 0 && (
            <ul className="mt-1.5 space-y-0.5 pl-3 border-l-2 border-[var(--color-border)]">
              {subs.map((s, j) => (
                <li
                  key={s.id ?? j}
                  className="text-[12px] text-[var(--color-ink-mute)] leading-relaxed pl-2"
                >
                  {s.title}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </li>
  );
}
