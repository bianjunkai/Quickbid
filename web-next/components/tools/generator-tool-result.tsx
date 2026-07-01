"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  AlertOctagon,
  Check,
  Copy,
  Download,
  FileText,
  Folder,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { normalizeMaybeScoringTitle } from "./scoring-labels";

// ---- 类型 ----
type GeneratedChapter = {
  chapter_id?: string;
  no?: number;
  volume_no?: number;
  title?: string;
  volume?: string;
  category?: string;
  subsections?: Array<{ id?: string; title?: string }>;
  content?: string;
  file_path?: string | null;
  material_title?: string;
  match_score?: string;
  error?: string;
};

type OutlineItem = {
  id?: string;
  no?: number;
  title?: string;
  category?: string;
  subsections?: Array<{ id?: string; title?: string }>;
};

type Props = {
  state: string;
  input?: { projectId?: number; tenderType?: string };
  output?: {
    // 状态机路径
    tenderId?: number;
    draft_path?: string;
    draft_chapters?: GeneratedChapter[];
    draft_preview?: string;
    errors?: string[];
    failed?: boolean;
    outline?: OutlineItem[];
    // 一次性路径
    draft?: {
      content?: string;
      chapters?: GeneratedChapter[];
      errors?: string[];
      outline?: OutlineItem[];
    };
    message?: string;
    action_hint?: string;
  };
  errorText?: string;
};

// ---- 主体 ----
export function GeneratorToolResult({
  state,
  input,
  output,
  errorText,
}: Props) {
  // 统一两种 payload 形态
  const chapters: GeneratedChapter[] = useMemo(() => {
    return withVolumeNumbers(
      output?.draft_chapters ??
      output?.draft?.chapters ??
      []
    );
  }, [output]);

  const outline: OutlineItem[] = useMemo(() => {
    return output?.outline ?? output?.draft?.outline ?? [];
  }, [output]);

  const errors: string[] = useMemo(() => {
    return (
      output?.errors ??
      output?.draft?.errors ??
      chapters.filter((c) => c.error).map((c) => `${c.title}: ${c.error}`) ??
      []
    );
  }, [chapters, output]);

  const draftPath = output?.draft_path;
  const projectId = input?.projectId;
  const placeholderCount = chapters.filter((c) =>
    (c.content || "").includes("[待补充")
  ).length;

  // ---- 错误态 ----
  if (errorText) {
    return (
      <div className="card-soft p-4 border border-[var(--color-danger)]">
        <div className="flex items-center gap-2 mb-2">
          <AlertOctagon className="w-4 h-4 text-[var(--color-danger)]" />
          <span className="text-[12px] font-semibold text-[var(--color-danger)] uppercase tracking-wider">
            主标生成失败
          </span>
        </div>
        <div className="text-[13px] text-[var(--color-ink)] font-mono">
          {errorText}
        </div>
      </div>
    );
  }

  // ---- 流式 ----
  if (state === "input-available" || state === "input-streaming") {
    return (
      <div className="card-soft p-4">
        <div className="flex items-center gap-3">
          <Loader2 className="w-4 h-4 text-[var(--color-primary)] animate-spin" />
          <div className="flex-1">
            <div className="text-[12px] font-semibold text-[var(--color-ink)]">
              正在生成主标…
            </div>
            <div className="text-[11px] text-[var(--color-ink-mute)] font-mono mt-0.5">
              project=#{String(projectId ?? 0).padStart(3, "0")} ·{" "}
              {input?.tenderType ?? "main"}
            </div>
          </div>
        </div>
        <div className="mt-3 h-1 rounded-full bg-[var(--color-paper-warm)] overflow-hidden">
          <div className="h-full w-1/3 bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-soft)] rounded-full animate-pulse" />
        </div>
      </div>
    );
  }

  // ---- 完成态 ----
  if (state === "output-available" && output) {
    return (
      <div className="card-soft overflow-hidden">
        <Header
          chaptersCount={chapters.length}
          errorsCount={errors.length}
          placeholderCount={placeholderCount}
          onCopyAll={() => copyAllChapters(chapters)}
          onDownload={() =>
            downloadAllChapters(chapters, projectId ?? 0, draftPath)
          }
          draftPath={draftPath}
        />
        {chapters.length > 0 && (
          <FileCategorizationPreview chapters={chapters} outline={outline} />
        )}
        {errors.length > 0 && <ErrorBanner errors={errors} />}
        {draftPath && (
          <div className="px-4 py-2.5 bg-[var(--color-primary-bg)] border-t border-[var(--color-primary-tint)] flex items-start gap-2">
            <Check className="w-3 h-3 text-[var(--color-primary-deep)] mt-0.5 shrink-0" />
            <div className="text-[12px] text-[var(--color-primary-deep)] leading-relaxed">
              → 已归档到右侧项目文件面板。商务/技术偏离表在「商务/技术偏离表（deviation.md）」中，点击可全屏查看。
            </div>
          </div>
        )}
      </div>
    );
  }

  return null;
}

// ---- 子组件 ----

function Header({
  chaptersCount,
  errorsCount,
  placeholderCount,
  onCopyAll,
  onDownload,
  draftPath,
}: {
  chaptersCount: number;
  errorsCount: number;
  placeholderCount: number;
  onCopyAll: () => void;
  onDownload: () => void;
  draftPath?: string;
}) {
  const [copyOk, setCopyOk] = useState(false);
  const handleCopy = async () => {
    onCopyAll();
    setCopyOk(true);
    setTimeout(() => setCopyOk(false), 1500);
  };
  return (
    <div className="px-4 py-3 border-b border-[var(--color-border)]">
      <div className="flex items-center gap-3 flex-wrap">
        <FileText className="w-3.5 h-3.5 text-[var(--color-primary)]" />
        <span className="text-[13px] font-semibold text-[var(--color-ink)]">
          主标生成
        </span>
        <span className="text-[11px] text-[var(--color-ink-mute)] font-mono tabular-nums">
          已生成 {chaptersCount} 个章节文件
          {errorsCount > 0 && ` · ${errorsCount} 个章节生成失败`}
          {placeholderCount > 0 && ` · ${placeholderCount} 个章节含待补充内容`}
        </span>
        <div className="ml-auto flex items-center gap-1.5">
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] transition-colors"
            aria-label="复制全部 Markdown"
          >
            {copyOk ? (
              <Check className="w-3 h-3 text-[var(--color-success)]" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
            {copyOk ? "已复制" : "复制全部"}
          </button>
          <button
            onClick={onDownload}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] transition-colors"
            aria-label="下载 draft.md"
          >
            <Download className="w-3 h-3" />
            下载 Markdown
          </button>
        </div>
      </div>
      {draftPath && (
        <div className="mt-2 rounded-lg bg-[var(--color-surface-sunk)] border border-[var(--color-border)] px-3 py-2 text-[11px] text-[var(--color-ink-mute)] font-mono break-all">
          主标汇总文件：{draftPath}
        </div>
      )}
    </div>
  );
}

function FileCategorizationPreview({
  chapters,
  outline,
}: {
  chapters: GeneratedChapter[];
  outline: OutlineItem[];
}) {
  // 按 category 聚合章节
  const groups = useMemo(() => groupByCategory(chapters), [chapters]);
  if (groups.length === 0) return null;
  return (
    <ul className="border-t border-[var(--color-border)] divide-y divide-[var(--color-border)]">
      {groups.map((g) => (
        <li key={g.category} className="px-4 py-2.5">
          <div className="flex items-center gap-2 mb-1.5">
            <Folder className="w-3 h-3 text-[var(--color-primary)]" />
            <span className="text-[12px] font-semibold text-[var(--color-ink)]">
              {g.label}
            </span>
            <span className="text-[10px] text-[var(--color-ink-mute)] font-mono">
              · {g.category}
            </span>
            <span className="ml-auto text-[10px] text-[var(--color-ink-mute)] font-mono tabular-nums">
              {g.chapters.length} 个章节文件
            </span>
          </div>
          <ol className="ml-5 space-y-2">
            {g.chapters.map((ch, i) => (
              <li
                key={ch.chapter_id ?? i}
                className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-sunk)] px-3 py-2 text-[12px] text-[var(--color-ink-soft)] leading-relaxed"
              >
                <div className="flex items-start gap-2">
                  <span className="mt-0.5 text-[var(--color-ink-mute)] font-mono tabular-nums w-7 shrink-0">
                    {String(displayChapterNo(ch, i)).padStart(2, "0")}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-semibold text-[var(--color-ink)]">
                        {normalizeMaybeScoringTitle(ch.title || "未命名章节")}
                      </span>
                      <InfoPill>卷别：{volumeLabel(ch.volume)}</InfoPill>
                      <InfoPill>卷内序号：第 {displayChapterNo(ch, i)} 章</InfoPill>
                      <InfoPill>材料分类：{prettyCategory(ch.category || "06_其他")}</InfoPill>
                      {ch.chapter_id && <InfoPill>大纲节点：{ch.chapter_id}</InfoPill>}
                      {ch.match_score && <InfoPill>材料匹配质量：{ch.match_score}</InfoPill>}
                      {chapterState(ch) && (
                        <span className={cn(
                          "inline-flex rounded-md px-1.5 py-0.5 text-[10.5px] font-medium",
                          ch.error
                            ? "bg-[var(--color-danger-bg)] text-[var(--color-danger)]"
                            : "bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)]"
                        )}>
                          {chapterState(ch)}
                        </span>
                      )}
                    </div>
                    {ch.material_title && (
                      <div className="mt-1 text-[11.5px] text-[var(--color-ink-soft)]">
                        已匹配材料名称：{ch.material_title}
                      </div>
                    )}
                    {ch.file_path && (
                      <div className="mt-1 text-[11px] text-[var(--color-ink-mute)] font-mono break-all">
                        已匹配材料路径：{ch.file_path}
                      </div>
                    )}
                    {ch.subsections && ch.subsections.length > 0 && (
                      <div className="mt-1 text-[11.5px] text-[var(--color-ink-mute)]">
                        章节小节：{ch.subsections.map((s) => normalizeMaybeScoringTitle(s.title || "")).filter(Boolean).join(" / ")}
                      </div>
                    )}
                    {ch.error && (
                      <div className="mt-1 text-[11.5px] text-[var(--color-danger)] break-words">
                        生成错误：{ch.error}
                      </div>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </li>
      ))}
    </ul>
  );
}

function ErrorBanner({ errors }: { errors: string[] }) {
  return (
    <div className="mx-4 my-3 px-3 py-2 rounded-lg bg-[var(--color-danger)]/8 border border-[var(--color-danger)]/30 text-[12px] text-[var(--color-danger)] leading-relaxed">
      <div className="font-semibold mb-1">⚠️ {errors.length} 章生成失败</div>
      <ul className="space-y-0.5 text-[11.5px]">
        {errors.slice(0, 3).map((e, i) => (
          <li key={i} className="truncate">
            · {e}
          </li>
        ))}
        {errors.length > 3 && <li>· ...还有 {errors.length - 3} 项</li>}
      </ul>
    </div>
  );
}

// ---- helpers ----

function groupByCategory(chapters: GeneratedChapter[]): Array<{
  category: string;
  label: string;
  chapters: GeneratedChapter[];
}> {
  const map = new Map<string, GeneratedChapter[]>();
  for (const ch of chapters) {
    const cat = ch.category || "06_其他";
    if (!map.has(cat)) map.set(cat, []);
    map.get(cat)!.push(ch);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([category, list]) => ({
      category,
      label: prettyCategory(category),
      chapters: list.sort((a, b) => {
        const av = a.volume === "technical" ? 1 : 0;
        const bv = b.volume === "technical" ? 1 : 0;
        if (av !== bv) return av - bv;
        return (a.volume_no ?? a.no ?? 0) - (b.volume_no ?? b.no ?? 0);
      }),
    }));
}

function prettyCategory(cat: string): string {
  // "01_公司资质" -> "公司资质"
  const idx = cat.indexOf("_");
  return idx >= 0 ? cat.slice(idx + 1) : cat;
}

function volumeLabel(volume?: string): string {
  return volume === "technical" ? "技术文件" : "商务文件";
}

function InfoPill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-1.5 py-0.5 text-[10.5px] text-[var(--color-ink-mute)]">
      {children}
    </span>
  );
}

function chapterState(chapter: GeneratedChapter): string {
  if (chapter.error) return "生成失败";
  if ((chapter.content || "").includes("[待补充")) return "含待补充占位";
  return "";
}

function fullDraftMarkdown(chapters: GeneratedChapter[]): string {
  // 复刻 GeneratorAgent._assemble_markdown 的最简版本（不依赖 K 字段）
  const parts: string[] = ["# 投标文件（主标）", "", "## 目录", ""];
  const groups = groupByVolume(chapters);
  for (const group of groups) {
    parts.push(`### ${group.label}`, "");
    group.chapters.forEach((ch, i) => {
      parts.push(`- 第${displayChapterNo(ch, i)}章 ${ch.title || ""}`);
    });
    parts.push("");
  }
  parts.push("", "---", "");
  for (const group of groups) {
    parts.push(`## ${group.label}`, "");
    for (const ch of group.chapters) {
      parts.push((ch.content || "").trim());
      parts.push("", "---", "");
    }
  }
  return parts.join("\n");
}

function displayChapterNo(chapter: GeneratedChapter, index: number): number {
  return chapter.volume_no ?? chapter.no ?? index + 1;
}

function withVolumeNumbers(chapters: GeneratedChapter[]): GeneratedChapter[] {
  const counters = { commercial: 0, technical: 0 };
  return chapters.map((chapter) => {
    const volume = chapter.volume === "technical" ? "technical" : "commercial";
    counters[volume] += 1;
    return {
      ...chapter,
      volume,
      volume_no: chapter.volume_no ?? counters[volume],
    };
  });
}

function groupByVolume(chapters: GeneratedChapter[]): Array<{
  volume: "commercial" | "technical";
  label: string;
  chapters: GeneratedChapter[];
}> {
  const grouped: Record<"commercial" | "technical", GeneratedChapter[]> = {
    commercial: [],
    technical: [],
  };
  for (const ch of chapters) {
    const volume = ch.volume === "technical" ? "technical" : "commercial";
    grouped[volume].push(ch);
  }
  return (["commercial", "technical"] as const)
    .filter((volume) => grouped[volume].length > 0)
    .map((volume) => ({
      volume,
      label: volume === "technical" ? "技术文件" : "商务文件",
      chapters: grouped[volume].map((ch, i) => ({
        ...ch,
        volume_no: ch.volume_no ?? i + 1,
      })),
    }));
}

async function copyAllChapters(chapters: GeneratedChapter[]) {
  if (chapters.length === 0) return;
  const md = fullDraftMarkdown(chapters);
  try {
    await navigator.clipboard.writeText(md);
  } catch {
    // 降级：选中文本让用户手动复制
    const ta = document.createElement("textarea");
    ta.value = md;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  }
}

function downloadAllChapters(
  chapters: GeneratedChapter[],
  projectId: number,
  draftPath?: string
) {
  if (chapters.length === 0 && !draftPath) return;
  const md = fullDraftMarkdown(chapters);
  const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `tender_main_p${projectId || "x"}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
