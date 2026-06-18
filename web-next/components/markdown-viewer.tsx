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
  FileText,
  Loader2,
  X,
} from "lucide-react";
import { readTenderFile, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

type Props = {
  projectId: number;
  tenderId?: number;
  filePath: string;
  onClose: () => void;
};

// ---- 主组件 ----
export function MarkdownViewer({
  projectId,
  tenderId,
  filePath,
  onClose,
}: Props) {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copyOk, setCopyOk] = useState(false);

  const folder = filePath.includes("/")
    ? filePath.slice(0, filePath.lastIndexOf("/"))
    : "";
  const fileName = filePath.includes("/")
    ? filePath.slice(filePath.lastIndexOf("/") + 1)
    : filePath;

  useEffect(() => {
    let cancelled = false;
    setContent(null);
    setError(null);
    if (!tenderId) {
      setError("未找到对应标书 (tenderId 缺失)");
      return;
    }
    readTenderFile(projectId, tenderId, filePath)
      .then((text) => {
        if (!cancelled) setContent(text);
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
  }, [projectId, tenderId, filePath]);

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
