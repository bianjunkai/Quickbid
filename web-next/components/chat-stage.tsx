"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ProjectDetail } from "@/lib/api";
import { uploadTender } from "@/lib/api";

const STATUS_HINTS: Record<string, string> = {
  parsing: "📄 请上传招标文件（PDF / DOCX）",
  parsed: "✅ 已解析。请在右侧查看完整报告。",
  materials_preparing: "📚 材料准备中…",
  draft_ready: "📝 草稿就绪",
  reviewing: "🔍 审查中",
  done: "🎉 完成",
};

export function ChatStage({ project }: { project: ProjectDetail }) {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setUploadError(null);
    try {
      await uploadTender(project.id, file);
      router.refresh();
    } catch (e: any) {
      setUploadError(e.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <main className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="border-b border-border bg-surface px-8 py-4">
        <h1 className="font-display text-2xl text-ink">{project.name}</h1>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-[10px] px-2 py-0.5 bg-amber-light text-amber rounded-sm uppercase tracking-wider">
            {project.status}
          </span>
          <span className="text-xs text-stone">
            {STATUS_HINTS[project.status] || ""}
          </span>
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-2xl mx-auto">
          {/* Upload zone (status==='parsing') */}
          {project.status === "parsing" && (
            <div className="border-2 border-dashed border-border rounded-sm p-12 text-center bg-surface">
              <div className="text-3xl mb-3">📤</div>
              <p className="text-sm text-ink mb-2">上传招标文件</p>
              <p className="text-xs text-stone mb-4">支持 PDF / DOCX · 最大 50MB</p>
              <label className="inline-block px-5 py-2 bg-ink text-paper text-sm rounded-sm cursor-pointer hover:bg-ink-light">
                {uploading ? "上传中…" : "选择文件"}
                <input
                  type="file"
                  accept=".pdf,.docx"
                  className="hidden"
                  disabled={uploading}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleUpload(f);
                  }}
                />
              </label>
              {uploadError && <p className="text-xs text-danger mt-3">{uploadError}</p>}
            </div>
          )}

          {/* Parsed report (status==='parsed') */}
          {project.status === "parsed" && project.parsed_data && (
            <div className="bg-surface border border-border rounded-sm p-6">
              <h2 className="font-display text-xl mb-4">解析报告</h2>
              <div className="space-y-2 text-sm">
                {Object.entries(project.parsed_data)
                  .filter(([k]) => k.startsWith("K") && k.includes("_"))
                  .slice(0, 6)
                  .map(([k, v]) => (
                    <div key={k} className="flex gap-3 border-b border-border pb-2">
                      <span className="font-mono text-[10px] text-stone w-20 shrink-0 pt-0.5">
                        {k.split("_")[0]}
                      </span>
                      <span className="text-ink flex-1 truncate">
                        {Array.isArray(v) ? `${v.length} 项` : String(v).slice(0, 80)}
                      </span>
                    </div>
                  ))}
              </div>
              <p className="text-xs text-stone mt-4">
                完整报告 8 模块 + 标记 + 风险条款 在 Stage 2.C 集成 assistant-ui 时呈现
              </p>
            </div>
          )}

          {/* Other status */}
          {project.status !== "parsing" && project.status !== "parsed" && (
            <div className="text-center py-12 text-sm text-stone">
              {STATUS_HINTS[project.status] || "状态： " + project.status}
              <p className="text-xs mt-2">后续状态由 Chat 驱动（Stage 2.C 集成）</p>
            </div>
          )}
        </div>
      </div>

      {/* Footer hint */}
      <footer className="border-t border-border bg-surface px-8 py-3 text-[10px] text-stone uppercase tracking-wider">
        Stage 2.B 占位 · Stage 2.C 集成 assistant-ui · 输入「放好了」开始解析
      </footer>
    </main>
  );
}
