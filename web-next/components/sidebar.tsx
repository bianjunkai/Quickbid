"use client";

import { Fragment, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Plus,
  X,
  ChevronsUpDown,
  PanelLeftClose,
  Library,
  Briefcase,
  Settings,
  ChevronRight,
  Trash2,
} from "lucide-react";
import { listProjects, createProject, deleteProject, type Project } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_STATE: Record<string, "parsing" | "parsed" | "done" | "error"> = {
  parsing: "parsing",
  parsed: "parsed",
  outline_generating: "parsing",
  materials_preparing: "parsing",
  deviation_preparing: "parsing",
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
  deviation_preparing: "偏离表确认",
  generating: "生成中",
  generated: "已生成",
  reviewing: "审查中",
  reviewed: "已终审",
  review_failed: "终审失败",
  done: "完成",
};

type FeatureItem = {
  label: string;
  desc: string;
  icon: typeof Briefcase;
  href: string;
  showCount?: boolean;
  exact?: boolean;
  hasSubList?: boolean;
};

const FEATURES: FeatureItem[] = [
  {
    label: "项目",
    desc: "Project",
    icon: Briefcase,
    href: "/projects",
    showCount: true,
    hasSubList: true,
  },
  {
    label: "材料库",
    desc: "Library",
    icon: Library,
    href: "/materials",
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [featuresOpen, setFeaturesOpen] = useState(true);
  const [deleting, setDeleting] = useState<number | null>(null);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = await listProjects();
      setProjects(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [pathname]);

  useEffect(() => {
    if (showCreate) {
      const onKey = (e: KeyboardEvent) => {
        if (e.key === "Escape") setShowCreate(false);
      };
      document.addEventListener("keydown", onKey);
      return () => document.removeEventListener("keydown", onKey);
    }
  }, [showCreate]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const res = await createProject({ name: newName.trim(), tender_file_name: "tender.pdf" });
      setShowCreate(false);
      setNewName("");
      await fetchProjects();
      if (res?.project_id) router.push(`/projects/${res.project_id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`确定删除项目「${name}」？此操作不可撤销。`)) return;
    setDeleting(id);
    try {
      await deleteProject(id);
      await fetchProjects();
      // 如果删除的是当前项目，跳回项目列表
      if (pathname === `/projects/${id}`) {
        router.push("/projects");
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <aside className="w-64 shrink-0 bg-[var(--color-surface)] border-r border-[var(--color-border)] flex flex-col h-screen">
      {/* Brand */}
      <div className="px-4 pt-4 pb-3">
        <div className="flex items-center justify-between">
          <Link href="/projects" className="flex items-center gap-2.5 group" aria-label="QuickBid 首页">
            <div className="w-9 h-9 rounded-[10px] bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-deep)] flex items-center justify-center shadow-sm">
              <span className="font-bold text-white text-[15px] tracking-tight">Q</span>
            </div>
            <div>
              <div className="font-semibold text-[15px] text-[var(--color-ink)] leading-none tracking-tight">
                QuickBid
              </div>
              <div className="text-[10px] text-[var(--color-ink-mute)] mt-1 font-medium uppercase tracking-wider">
                标书工作台
              </div>
            </div>
          </Link>
          <button
            aria-label="收起侧栏"
            className="w-7 h-7 rounded-md text-[var(--color-ink-mute)] hover:bg-[var(--color-paper-warm)] hover:text-[var(--color-ink)] flex items-center justify-center"
          >
            <PanelLeftClose className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* New project button */}
      <div className="px-4 pb-4">
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary w-full"
          aria-label="新建项目"
        >
          <Plus className="w-4 h-4" strokeWidth={2.5} />
          <span>新建项目</span>
        </button>
      </div>

      {/* Scrollable nav */}
      <nav className="flex-1 overflow-y-auto pb-2">
        {/* Features section */}
        <div className="px-4">
          <button
            onClick={() => setFeaturesOpen((v) => !v)}
            className="section-label w-full"
            aria-expanded={featuresOpen}
          >
            <span className="flex items-center gap-1.5">
              <ChevronRight
                className={cn("w-3 h-3 transition-transform", featuresOpen && "rotate-90")}
              />
              功能
            </span>
          </button>
          {featuresOpen && (
            <ul className="space-y-0.5 mb-5">
              {FEATURES.map((f) => {
                const active = f.exact
                  ? pathname === f.href
                  : pathname.startsWith(f.href);
                return (
                  <Fragment key={f.label}>
                    <li>
                      <Link
                        href={f.href}
                        className={cn(
                          "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13px] transition-colors min-h-[34px]",
                          active
                            ? "bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)]"
                            : "text-[var(--color-ink-soft)] hover:bg-[var(--color-paper-warm)] hover:text-[var(--color-ink)]"
                        )}
                      >
                        <f.icon className="w-3.5 h-3.5 text-[var(--color-primary)]" strokeWidth={1.75} />
                        <span className="flex-1">{f.label}</span>
                        {f.showCount && (
                          <span className="text-[10px] text-[var(--color-ink-mute)] font-mono tabular-nums">
                            {String(projects.length).padStart(2, "0")}
                          </span>
                        )}
                        <span className="text-[10px] text-[var(--color-ink-mute)]">{f.desc}</span>
                      </Link>
                    </li>
                    {f.hasSubList && (
                      <>
                        {loading ? (
                          <li className="px-2.5 py-2 text-[12px] text-[var(--color-ink-mute)]">
                            加载中…
                          </li>
                        ) : projects.length === 0 ? (
                          <li className="px-2.5 py-2 text-[12px] text-[var(--color-ink-mute)]">
                            暂无项目
                          </li>
                        ) : (
                          projects.map((p) => {
                            const itemActive = pathname === `/projects/${p.id}`;
                            const state = STATUS_STATE[p.status] || "parsing";
                            return (
                              <li key={p.id} className="group flex items-center">
                                <Link
                                  href={`/projects/${p.id}`}
                                  className={cn(
                                    "flex-1 flex items-center gap-2.5 pl-7 pr-1 py-1.5 rounded-lg transition-colors min-h-[32px]",
                                    itemActive
                                      ? "bg-[var(--color-primary-bg)]"
                                      : "hover:bg-[var(--color-paper-warm)]"
                                  )}
                                >
                                  <span
                                    className={cn(
                                      "w-1.5 h-1.5 rounded-full shrink-0",
                                      state === "done" && "bg-[var(--color-success)]",
                                      state === "parsed" && "bg-[var(--color-primary)]",
                                      state === "parsing" && "bg-[var(--color-warning)]",
                                      state === "error" && "bg-[var(--color-danger)]"
                                    )}
                                  />
                                  <span
                                    className={cn(
                                      "flex-1 text-[12.5px] truncate",
                                      itemActive
                                        ? "text-[var(--color-primary-deep)] font-semibold"
                                        : "text-[var(--color-ink)]"
                                    )}
                                  >
                                    {p.name}
                                  </span>
                                </Link>
                                <button
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    handleDelete(p.id, p.name);
                                  }}
                                  disabled={deleting === p.id}
                                  aria-label={`删除项目 ${p.name}`}
                                  className={cn(
                                    "shrink-0 w-6 h-6 rounded-md flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all",
                                    "text-[var(--color-ink-mute)] hover:text-[var(--color-danger)] hover:bg-red-50",
                                    deleting === p.id && "opacity-100 pointer-events-none"
                                  )}
                                >
                                  {deleting === p.id ? (
                                    <span className="w-2.5 h-2.5 border-2 border-[var(--color-ink-mute)] border-t-transparent rounded-full animate-spin" />
                                  ) : (
                                    <Trash2 className="w-3 h-3" />
                                  )}
                                </button>
                              </li>
                            );
                          })
                        )}
                      </>
                    )}
                  </Fragment>
                );
              })}
            </ul>
          )}
        </div>
      </nav>

      {/* Bottom nav — settings */}
      <div className="border-t border-[var(--color-border)] px-4 py-2.5 flex items-center gap-2 text-[11px] text-[var(--color-ink-mute)]">
        <Settings className="w-3 h-3" />
        <span>设置 · v3.0</span>
      </div>

      {/* Create dialog */}
      {showCreate && (
        <div
          className="fixed inset-0 bg-[var(--color-ink)]/40 flex items-center justify-center z-50"
          onClick={() => setShowCreate(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="new-project-title"
        >
          <div
            className="card-soft bg-[var(--color-surface)] w-[440px] max-w-[92vw] p-7"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-5">
              <div>
                <h3 id="new-project-title" className="font-semibold text-[22px] text-[var(--color-ink)] tracking-tight">
                  新建项目
                </h3>
                <p className="text-[12px] text-[var(--color-ink-mute)] mt-1">
                  输入项目名称以创建工作流
                </p>
              </div>
              <button
                onClick={() => setShowCreate(false)}
                aria-label="关闭"
                className="w-8 h-8 rounded-lg text-[var(--color-ink-mute)] hover:bg-[var(--color-paper-warm)] hover:text-[var(--color-ink)] flex items-center justify-center"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div>
              <label htmlFor="new-project-name" className="block text-[12px] font-medium text-[var(--color-ink-soft)] mb-1.5">
                项目名称
              </label>
              <input
                id="new-project-name"
                autoFocus
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                placeholder="如：XX 医院 HIS 系统"
                className="w-full px-3.5 py-2.5 bg-[var(--color-surface-sunk)] border border-[var(--color-border)] rounded-xl text-[14px] text-[var(--color-ink)] placeholder:text-[var(--color-ink-mute)] focus:bg-white focus:border-[var(--color-primary)] focus:outline-none min-h-[44px]"
              />
              {error && (
                <p className="mt-2 text-[11px] text-[var(--color-danger)]">{error}</p>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-[13px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] rounded-lg min-h-[40px]"
              >
                取消
              </button>
              <button
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                className="btn-primary disabled:opacity-40 disabled:hover:bg-[var(--color-ink-button)]"
              >
                {creating ? "创建中…" : "创建项目"}
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
