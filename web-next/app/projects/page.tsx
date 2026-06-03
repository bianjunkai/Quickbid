"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sidebar } from "@/components/sidebar";
import { listProjects, type Project } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  parsing: { label: "解析中", color: "bg-amber-light text-amber" },
  parsed: { label: "已解析", color: "bg-success-light text-success" },
  materials_preparing: { label: "材料准备中", color: "bg-amber-light text-amber" },
  draft_ready: { label: "草稿就绪", color: "bg-success-light text-success" },
  reviewing: { label: "审查中", color: "bg-amber-light text-amber" },
  done: { label: "完成", color: "bg-success-light text-success" },
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-8 py-10">
          <h1 className="font-display text-3xl text-ink mb-1">项目</h1>
          <p className="text-sm text-stone mb-8">所有招标项目工作流</p>

          {loading ? (
            <div className="text-sm text-stone">加载中...</div>
          ) : error ? (
            <div className="text-sm text-danger">{error}</div>
          ) : projects.length === 0 ? (
            <div className="text-sm text-stone py-12 text-center border border-dashed border-border rounded-sm">
              暂无项目。点击左侧「新建项目」开始。
            </div>
          ) : (
            <div className="border border-border rounded-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-paper text-stone text-[10px] uppercase tracking-wider">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium">项目</th>
                    <th className="text-left px-4 py-3 font-medium">状态</th>
                    <th className="text-left px-4 py-3 font-medium">创建时间</th>
                    <th className="text-right px-4 py-3 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {projects.map((p) => {
                    const status = STATUS_LABELS[p.status] || { label: p.status, color: "bg-stone/20 text-stone" };
                    return (
                      <tr key={p.id} className="border-t border-border hover:bg-paper/50">
                        <td className="px-4 py-3">
                          <Link href={`/projects/${p.id}`} className="font-medium text-ink hover:text-amber">
                            {p.name}
                          </Link>
                          <div className="text-xs text-stone mt-0.5">#{p.id}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn("text-[10px] px-2 py-0.5 rounded-sm", status.color)}>
                            {status.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-stone">
                          {new Date(p.created_at).toLocaleString("zh-CN")}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Link href={`/projects/${p.id}`} className="text-xs text-amber hover:underline">
                            打开 →
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
