"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { listMaterials, type Material } from "@/lib/api";
import { cn } from "@/lib/utils";

const CATEGORIES = [
  { key: "", label: "全部" },
  { key: "01_公司资质", label: "公司资质" },
  { key: "02_业绩案例", label: "业绩案例" },
  { key: "03_技术方案", label: "技术方案" },
  { key: "04_实施方案", label: "实施方案" },
  { key: "05_商务文件", label: "商务文件" },
  { key: "06_其他", label: "其他" },
];

export default function MaterialsPage() {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    setLoading(true);
    listMaterials(filter ? { category: filter } : undefined)
      .then(setMaterials)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-[var(--color-paper)]">
        <div className="max-w-6xl mx-auto px-8 py-10">
          {/* Header */}
          <header className="mb-6">
            <div className="text-[11px] text-[var(--color-ink-mute)] uppercase tracking-wider font-medium mb-2">
              材料库
            </div>
            <h1 className="text-[36px] font-semibold text-[var(--color-ink)] leading-[1.1] tracking-tight">
              可复用材料
            </h1>
            <p className="mt-3 text-[14px] text-[var(--color-ink-mute)] max-w-2xl leading-relaxed">
              所有可复用的资质 / 方案 / 业绩材料。在项目工作流中自动匹配与引用。
            </p>
          </header>

          {/* Category filter — pill style */}
          <div className="mb-6 flex items-center gap-1.5 flex-wrap">
            {CATEGORIES.map((c) => {
              const active = filter === c.key;
              return (
                <button
                  key={c.key}
                  onClick={() => setFilter(c.key)}
                  className={cn(
                    "px-3.5 py-1.5 rounded-full text-[12px] font-medium transition-all min-h-[32px]",
                    active
                      ? "bg-[var(--color-ink)] text-[var(--color-paper)]"
                      : "bg-[var(--color-surface)] text-[var(--color-ink-soft)] border border-[var(--color-border)] hover:border-[var(--color-ink)] hover:text-[var(--color-ink)]"
                  )}
                >
                  {c.label}
                </button>
              );
            })}
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
          ) : materials.length === 0 ? (
            <div className="card-soft border-dashed py-16 text-center">
              <div className="text-[12px] text-[var(--color-ink-mute)]">暂无材料</div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {materials.map((m, i) => (
                <article
                  key={m.id}
                  className="card-soft p-4 hover:shadow-md transition-shadow cursor-pointer group"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h3 className="text-[14px] font-semibold text-[var(--color-ink)] leading-snug group-hover:text-[var(--color-primary-deep)] transition-colors">
                      {m.title}
                    </h3>
                    <span className="text-[10px] text-[var(--color-ink-mute)] font-mono shrink-0">
                      v{String(m.version ?? 1).padStart(2, "0")}
                    </span>
                  </div>
                  <p className="text-[12px] text-[var(--color-ink-mute)] leading-relaxed line-clamp-2 mb-3 min-h-[32px]">
                    {m.description || "—"}
                  </p>
                  <div className="flex items-center justify-between pt-2.5 border-t border-[var(--color-border)]">
                    <span className="text-[10px] text-[var(--color-ink-soft)] font-medium uppercase tracking-wider">
                      {m.category?.slice(3) || "—"}
                    </span>
                    <span className="text-[10px] text-[var(--color-ink-mute)] font-mono tabular-nums">
                      {String(m.char_count || 0).padStart(5, "0")} 字
                    </span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
