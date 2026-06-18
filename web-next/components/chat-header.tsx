"use client";

import { useState } from "react";
import {
  ChevronDown,
  Pencil,
  MessageSquare,
  BarChart3,
  Settings,
  Sun,
  Moon,
  Download,
  Trash2,
} from "lucide-react";
import type { ProjectDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_STATE: Record<string, "parsing" | "parsed" | "done" | "error"> = {
  parsing: "parsing",
  parsed: "parsed",
  outline_generating: "parsing",
  materials_preparing: "parsing",
  generating: "parsing",
  generated: "parsed",
  reviewing: "parsing",
  reviewed: "done",
  review_failed: "error",
  done: "done",
};

const STATUS_LABEL: Record<string, string> = {
  parsing: "解析中",
  parsed: "已解析",
  outline_generating: "提纲确认",
  materials_preparing: "材料准备",
  generating: "生成中",
  generated: "已生成",
  reviewing: "审查中",
  reviewed: "已终审",
  review_failed: "终审失败",
  done: "完成",
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
  const state = STATUS_STATE[project.status] || "parsing";
  const statusText = STATUS_LABEL[project.status] || project.status;

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
    <header className="bg-[var(--color-surface)] border-b border-[var(--color-border)]">
      {/* Utility bar — breadcrumb + tools (matches reference top bar) */}
      <div className="flex items-center gap-3 px-6 py-2.5">
        <div className="flex items-center gap-1.5 text-[12px]">
          <span className="text-[var(--color-ink-mute)]">QuickBid</span>
          <span className="text-[var(--color-ink-faint)]">/</span>
          <span className="text-[var(--color-ink-mute)]">项目</span>
          <span className="text-[var(--color-ink-faint)]">/</span>
          <span className="text-[var(--color-ink)] font-medium">
            {project.name}
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-[var(--color-ink-mute)]" />
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <IconButton label="设置" icon={<Settings className="w-3.5 h-3.5" />} />
          <IconButton label="浅色" icon={<Sun className="w-3.5 h-3.5" />} />
          <IconButton label="深色" icon={<Moon className="w-3.5 h-3.5" />} />
          <button
            aria-label="导出"
            className="ml-1.5 flex items-center gap-1.5 px-3 py-1.5 bg-[var(--color-ink-button)] text-[var(--color-paper)] rounded-lg text-[12px] font-medium hover:bg-[var(--color-ink-button-soft)] transition-colors min-h-[32px]"
          >
            <Download className="w-3.5 h-3.5" />
            <span>导出</span>
          </button>
        </div>
      </div>

      {/* Main bar — title + view tabs + actions */}
      <div className="flex items-center gap-4 px-6 py-3 border-t border-[var(--color-border)]">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5">
            <span className="pill-soft" data-state={state}>
              <span className="dot" />
              {statusText}
            </span>
            {project.tender_file_path && (
              <span className="text-[11px] text-[var(--color-ink-mute)] font-mono truncate max-w-[280px]">
                {project.tender_file_path.split("/").pop()}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-1.5">
            <h1 className="text-[20px] font-semibold text-[var(--color-ink)] leading-none tracking-tight truncate">
              {project.name}
            </h1>
            <button
              className="w-6 h-6 rounded-md text-[var(--color-ink-mute)] hover:bg-[var(--color-paper-warm)] hover:text-[var(--color-ink)] flex items-center justify-center"
              aria-label="编辑项目名"
            >
              <Pencil className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* View tabs (pill style) */}
        {canShowReport && (
          <div className="flex p-1 bg-[var(--color-paper-warm)] rounded-xl" role="tablist">
            <TabBtn
              active={view === "chat"}
              onClick={() => onViewChange("chat")}
              icon={<MessageSquare className="w-3.5 h-3.5" />}
              label="对话"
            />
            <TabBtn
              active={view === "report"}
              onClick={() => onViewChange("report")}
              icon={<BarChart3 className="w-3.5 h-3.5" />}
              label="报告"
            />
          </div>
        )}

        {/* Right actions */}
        <div className="flex items-center gap-1.5">
          {project.status === "parsing" && (
            <label className="btn-primary cursor-pointer" aria-label="上传招标文件">
              {uploading ? "上传中…" : (
                <>
                  <span>↑ 上传招标文件</span>
                </>
              )}
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
            aria-label="清空对话历史"
            className="w-9 h-9 rounded-lg text-[var(--color-ink-mute)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-bg)] flex items-center justify-center transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {err && (
        <div className="px-6 py-2 bg-[var(--color-danger-bg)] border-t border-[var(--color-danger)] text-[12px] text-[var(--color-danger)]">
          {err}
        </div>
      )}
    </header>
  );
}

function IconButton({ label, icon }: { label: string; icon: React.ReactNode }) {
  return (
    <button
      aria-label={label}
      title={label}
      className="w-8 h-8 rounded-lg text-[var(--color-ink-mute)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] flex items-center justify-center transition-colors"
    >
      {icon}
    </button>
  );
}

function TabBtn({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all min-h-[30px]",
        active
          ? "bg-[var(--color-surface)] text-[var(--color-ink)] shadow-sm"
          : "text-[var(--color-ink-mute)] hover:text-[var(--color-ink)]"
      )}
    >
      {icon}
      {label}
    </button>
  );
}
