"use client";

import { useState } from "react";
import { ChevronDown, AlertOctagon, Loader2, ListTree, Pencil, AlertTriangle, XCircle } from "lucide-react";
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

const VOLUME_LABEL: Record<string, string> = {
  commercial: "商务标",
  technical: "技术标",
  price: "报价标",
  other: "其他",
};

type Subsection = { id?: string; title?: string };
type EvidenceRef = {
  page?: number | null;
  quote?: string;
  field_path?: string;
};
type Chapter = {
  id?: string;
  no?: number;
  title?: string;
  volume?: string;
  category?: string;
  subsections?: Subsection[];
  source?: string;
  requirement_refs?: EvidenceRef[];
  scoring_refs?: EvidenceRef[];
};

type ValidationResult = {
  is_valid: boolean;
  warnings: string[];
  errors: string[];
  stats?: {
    chapter_count: number;
    subsection_count: number;
    category_usage: Record<string, number>;
    scoring_coverage: number;
    scoring_items_checked?: number;
    scoring_items_missing?: number;
  };
};

export function OutlineToolResult({
  state,
  input,
  output,
  errorText,
}: {
  state: string;
  input?: { projectId?: number; tenderType?: string };
  output?: {
    outline?: Chapter[];
    message?: string;
    action_hint?: string;
    validation?: ValidationResult;
  };
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
    const validation = output.validation;
    const groups = groupByVolume(outline);

    return (
      <div className="space-y-3">
        {/* 验证结果卡片 */}
        {validation && (validation.errors.length > 0 || validation.warnings.length > 0) && (
          <ValidationCard validation={validation} />
        )}

        {/* 提纲展示 */}
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
            {validation && validation.stats && validation.stats.scoring_coverage !== undefined && (
              <span
                className={cn(
                  "text-[11px] font-mono tabular-nums",
                  validation.stats.scoring_coverage >= 0.8
                    ? "text-[var(--color-success)]"
                    : validation.stats.scoring_coverage >= 0.6
                    ? "text-[var(--color-warning)]"
                    : "text-[var(--color-danger)]"
                )}
              >
                · 评分覆盖 {Math.round(validation.stats.scoring_coverage * 100)}%
              </span>
            )}
          </button>

          {expanded && (
            <>
              <div className="border-t border-[var(--color-border)]">
                {groups.map((group) => (
                  <div key={group.volume}>
                    <div className="px-4 py-2 bg-[var(--color-paper-warm)] border-b border-[var(--color-border)] text-[11px] font-semibold text-[var(--color-ink-soft)]">
                      {VOLUME_LABEL[group.volume] ?? group.volume} · {group.items.length} 章
                    </div>
                    <ol className="divide-y divide-[var(--color-border)]">
                      {group.items.map(({ chapter, index }) => (
                        <ChapterRow key={chapter.id ?? index} chapter={chapter} index={index} />
                      ))}
                    </ol>
                  </div>
                ))}
              </div>
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
      </div>
    );
  }

  return null;
}

function groupByVolume(outline: Chapter[]) {
  const order = ["commercial", "technical", "price", "other"];
  const map = new Map<string, Array<{ chapter: Chapter; index: number }>>();
  outline.forEach((chapter, index) => {
    const volume = chapter.volume || "other";
    if (!map.has(volume)) map.set(volume, []);
    map.get(volume)!.push({ chapter, index });
  });
  return Array.from(map.entries())
    .sort((a, b) => {
      const ai = order.indexOf(a[0]);
      const bi = order.indexOf(b[0]);
      return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
    })
    .map(([volume, items]) => ({ volume, items }));
}

function ChapterRow({ chapter, index }: { chapter: Chapter; index: number }) {
  const no = chapter.no ?? index + 1;
  const cat = chapter.category ?? "";
  const catLabel = CATEGORY_LABEL[cat] ?? cat;
  const subs = chapter.subsections ?? [];
  const sourceLabel = chapter.source ? SOURCE_LABEL[chapter.source] : null;
  const requirementRef = firstRefLabel(chapter.requirement_refs);
  const scoringRef = firstRefLabel(chapter.scoring_refs);

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
          {(requirementRef || scoringRef) && (
            <div className="mt-1 flex flex-wrap gap-1.5 text-[10.5px] text-[var(--color-ink-mute)]">
              {requirementRef && (
                <span className="rounded-md bg-[var(--color-primary-bg)] px-1.5 py-0.5 text-[var(--color-primary-deep)]">
                  要求 {requirementRef}
                </span>
              )}
              {scoringRef && (
                <span className="rounded-md bg-[var(--color-warning-bg)] px-1.5 py-0.5 text-[var(--color-warning)]">
                  评分 {scoringRef}
                </span>
              )}
            </div>
          )}
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

function firstRefLabel(refs?: EvidenceRef[]) {
  const ref = refs?.find((r) => r.page || r.field_path || r.quote);
  if (!ref) return "";
  if (ref.page) return `P.${ref.page}`;
  if (ref.field_path) return ref.field_path;
  return ref.quote?.slice(0, 24) || "";
}

function ValidationCard({ validation }: { validation: ValidationResult }) {
  const { errors, warnings, is_valid, stats } = validation;
  const hasErrors = errors.length > 0;
  const hasWarnings = warnings.length > 0;

  return (
    <div
      className={cn(
        "card-soft p-4 border-l-4",
        hasErrors
          ? "border-[var(--color-danger)] bg-red-50/50"
          : "border-[var(--color-warning)] bg-yellow-50/50"
      )}
    >
      {/* 标题 */}
      <div className="flex items-start gap-2 mb-3">
        {hasErrors ? (
          <XCircle className="w-4 h-4 text-[var(--color-danger)] shrink-0 mt-0.5" />
        ) : (
          <AlertTriangle className="w-4 h-4 text-[var(--color-warning)] shrink-0 mt-0.5" />
        )}
        <div className="flex-1">
          <div className="text-[13px] font-semibold text-[var(--color-ink)] mb-0.5">
            提纲验证{hasErrors ? "失败" : "警告"}
          </div>
          {stats && (
            <div className="text-[11px] text-[var(--color-ink-mute)] font-mono">
              {stats.scoring_items_checked && stats.scoring_items_missing !== undefined && (
                <span>
                  评分项覆盖: {stats.scoring_items_checked - stats.scoring_items_missing}/
                  {stats.scoring_items_checked}
                  {stats.scoring_coverage !== undefined &&
                    ` (${Math.round(stats.scoring_coverage * 100)}%)`}
                </span>
              )}
            </div>
          )}
        </div>
        {!is_valid && (
          <span className="text-[10px] font-semibold text-[var(--color-danger)] uppercase tracking-wider px-2 py-0.5 rounded-md bg-red-100 border border-red-200">
            阻塞
          </span>
        )}
      </div>

      {/* 错误列表 */}
      {hasErrors && (
        <div className="space-y-1.5 mb-3">
          {errors.map((err, i) => (
            <div
              key={i}
              className="flex items-start gap-2 text-[12px] text-[var(--color-danger)] leading-relaxed pl-1"
            >
              <span className="shrink-0 mt-0.5">•</span>
              <span>{err}</span>
            </div>
          ))}
        </div>
      )}

      {/* 警告列表 */}
      {hasWarnings && (
        <div className="space-y-1.5">
          {warnings.map((warn, i) => (
            <div
              key={i}
              className="flex items-start gap-2 text-[12px] text-[var(--color-warning-deep)] leading-relaxed pl-1"
            >
              <span className="shrink-0 mt-0.5">•</span>
              <span>{warn}</span>
            </div>
          ))}
        </div>
      )}

      {/* 操作提示 */}
      {hasErrors && (
        <div className="mt-3 pt-3 border-t border-red-200 text-[11px] text-[var(--color-ink-soft)]">
          请修复上述错误后再继续，或说"重新生成"让 AI 重新设计提纲
        </div>
      )}
    </div>
  );
}
