"use client";

import { AlertOctagon, Check, Download, FileText, Loader2 } from "lucide-react";

type Props = {
  state: string;
  input?: { tenderId?: number; format?: string };
  output?: {
    tenderId?: number;
    format?: string;
    export_path?: string;
    download_url?: string;
    error?: string;
    message?: string;
  };
  errorText?: string;
};

export function ExportToolResult({ state, input, output, errorText }: Props) {
  const error = errorText || output?.error;

  if (state === "input-available" || state === "input-streaming") {
    return (
      <div className="card-soft p-4">
        <div className="flex items-center gap-3">
          <Loader2 className="w-4 h-4 text-[var(--color-primary)] animate-spin" />
          <div>
            <div className="text-[12px] font-semibold text-[var(--color-ink)]">
              正在导出文件…
            </div>
            <div className="text-[11px] text-[var(--color-ink-mute)] font-mono mt-0.5">
              tender=#{input?.tenderId ?? "-"} · {input?.format ?? "word"}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card-soft p-4 border border-[var(--color-danger)]">
        <div className="flex items-center gap-2 mb-2">
          <AlertOctagon className="w-4 h-4 text-[var(--color-danger)]" />
          <span className="text-[12px] font-semibold text-[var(--color-danger)] uppercase tracking-wider">
            导出失败
          </span>
        </div>
        <div className="text-[13px] text-[var(--color-ink)] font-mono break-words">
          {error}
        </div>
      </div>
    );
  }

  if (state !== "output-available" || !output) return null;

  return (
    <div className="card-soft overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--color-border)] flex items-center gap-3">
        <FileText className="w-3.5 h-3.5 text-[var(--color-primary)]" />
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-semibold text-[var(--color-ink)]">
            导出完成
          </div>
          <div className="text-[11px] text-[var(--color-ink-mute)] font-mono truncate">
            {output.export_path}
          </div>
        </div>
        <Check className="w-4 h-4 text-[var(--color-success)] shrink-0" />
      </div>
      <div className="px-4 py-3 flex items-center gap-2">
        <span className="text-[12px] text-[var(--color-ink-soft)]">
          格式：{output.format ?? "word"}
        </span>
        {output.download_url && (
          <a
            href={output.download_url}
            className="ml-auto inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[12px] text-white bg-[var(--color-primary)] hover:bg-[var(--color-primary-deep)] transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            下载
          </a>
        )}
      </div>
    </div>
  );
}
