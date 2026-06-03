"use client";

import { useState } from "react";
import { BarChart3, MessageSquare, Trash2 } from "lucide-react";
import type { ProjectDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  parsing: { label: "解析中", color: "bg-amber-light text-amber" },
  parsed: { label: "已解析", color: "bg-success-light text-success" },
  materials_preparing: { label: "材料准备中", color: "bg-amber-light text-amber" },
  draft_ready: { label: "草稿就绪", color: "bg-success-light text-success" },
  reviewing: { label: "审查中", color: "bg-amber-light text-amber" },
  done: { label: "完成", color: "bg-success-light text-success" },
};

export function ChatHeader({
  project,
  onUpload,
  view,
  onViewChange,
  canShowReport,
  onClearHistory,
}: {
  project: ProjectDetail;
  onUpload: (file: File) => Promise<void>;
  view: "chat" | "report";
  onViewChange: (v: "chat" | "report") => void;
  canShowReport: boolean;
  onClearHistory: () => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const status =
    STATUS_LABELS[project.status] || {
      label: project.status,
      color: "bg-stone/20 text-stone",
    };

  const handleFile = async (file: File) => {
    setUploading(true);
    setErr(null);
    try {
      await onUpload(file);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <header className="border-b border-border bg-surface px-8 py-3 flex items-center gap-4">
      <div className="flex-1 min-w-0">
        <h1 className="font-display text-xl text-ink truncate">
          {project.name}
        </h1>
        <div className="flex items-center gap-2 mt-0.5">
          <span
            className={cn(
              "text-[9px] px-1.5 py-0.5 rounded-sm uppercase tracking-wider",
              status.color
            )}
          >
            {status.label}
          </span>
          {project.tender_file_path && (
            <span className="text-[10px] text-stone truncate">
              {project.tender_file_path.split("/").pop()}
            </span>
          )}
        </div>
      </div>

      {/* 视图切换 + 工具按钮 */}
      <div className="flex items-center gap-1">
        {canShowReport && (
          <div className="flex border border-border rounded-sm overflow-hidden mr-2">
            <button
              onClick={() => onViewChange("chat")}
              className={cn(
                "px-2.5 py-1 text-[11px] flex items-center gap-1",
                view === "chat"
                  ? "bg-ink text-paper"
                  : "bg-surface text-ink-light hover:text-ink"
              )}
              title="对话视图"
            >
              <MessageSquare className="w-3 h-3" />
              对话
            </button>
            <button
              onClick={() => onViewChange("report")}
              className={cn(
                "px-2.5 py-1 text-[11px] flex items-center gap-1 border-l border-border",
                view === "report"
                  ? "bg-ink text-paper"
                  : "bg-surface text-ink-light hover:text-ink"
              )}
              title="查看解析报告"
            >
              <BarChart3 className="w-3 h-3" />
              报告
            </button>
          </div>
        )}

        {project.status === "parsing" && (
          <label className="px-3 py-1.5 text-xs bg-ink text-paper rounded-sm cursor-pointer hover:bg-ink-light">
            {uploading ? "上传中…" : "上传文件"}
            <input
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              disabled={uploading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
              }}
            />
          </label>
        )}

        <button
          onClick={onClearHistory}
          title="清空对话历史"
          className="p-1.5 text-stone hover:text-danger rounded-sm"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {err && <span className="text-xs text-danger">{err}</span>}
    </header>
  );
}
