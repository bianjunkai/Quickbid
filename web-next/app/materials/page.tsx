"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { listMaterials, type Material } from "@/lib/api";

const CATEGORIES = [
  "01_公司资质",
  "02_技术方案",
  "03_商务资质",
  "04_项目业绩",
  "05_人员资质",
  "06_其他",
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
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-8 py-10">
          <h1 className="font-display text-3xl text-ink mb-1">材料库</h1>
          <p className="text-sm text-stone mb-6">所有可复用的资质 / 方案 / 业绩材料</p>

          {/* Category filter */}
          <div className="flex gap-2 mb-6 flex-wrap">
            <button
              onClick={() => setFilter("")}
              className={`px-3 py-1 text-xs rounded-sm border ${
                filter === "" ? "bg-ink text-paper border-ink" : "bg-surface text-stone border-border hover:border-ink"
              }`}
            >
              全部
            </button>
            {CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => setFilter(c)}
                className={`px-3 py-1 text-xs rounded-sm border ${
                  filter === c ? "bg-ink text-paper border-ink" : "bg-surface text-stone border-border hover:border-ink"
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="text-sm text-stone">加载中…</div>
          ) : error ? (
            <div className="text-sm text-danger">{error}</div>
          ) : materials.length === 0 ? (
            <div className="text-sm text-stone py-12 text-center border border-dashed border-border rounded-sm">
              暂无材料
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {materials.map((m) => (
                <div
                  key={m.id}
                  className="bg-surface border border-border rounded-sm p-4 hover:border-amber transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-medium text-sm text-ink flex-1">{m.title}</h3>
                    <span className="text-[9px] text-stone shrink-0 ml-2">v{m.version}</span>
                  </div>
                  <p className="text-xs text-stone line-clamp-2 mb-3">{m.description}</p>
                  <div className="flex items-center justify-between text-[10px] text-stone">
                    <span className="px-1.5 py-0.5 bg-paper rounded-sm">{m.category}</span>
                    <span>{m.char_count || 0} 字</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
