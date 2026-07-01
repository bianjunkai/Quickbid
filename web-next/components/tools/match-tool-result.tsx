"use client";

import { useEffect, useState } from "react";
import { ChevronDown, AlertOctagon, Loader2, BookOpen, Check, Eye, Plus, Save, Upload } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  listMaterialOptions,
  readMaterialFile,
  updateMatchedChapter,
  uploadProjectMaterial,
  type MaterialOption,
} from "@/lib/api";

const CATEGORY_LABEL: Record<string, string> = {
  "01_公司资质": "公司资质",
  "02_业绩案例": "业绩案例",
  "03_技术方案": "技术方案",
  "04_实施方案": "实施方案",
  "05_商务文件": "商务文件",
  "06_其他": "其他",
};

const SCORE_META: Record<string, { icon: string; color: string; label: string }> = {
  高: { icon: "🟢", color: "var(--color-success)", label: "高" },
  中: { icon: "🟡", color: "var(--color-warning, #d97706)", label: "中" },
  低: { icon: "🔴", color: "var(--color-danger)", label: "低" },
};

type MatchedChapter = {
  chapter?: string;
  chapter_id?: string;
  category?: string;
  file_path?: string | null;
  material_id?: number | null;
  material_title?: string;
  match_score?: string;
  reason?: string;
  alternatives?: Array<{
    file_path?: string | null;
    material_id?: number | null;
    material_title?: string;
    match_score?: string;
  }>;
};

export function MatchToolResult({
  state,
  input,
  output,
  errorText,
}: {
  state: string;
  input?: { projectId?: number; tenderType?: string };
  output?: { chapters?: MatchedChapter[]; message?: string; action_hint?: string };
  errorText?: string;
}) {
  const [expanded, setExpanded] = useState(true);
  const [chaptersOverride, setChaptersOverride] = useState<MatchedChapter[] | null>(null);

  useEffect(() => {
    setChaptersOverride(output?.chapters ?? null);
  }, [output?.chapters]);

  if (errorText) {
    return (
      <div className="card-soft p-4 border border-[var(--color-danger)]">
        <div className="flex items-center gap-2 mb-2">
          <AlertOctagon className="w-4 h-4 text-[var(--color-danger)]" />
          <span className="text-[12px] font-semibold text-[var(--color-danger)] uppercase tracking-wider">
            材料匹配失败
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
            <div className="text-[12px] font-semibold text-[var(--color-ink)]">正在匹配材料…</div>
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
    const chapters = chaptersOverride ?? output.chapters ?? [];
    const matched = chapters.filter((c) => c.file_path || c.material_id).length;
    const empty = chapters.length > 0 && matched === 0;

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
          <BookOpen className="w-3.5 h-3.5 text-[var(--color-primary)]" />
          <span className="text-[13px] font-semibold text-[var(--color-ink)]">材料匹配</span>
          <span className="text-[11px] text-[var(--color-ink-mute)] font-mono tabular-nums">
            · {chapters.length} 章
            {empty
              ? " · ⚠️ 材料库为空"
              : matched < chapters.length
              ? ` · ${matched} 匹配 / ${chapters.length - matched} 待建`
              : " · 全部匹配"}
          </span>
        </button>

        {expanded && (
          <>
            {empty && (
              <div className="mx-4 mt-3 px-3 py-2 rounded-lg bg-[var(--color-primary-bg)] border border-[var(--color-primary-tint)] text-[12px] text-[var(--color-primary-deep)]">
                材料库为空，所有章节都标记为「需新建」。请到「材料库」上传资质、方案等可复用材料。
              </div>
            )}
            <ol className="border-t border-[var(--color-border)] divide-y divide-[var(--color-border)]">
              {chapters.map((ch, i) => (
                <ChapterMatchRow
                  key={ch.chapter_id ?? i}
                  chapter={ch}
                  index={i}
                  projectId={input?.projectId}
                  onChapterChange={(updated) => {
                    setChaptersOverride((prev) =>
                      (prev ?? chapters).map((item, idx) =>
                        (item.chapter_id && item.chapter_id === updated.chapter_id) ||
                        (!item.chapter_id && idx === i)
                          ? updated
                          : item
                      )
                    );
                  }}
                />
              ))}
            </ol>
            {output.action_hint && (
              <div className="px-4 py-2.5 bg-[var(--color-primary-bg)] border-t border-[var(--color-primary-tint)] flex items-start gap-2">
                <Check className="w-3 h-3 text-[var(--color-primary-deep)] mt-0.5 shrink-0" />
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

function ChapterMatchRow({
  chapter,
  index,
  projectId,
  onChapterChange,
}: {
  chapter: MatchedChapter;
  index: number;
  projectId?: number;
  onChapterChange: (chapter: MatchedChapter) => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedTitle, setUploadedTitle] = useState<string | null>(null);
  const [materialOpen, setMaterialOpen] = useState(false);
  const [materialContent, setMaterialContent] = useState<string | null>(null);
  const [materialLoading, setMaterialLoading] = useState(false);
  const [optionsOpen, setOptionsOpen] = useState(false);
  const [options, setOptions] = useState<MaterialOption[]>([]);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [selectedPath, setSelectedPath] = useState(chapter.file_path || "");
  const [savingMatch, setSavingMatch] = useState(false);
  const [matchMessage, setMatchMessage] = useState<string | null>(null);
  const score = chapter.match_score || "";
  const meta = SCORE_META[score] || { icon: "❓", color: "var(--color-ink-mute)", label: "?" };
  const cat = chapter.category || "";
  const catLabel = CATEGORY_LABEL[cat] || cat;
  const title = chapter.material_title || "无匹配材料";
  const alts = chapter.alternatives || [];

  useEffect(() => {
    setSelectedPath(chapter.file_path || "");
  }, [chapter.file_path]);

  const handleViewMaterial = async () => {
    if (!chapter.file_path) return;
    setMaterialOpen((open) => !open);
    if (materialContent !== null) return;
    setMaterialLoading(true);
    setUploadError(null);
    try {
      const data = await readMaterialFile(chapter.file_path);
      setMaterialContent(data.content || "");
    } catch (e: any) {
      setUploadError(e.message || "材料读取失败");
    } finally {
      setMaterialLoading(false);
    }
  };

  const handleOpenOptions = async () => {
    const nextOpen = !optionsOpen;
    setOptionsOpen(nextOpen);
    if (!nextOpen || options.length > 0) return;
    setOptionsLoading(true);
    setUploadError(null);
    try {
      const data = await listMaterialOptions({ category: chapter.category || undefined });
      setOptions(data);
    } catch (e: any) {
      setUploadError(e.message || "材料列表读取失败");
    } finally {
      setOptionsLoading(false);
    }
  };

  const handleSaveMatch = async () => {
    if (!projectId || !chapter.chapter_id) return;
    const selected = options.find((item) => item.file_path === selectedPath);
    setSavingMatch(true);
    setMatchMessage(null);
    setUploadError(null);
    try {
      const result = await updateMatchedChapter(projectId, {
        chapter_id: chapter.chapter_id,
        file_path: selectedPath || null,
        material_title: selected?.title || (selectedPath ? undefined : "无匹配材料"),
        match_score: selectedPath ? "高" : "低",
        reason: selectedPath ? "用户手动选择" : "用户标记为需新建",
      });
      onChapterChange(result.chapter);
      setMatchMessage("已保存");
      setOptionsOpen(false);
      setMaterialContent(null);
      window.dispatchEvent(new CustomEvent("quickbid:match-updated"));
    } catch (e: any) {
      setUploadError(e.message || "保存失败");
    } finally {
      setSavingMatch(false);
    }
  };

  const handleUpload = async (file: File) => {
    if (!projectId) return;
    setUploading(true);
    setUploadError(null);
    try {
      const result = await uploadProjectMaterial(projectId, {
        file,
        category: chapter.category || "06_其他",
        chapter: chapter.chapter,
      });
      setUploadedTitle(result.title);
      window.dispatchEvent(new CustomEvent("quickbid:materials-updated"));
    } catch (e: any) {
      setUploadError(e.message || "上传失败");
    } finally {
      setUploading(false);
    }
  };

  return (
    <li className="px-4 py-3 hover:bg-[var(--color-paper-warm)] transition-colors">
      <div className="flex items-start gap-3">
        <span className="shrink-0 mt-0.5 text-[13px]" aria-hidden>{meta.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[13.5px] font-semibold text-[var(--color-ink)] leading-snug">
              {chapter.chapter || `第 ${index + 1} 章`}
            </span>
            {catLabel && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-md bg-[var(--color-surface)] border border-[var(--color-border)] text-[10px] text-[var(--color-ink-soft)] font-medium">
                {catLabel}
              </span>
            )}
            <span
              className="text-[10px] font-mono font-semibold uppercase tracking-wider"
              style={{ color: meta.color }}
            >
              {meta.label}
            </span>
          </div>
          <div className="mt-1 text-[12.5px] text-[var(--color-ink-soft)] leading-relaxed">
            → <span className="font-medium">{title}</span>
          </div>
          {chapter.reason && (
            <div className="mt-0.5 text-[11.5px] text-[var(--color-ink-mute)] leading-relaxed">
              {chapter.reason}
            </div>
          )}
          {alts.length > 0 && (
            <div className="mt-1.5 pl-3 border-l-2 border-[var(--color-border)] text-[11.5px] text-[var(--color-ink-mute)]">
              备选：
              {alts.map((a, j) => (
                <span key={a.material_id ?? j} className="ml-1.5">
                  · {a.material_title}
                </span>
              ))}
            </div>
          )}
          {projectId && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleViewMaterial}
                disabled={!chapter.file_path}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[11.5px] font-medium text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] disabled:opacity-45 disabled:cursor-not-allowed"
              >
                {materialLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Eye className="w-3 h-3" />}
                查看材料
              </button>
              <button
                type="button"
                onClick={handleOpenOptions}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[11.5px] font-medium text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)]"
              >
                改匹配
              </button>
              <label className="inline-flex items-center gap-1.5 rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-[11.5px] font-medium text-[var(--color-ink-soft)] hover:border-[var(--color-primary)] hover:text-[var(--color-primary-deep)] hover:bg-[var(--color-primary-bg)] cursor-pointer transition-colors">
                {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
                {uploading ? "上传中" : "添加材料"}
                <input
                  type="file"
                  accept=".md,.txt,.docx,.pdf"
                  className="hidden"
                  disabled={uploading}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUpload(file);
                    e.currentTarget.value = "";
                  }}
                />
              </label>
              {uploadedTitle && (
                <span className="inline-flex items-center gap-1 text-[11.5px] text-[var(--color-success)]">
                  <Plus className="w-3 h-3" />
                  已归档：{uploadedTitle}
                </span>
              )}
              {uploadError && (
                <span className="text-[11.5px] text-[var(--color-danger)]">
                  {uploadError}
                </span>
              )}
              {matchMessage && (
                <span className="text-[11.5px] text-[var(--color-success)]">
                  {matchMessage}
                </span>
              )}
            </div>
          )}
          {materialOpen && (
            <div className="mt-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-sunk)] p-3">
              {materialLoading ? (
                <div className="flex items-center gap-2 text-[11.5px] text-[var(--color-ink-mute)]">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  读取材料…
                </div>
              ) : (
                <pre className="max-h-56 overflow-auto whitespace-pre-wrap text-[11.5px] leading-5 text-[var(--color-ink-soft)] font-mono">
                  {materialContent || "材料内容为空"}
                </pre>
              )}
            </div>
          )}
          {optionsOpen && (
            <div className="mt-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-sunk)] p-3 space-y-2">
              {optionsLoading ? (
                <div className="flex items-center gap-2 text-[11.5px] text-[var(--color-ink-mute)]">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  读取同分类材料…
                </div>
              ) : (
                <>
                  <select
                    value={selectedPath}
                    onChange={(e) => setSelectedPath(e.target.value)}
                    className="w-full h-8 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-[11.5px] text-[var(--color-ink)]"
                  >
                    <option value="">无匹配材料 / 需新建</option>
                    {options.map((item) => (
                      <option key={item.file_path} value={item.file_path}>
                        {item.title}
                      </option>
                    ))}
                  </select>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10.5px] text-[var(--color-ink-mute)]">
                      {catLabel || "当前分类"} · {options.length} 个可选材料
                    </span>
                    <button
                      type="button"
                      onClick={handleSaveMatch}
                      disabled={savingMatch || !chapter.chapter_id}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-ink-button)] px-2.5 py-1.5 text-[11.5px] font-semibold text-[var(--color-paper)] hover:bg-[var(--color-ink-button-soft)] disabled:opacity-50"
                    >
                      {savingMatch ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                      保存
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </li>
  );
}
