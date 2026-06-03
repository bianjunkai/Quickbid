"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { listProjects, createProject, type Project } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  parsing: { label: "解析中", color: "bg-amber-light text-amber" },
  parsed: { label: "已解析", color: "bg-success-light text-success" },
  materials_preparing: { label: "材料准备中", color: "bg-amber-light text-amber" },
  draft_ready: { label: "草稿就绪", color: "bg-success-light text-success" },
  reviewing: { label: "审查中", color: "bg-amber-light text-amber" },
  done: { label: "完成", color: "bg-success-light text-success" },
};

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
  }, [pathname]); // 路由变化时刷新

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const res = await createProject({ name: newName.trim(), tender_file_name: "tender.pdf" });
      setShowCreate(false);
      setNewName("");
      // 刷新列表
      await fetchProjects();
      // 跳转
      if (res?.project_id) {
        router.push(`/projects/${res.project_id}`);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <aside className="w-60 shrink-0 border-r border-border bg-surface flex flex-col h-screen">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-border">
        <Link href="/projects" className="block">
          <div className="font-display text-2xl font-semibold text-ink leading-none">QuickBid</div>
          <div className="text-[10px] text-stone uppercase tracking-wider mt-1">标书智能生成</div>
        </Link>
      </div>

      {/* New project */}
      <div className="px-4 py-3 border-b border-border">
        <button
          onClick={() => setShowCreate(true)}
          className="w-full px-3 py-2 text-sm bg-ink text-paper rounded-sm hover:bg-ink-light transition-colors"
        >
          + 新建项目
        </button>
      </div>

      {/* Project list */}
      <nav className="flex-1 overflow-y-auto py-2">
        {loading ? (
          <div className="px-4 py-3 text-xs text-stone">加载中...</div>
        ) : projects.length === 0 ? (
          <div className="px-4 py-3 text-xs text-stone">暂无项目</div>
        ) : (
          projects.map((p) => {
            const active = pathname === `/projects/${p.id}`;
            const status = STATUS_LABELS[p.status] || { label: p.status, color: "bg-stone/20 text-stone" };
            return (
              <Link
                key={p.id}
                href={`/projects/${p.id}`}
                className={cn(
                  "block px-4 py-2.5 mx-2 rounded-sm transition-colors",
                  active ? "bg-paper" : "hover:bg-paper/50"
                )}
              >
                <div className="text-sm font-medium text-ink truncate">{p.name}</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className={cn("text-[9px] px-1.5 py-0.5 rounded-sm", status.color)}>
                    {status.label}
                  </span>
                  <span className="text-[10px] text-stone">#{p.id}</span>
                </div>
              </Link>
            );
          })
        )}
      </nav>

      {/* Bottom nav */}
      <div className="border-t border-border px-4 py-3">
        <Link
          href="/materials"
          className={cn(
            "block text-xs uppercase tracking-wider transition-colors",
            pathname.startsWith("/materials") ? "text-amber" : "text-stone hover:text-ink"
          )}
        >
          材料库
        </Link>
      </div>

      {/* Create dialog */}
      {showCreate && (
        <div className="fixed inset-0 bg-ink/40 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div
            className="bg-surface rounded-sm shadow-2xl p-6 w-[420px]"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-display text-xl mb-4">新建项目</h3>
            <input
              autoFocus
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              placeholder="项目名称"
              className="w-full px-3 py-2 border border-border rounded-sm text-sm focus:outline-none focus:border-amber"
            />
            {error && <p className="text-xs text-danger mt-2">{error}</p>}
            <div className="flex justify-end gap-2 mt-5">
              <button
                onClick={() => setShowCreate(false)}
                className="px-3 py-1.5 text-sm text-stone hover:text-ink"
              >
                取消
              </button>
              <button
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                className="px-4 py-1.5 text-sm bg-ink text-paper rounded-sm disabled:opacity-50"
              >
                {creating ? "创建中..." : "创建"}
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
