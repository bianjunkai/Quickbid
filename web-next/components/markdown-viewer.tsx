"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertOctagon,
  Check,
  ChevronRight,
  Copy,
  Download,
  Edit3,
  Eye,
  FileText,
  Loader2,
  Save,
  X,
} from "lucide-react";
import {
  ApiError,
  readProjectMarkdown,
  readTenderFile,
  saveProjectMarkdown,
  saveTenderFile,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Props = {
  projectId: number;
  tenderId?: number;
  filePath?: string;
  documentType?: "file" | "outline" | "deviation";
  onClose: () => void;
};

// ---- 主组件 ----
export function MarkdownViewer({
  projectId,
  tenderId,
  filePath,
  documentType = "file",
  onClose,
}: Props) {
  const [content, setContent] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [copyOk, setCopyOk] = useState(false);
  const [mode, setMode] = useState<"preview" | "edit">("preview");
  const [saving, setSaving] = useState(false);
  const [saveOk, setSaveOk] = useState(false);

  const effectivePath = filePath || `${documentType}.md`;
  const folder = effectivePath.includes("/")
    ? effectivePath.slice(0, effectivePath.lastIndexOf("/"))
    : "";
  const fileName =
    documentType === "outline"
      ? "章节大纲.md"
      : documentType === "deviation"
      ? "偏离表.md"
      : effectivePath.includes("/")
      ? effectivePath.slice(effectivePath.lastIndexOf("/") + 1)
      : effectivePath;

  useEffect(() => {
    let cancelled = false;
    setContent(null);
    setDraft("");
    setError(null);
    const reader =
      documentType === "file"
        ? tenderId
          ? readTenderFile(projectId, tenderId, effectivePath)
          : Promise.reject(new Error("未找到对应标书 (tenderId 缺失)"))
        : readProjectMarkdown(projectId, documentType);
    if (documentType === "file" && !tenderId) {
      setError("未找到对应标书 (tenderId 缺失)");
      return;
    }
    reader
      .then((text) => {
        if (!cancelled) {
          setContent(text);
          setDraft(text);
        }
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (e instanceof ApiError) setError(`${e.status} ${e.message}`);
        else if (e instanceof Error) setError(e.message);
        else setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, tenderId, effectivePath, documentType]);

  // ESC 关闭
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const handleCopy = async () => {
    if (!content) return;
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = content;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopyOk(true);
    setTimeout(() => setCopyOk(false), 1500);
  };

  const handleDownload = () => {
    if (!content) return;
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveOk(false);
    setError(null);
    try {
      if (documentType === "file") {
        if (!tenderId) throw new Error("未找到对应标书 (tenderId 缺失)");
        await saveTenderFile(projectId, tenderId, effectivePath, draft);
      } else {
        await saveProjectMarkdown(projectId, documentType, draft);
      }
      setContent(draft);
      setSaveOk(true);
      setMode("preview");
      setTimeout(() => setSaveOk(false), 1800);
    } catch (e: unknown) {
      if (e instanceof ApiError) setError(`${e.status} ${e.message}`);
      else if (e instanceof Error) setError(e.message);
      else setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="absolute inset-0 z-20 bg-[var(--color-paper)] flex flex-col">
      {/* Top bar */}
      <div className="shrink-0 px-6 py-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] flex items-center gap-3 flex-wrap">
        <FileText className="w-4 h-4 text-[var(--color-primary)] shrink-0" />
        <div className="flex items-center gap-1.5 text-[12.5px] min-w-0">
          <span className="text-[var(--color-ink-mute)] font-mono">P{String(projectId).padStart(3, "0")}</span>
          {folder && (
            <>
              <ChevronRight className="w-3 h-3 text-[var(--color-ink-mute)]" />
              <span className="text-[var(--color-ink-soft)] truncate max-w-[260px]" title={folder}>
                {prettyFolder(folder)}
              </span>
            </>
          )}
          <ChevronRight className="w-3 h-3 text-[var(--color-ink-mute)]" />
          <span className="text-[var(--color-ink)] font-semibold truncate" title={fileName}>
            {fileName}
          </span>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <button
            onClick={handleCopy}
            disabled={!content}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {copyOk ? (
              <Check className="w-3.5 h-3.5 text-[var(--color-success)]" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
            {copyOk ? "已复制" : "复制"}
          </button>
          <button
            onClick={() => setMode((m) => (m === "preview" ? "edit" : "preview"))}
            disabled={!content}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {mode === "preview" ? <Edit3 className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            {mode === "preview" ? "编辑" : "预览"}
          </button>
          <button
            onClick={handleSave}
            disabled={!content || saving || draft === content}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saveOk ? <Check className="w-3.5 h-3.5 text-[var(--color-success)]" /> : <Save className="w-3.5 h-3.5" />}
            {saving ? "保存中" : saveOk ? "已保存" : "保存"}
          </button>
          <button
            onClick={handleDownload}
            disabled={!content}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download className="w-3.5 h-3.5" />
            下载
          </button>
          <button
            onClick={onClose}
            className="ml-1 inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] transition-colors"
            aria-label="关闭查看器"
          >
            <X className="w-3.5 h-3.5" />
            关闭
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        {error ? (
          <ErrorState message={error} />
        ) : content === null ? (
          <LoadingState />
        ) : mode === "edit" ? (
          <div className="h-full p-5">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              spellCheck={false}
              className="w-full h-[calc(100vh-132px)] resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-4 font-mono text-[13px] leading-7 text-[var(--color-ink)] shadow-sm outline-none focus:border-[var(--color-primary)]"
            />
          </div>
        ) : (
          <article
            className={cn(
              "max-w-3xl mx-auto px-6 py-8",
              "prose-tender"
            )}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={mdComponents}
            >
              {content}
            </ReactMarkdown>
          </article>
        )}
      </div>
    </div>
  );
}

// ---- 子状态 ----

function LoadingState() {
  return (
    <div className="flex items-center justify-center gap-2 py-24 text-[var(--color-ink-mute)] text-[13px]">
      <Loader2 className="w-4 h-4 animate-spin" />
      加载中…
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
      <div className="card-soft p-4 border border-[var(--color-danger)]">
        <div className="flex items-center gap-2 mb-2">
          <AlertOctagon className="w-4 h-4 text-[var(--color-danger)]" />
          <span className="text-[12px] font-semibold text-[var(--color-danger)] uppercase tracking-wider">
            加载失败
          </span>
        </div>
        <div className="text-[13px] text-[var(--color-ink)] font-mono break-words">
          {message}
        </div>
      </div>
    </div>
  );
}

// ---- helpers ----

function prettyFolder(folder: string): string {
  // "01_公司资质" -> "公司资质"
  return folder
    .split("/")
    .map((seg) => {
      const i = seg.indexOf("_");
      return i >= 0 ? seg.slice(i + 1) : seg;
    })
    .join(" / ");
}

// ---- Markdown 自定义组件（暖色编辑风） ----

const mdComponents = {
  h1: (p: any) => (
    <h1
      className="text-[24px] font-semibold text-[var(--color-ink)] leading-tight mt-2 mb-4 pb-2 border-b border-[var(--color-border)]"
      {...p}
    />
  ),
  h2: (p: any) => (
    <h2
      className="text-[18px] font-semibold text-[var(--color-ink)] leading-snug mt-7 mb-3 pb-1.5 border-b border-[var(--color-border)]"
      {...p}
    />
  ),
  h3: (p: any) => (
    <h3
      className="text-[15px] font-semibold text-[var(--color-ink)] leading-snug mt-5 mb-2"
      {...p}
    />
  ),
  h4: (p: any) => (
    <h4
      className="text-[13.5px] font-semibold text-[var(--color-ink-soft)] mt-4 mb-1.5"
      {...p}
    />
  ),
  p: (p: any) => (
    <p
      className="text-[14px] leading-[1.85] text-[var(--color-ink-soft)] my-3"
      {...p}
    />
  ),
  ul: (p: any) => (
    <ul
      className="list-disc pl-6 my-3 text-[14px] text-[var(--color-ink-soft)] space-y-1"
      {...p}
    />
  ),
  ol: (p: any) => (
    <ol
      className="list-decimal pl-6 my-3 text-[14px] text-[var(--color-ink-soft)] space-y-1"
      {...p}
    />
  ),
  li: (p: any) => <li className="leading-[1.75]" {...p} />,
  blockquote: (p: any) => (
    <blockquote
      className="border-l-[3px] border-[var(--color-primary-tint)] pl-4 my-3 py-1 text-[var(--color-ink-mute)] italic bg-[var(--color-primary-bg)]/40 rounded-r-md"
      {...p}
    />
  ),
  code: (p: any) => (
    <code
      className="px-1.5 py-0.5 rounded bg-[var(--color-paper-warm)] text-[12.5px] font-mono text-[var(--color-ink)] border border-[var(--color-border)]"
      {...p}
    />
  ),
  pre: (p: any) => (
    <pre
      className="p-3 rounded-lg bg-[var(--color-paper-warm)] text-[12.5px] font-mono overflow-x-auto my-3 border border-[var(--color-border)]"
      {...p}
    />
  ),
  table: (p: any) => (
    <div className="my-4 overflow-x-auto">
      <table
        className="border-collapse text-[13px] w-full"
        {...p}
      />
    </div>
  ),
  thead: (p: any) => (
    <thead className="bg-[var(--color-paper-warm)]" {...p} />
  ),
  th: (p: any) => (
    <th
      className="border border-[var(--color-border)] px-3 py-2 text-left font-semibold text-[var(--color-ink)]"
      {...p}
    />
  ),
  td: (p: any) => (
    <td
      className="border border-[var(--color-border)] px-3 py-2 text-[var(--color-ink-soft)]"
      {...p}
    />
  ),
  hr: (p: any) => (
    <hr className="my-6 border-t border-[var(--color-border)]" {...p} />
  ),
  a: (p: any) => (
    <a
      className="text-[var(--color-primary-deep)] underline decoration-[var(--color-primary-tint)] underline-offset-2 hover:decoration-[var(--color-primary)]"
      target="_blank"
      rel="noreferrer"
      {...p}
    />
  ),
  strong: (p: any) => (
    <strong className="font-semibold text-[var(--color-ink)]" {...p} />
  ),
};
