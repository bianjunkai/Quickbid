"use client";

import { useState } from "react";
import {
  Folder,
  FolderOpen,
  FileText,
  ChevronLeft,
  ChevronRight,
  Plus,
  ExternalLink,
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
        "relative bg-[var(--color-surface)] border-l border-[var(--color-border)] transition-all duration-200 shrink-0 flex flex-col h-full",
        shut ? "w-10" : "w-72"
      )}
      aria-label="项目文件"
    >
      {/* Toggle */}
      <button
        onClick={() => setShut((s) => !s)}
        aria-label={shut ? "展开文件栏" : "收起文件栏"}
        aria-expanded={!shut}
        className="absolute -left-3 top-6 z-10 w-6 h-6 bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-ink-mute)] rounded-md flex items-center justify-center hover:bg-[var(--color-ink)] hover:text-[var(--color-paper)] hover:border-[var(--color-ink)] transition-colors shadow-sm"
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
          <div className="px-4 pt-4 pb-3">
            <h3 className="text-[11px] font-medium text-[var(--color-ink-mute)] uppercase tracking-wider">
              项目文件
            </h3>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-4">
            {/* Tender file */}
            {project.tender_file_path && (
              <div>
                <div className="section-label">
                  <span>招标文件</span>
                  <span className="count">01</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-2 bg-[var(--color-surface-sunk)] border border-[var(--color-border)] rounded-xl">
                  <div className="w-7 h-7 rounded-md bg-white border border-[var(--color-border)] flex items-center justify-center shrink-0">
                    <FileText className="w-3.5 h-3.5 text-[var(--color-primary)]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[12px] text-[var(--color-ink)] truncate font-medium" title={project.tender_file_path}>
                      {project.tender_file_path.split("/").pop()}
                    </div>
                    <div className="text-[10px] text-[var(--color-ink-mute)] font-mono mt-0.5">PDF · TENDER</div>
                  </div>
                </div>
              </div>
            )}

            {/* Parsed overview */}
            {project.parsed_data && (
              <div>
                <div className="section-label">
                  <span>解析概览</span>
                  <span className="count">02</span>
                </div>
                <ParsedOverview data={project.parsed_data} onOpenReport={onOpenReport} />
              </div>
            )}

            {/* Main bid */}
            <div>
              <div className="section-label">
                <span>主标</span>
                <span className="count">03</span>
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
            {subBids.length > 0 && (
              <div>
                <div className="section-label">
                  <span>陪标</span>
                  <span className="count">{String(subBids.length).padStart(2, "0")}</span>
                </div>
                <div className="space-y-2">
                  {subBids.map((sub) => (
                    <div key={sub.id}>
                      <div className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] text-[var(--color-ink-soft)] font-medium">
                        <span className="w-1 h-1 rounded-full bg-[var(--color-ink-mute)]" />
                        <span className="truncate flex-1">{sub.name}</span>
                      </div>
                      <div className="space-y-0.5 ml-2">
                        {MAIN_BID_FOLDERS.map((name) => (
                          <FolderRow
                            key={`sub-${sub.id}-${name}`}
                            name={name}
                            open={openFolders.has(`sub-${sub.id}-${name}`)}
                            onToggle={() => toggleFolder(`sub-${sub.id}-${name}`)}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              type="button"
              className="w-full flex items-center justify-center gap-1.5 py-2 text-[12px] text-[var(--color-ink-mute)] bg-transparent border border-dashed border-[var(--color-border)] rounded-xl hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-colors min-h-[36px]"
            >
              <Plus className="w-3.5 h-3.5" />
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
      aria-expanded={open}
      className="group w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12.5px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] transition-colors text-left min-h-[30px]"
    >
      <ChevronRight
        className={cn(
          "w-3 h-3 text-[var(--color-ink-mute)] transition-transform shrink-0",
          open && "rotate-90 text-[var(--color-primary)]"
        )}
      />
      {open ? (
        <FolderOpen className="w-3.5 h-3.5 text-[var(--color-primary)] shrink-0" />
      ) : (
        <Folder className="w-3.5 h-3.5 text-[var(--color-ink-mute)] group-hover:text-[var(--color-primary)] shrink-0" />
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
    <div className="card-soft p-3.5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[var(--color-success)]" />
          <span className="text-[11px] font-semibold text-[var(--color-ink)]">已解析</span>
        </div>
        {onOpenReport && (
          <button
            onClick={onOpenReport}
            className="text-[11px] text-[var(--color-primary)] hover:text-[var(--color-primary-deep)] font-medium flex items-center gap-0.5"
            aria-label="在主区打开完整报告"
          >
            打开
            <ExternalLink className="w-3 h-3" />
          </button>
        )}
      </div>
      <dl className="space-y-2">
        {fields.map((f) => (
          <div key={f.label}>
            <dt className="text-[10px] text-[var(--color-ink-mute)] uppercase tracking-wider mb-0.5">
              {f.label}
            </dt>
            <dd className="text-[12px] text-[var(--color-ink)] font-mono truncate">
              {String(f.value).slice(0, 40)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
