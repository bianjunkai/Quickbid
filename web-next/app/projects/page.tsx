"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { Sidebar } from "@/components/sidebar";
import { listProjects, type Project } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_STATE: Record<string, "parsing" | "parsed" | "done" | "error"> = {
  parsing: "parsing",
  parsed: "parsed",
  materials_preparing: "parsing",
  draft_ready: "parsed",
  reviewing: "parsing",
  done: "done",
};

const STATUS_LABEL: Record<string, string> = {
  parsing: "解析中",
  parsed: "已解析",
  materials_preparing: "材料准备",
  draft_ready: "草稿就绪",
  reviewing: "审查中",
  done: "完成",
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
      <main className="flex-1 overflow-y-auto bg-[var(--color-paper)]">
        <div className="max-w-5xl mx-auto px-8 py-10">
          {/* Header */}
          <header className="mb-8">
            <div className="text-[11px] text-[var(--color-ink-mute)] uppercase tracking-wider font-medium mb-2">
              项目工作流
            </div>
            <h1 className="text-[36px] font-semibold text-[var(--color-ink)] leading-[1.1] tracking-tight">
              所有项目
            </h1>
            <p className="mt-3 text-[14px] text-[var(--color-ink-mute)] max-w-2xl leading-relaxed">
              创建、解析、生成、审查 — 一站式投标工作流。
            </p>
          </header>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 mb-6">
            <StatBlock label="项目总数" value={projects.length} />
            <StatBlock
              label="进行中"
              value={projects.filter((p) => p.status !== "done").length}
              accent="warning"
            />
            <StatBlock
              label="已完成"
              value={projects.filter((p) => p.status === "done").length}
              accent="success"
            />
          </div>

          {loading ? (
            <div className="card-soft p-8 text-center text-[12px] text-[var(--color-ink-mute)]">
              加载中…
            </div>
          ) : error ? (
            <div className="card-soft p-4 border border-[var(--color-danger)]">
              <div className="text-[11px] text-[var(--color-danger)] font-semibold uppercase tracking-wider mb-1">错误</div>
              <div className="text-[13px] text-[var(--color-ink)]">{error}</div>
            </div>
          ) : projects.length === 0 ? (
            <div className="card-soft border-dashed py-16 text-center">
              <div className="text-[12px] text-[var(--color-ink-mute)] mb-3">暂无项目</div>
              <div className="text-[11px] text-[var(--color-ink-mute)]">
                点击左侧「新建项目」按钮开始
              </div>
            </div>
          ) : (
            <div className="card-soft overflow-hidden">
              {projects.map((p, i) => {
                const state = STATUS_STATE[p.status] || "parsing";
                const label = STATUS_LABEL[p.status] || p.status;
                return (
                  <Link
                    key={p.id}
                    href={`/projects/${p.id}`}
                    className={cn(
                      "group flex items-center gap-4 px-5 py-4 transition-colors hover:bg-[var(--color-primary-bg)] min-h-[64px]",
                      i < projects.length - 1 && "border-b border-[var(--color-border)]"
                    )}
                  >
                    <div className="w-9 h-9 rounded-lg bg-[var(--color-paper-warm)] border border-[var(--color-border)] flex items-center justify-center text-[12px] font-mono font-semibold text-[var(--color-primary)] shrink-0">
                      #{String(p.id).padStart(2, "0")}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[14px] text-[var(--color-ink)] font-medium group-hover:text-[var(--color-primary-deep)] transition-colors truncate">
                        {p.name}
                      </div>
                      <div className="text-[11px] text-[var(--color-ink-mute)] font-mono mt-0.5 tabular-nums">
                        {new Date(p.created_at).toISOString().slice(0, 16).replace("T", " ")}
                      </div>
                    </div>
                    <span className="pill-soft" data-state={state}>
                      <span className="dot" />
                      {label}
                    </span>
                    <ChevronRight className="w-4 h-4 text-[var(--color-ink-mute)] group-hover:text-[var(--color-primary)] group-hover:translate-x-0.5 transition-transform" />
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function StatBlock({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: "success" | "warning";
}) {
  const color =
    accent === "success" ? "var(--color-success)" : accent === "warning" ? "var(--color-warning)" : "var(--color-ink)";
  return (
    <div className="card-soft p-4">
      <div className="text-[11px] text-[var(--color-ink-mute)] uppercase tracking-wider font-medium">
        {label}
      </div>
      <div className="text-[28px] font-semibold tabular-nums leading-none mt-2" style={{ color }}>
        {String(value).padStart(2, "0")}
      </div>
    </div>
  );
}
