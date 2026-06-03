"use client";

import { useState } from "react";
import {
  Folder,
  FolderOpen,
  FileText,
  ChevronRight,
  ChevronLeft,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProjectDetail } from "@/lib/api";

const MAIN_BID_FOLDERS = [
  "商务文件",
  "技术方案",
  "实施计划",
  "公司资质",
  "配图附件",
];

export function FileSidebar({
  project,
  onOpenReport,
}: {
  project: ProjectDetail;
  onOpenReport?: () => void;
}) {
  const [shut, setShut] = useState(false);
  const [openFolders, setOpenFolders] = useState<Set<string>>(new Set());
  const subBids: { id: number; name: string }[] =
    (project.parsed_data?.sub_bids as any[]) || [];

  const toggleFolder = (key: string) => {
    setOpenFolders((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <aside
      className={cn(
        "relative bg-surface border-l border-border transition-all duration-200 shrink-0",
        shut ? "w-8" : "w-64"
      )}
    >
      {/* Toggle */}
      <button
        onClick={() => setShut((s) => !s)}
        title={shut ? "展开" : "收起"}
        className="absolute -left-2.5 top-1/2 -translate-y-1/2 z-10 w-5 h-5 rounded-full border border-border bg-surface text-stone flex items-center justify-center hover:bg-ink hover:text-paper hover:border-ink transition-colors"
      >
        {shut ? (
          <ChevronLeft className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
      </button>

      {shut ? null : (
        <div className="flex flex-col h-full overflow-hidden">
          {/* Header */}
          <div className="px-4 py-4 border-b border-border">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink">
              项目文件
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
            {/* Tender file */}
            {project.tender_file_path && (
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-light mb-1.5">
                  招标文件
                </div>
                <div className="flex items-center gap-2 px-2.5 py-1.5 text-xs text-ink bg-paper border border-border rounded-sm">
                  <FileText className="w-3.5 h-3.5 text-amber shrink-0" />
                  <span className="truncate" title={project.tender_file_path}>
                    {project.tender_file_path.split("/").pop()}
                  </span>
                </div>
              </div>
            )}

            {/* Parsed overview */}
            {project.parsed_data && (
              <ParsedOverview data={project.parsed_data} onOpenReport={onOpenReport} />
            )}

            {/* Main bid */}
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-light mb-1.5">
                主标
              </div>
              <div className="space-y-0.5">
                {MAIN_BID_FOLDERS.map((name) => (
                  <FolderRow
                    key={`main-${name}`}
                    name={name}
                    open={openFolders.has(`main-${name}`)}
                    onToggle={() => toggleFolder(`main-${name}`)}
                  />
                ))}
              </div>
            </div>

            {/* Sub-bids */}
            {subBids.map((sub) => (
              <div key={sub.id}>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-light mb-1.5">
                  {sub.name}
                </div>
                <div className="space-y-0.5">
                  {MAIN_BID_FOLDERS.map((name) => (
                    <FolderRow
                      key={`sub-${sub.id}-${name}`}
                      name={name}
                      open={openFolders.has(`sub-${sub.id}-${name}`)}
                      onToggle={() =>
                        toggleFolder(`sub-${sub.id}-${name}`)
                      }
                    />
                  ))}
                </div>
              </div>
            ))}

            <button
              type="button"
              className="w-full py-1.5 text-xs text-stone bg-transparent border border-dashed border-border rounded-sm hover:border-ink hover:text-ink transition-colors flex items-center justify-center gap-1"
            >
              <Plus className="w-3 h-3" />
              添加陪标
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}

function FolderRow({
  name,
  open,
  onToggle,
}: {
  name: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center gap-2 px-2 py-1 text-xs text-ink-light hover:text-ink hover:bg-paper rounded-sm transition-colors text-left"
    >
      {open ? (
        <FolderOpen className="w-3.5 h-3.5 text-amber shrink-0" />
      ) : (
        <Folder className="w-3.5 h-3.5 text-stone shrink-0" />
      )}
      <span className="truncate">{name}</span>
    </button>
  );
}

function ParsedOverview({
  data,
  onOpenReport,
}: {
  data: any;
  onOpenReport?: () => void;
}) {
  const k = (key: string) => data?.[key] ?? data?.base?.[key];
  const fields = [
    { label: "项目名称", value: k("K01_project_name") || k("project_name") },
    { label: "招标编号", value: k("K02_tender_no") || k("tender_no") },
    { label: "预算", value: k("K04_budget") || k("budget") },
  ].filter((f) => f.value);

  if (fields.length === 0) return null;

  return (
    <div className="bg-paper border border-border rounded-sm p-2.5 space-y-1.5">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-light flex items-center justify-between">
        解析概览
        {onOpenReport && (
          <button
            onClick={onOpenReport}
            className="text-amber hover:underline normal-case tracking-normal"
            title="在主区打开完整报告"
          >
            打开 →
          </button>
        )}
      </div>
      {fields.map((f) => (
        <div key={f.label} className="text-[11px] leading-relaxed">
          <span className="text-stone mr-1.5">{f.label}:</span>
          <span className="text-ink">{String(f.value).slice(0, 60)}</span>
        </div>
      ))}
    </div>
  );
}
