"use client";

import { use, useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { ChatThread } from "@/components/chat-thread";
import { MarkdownViewer } from "@/components/markdown-viewer";
import { useRouter } from "next/navigation";

export default function ProjectChatPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ file?: string; tender?: string; doc?: string }>;
}) {
  const { id } = use(params);
  const search = use(searchParams);
  const projectId = Number(id);
  const filePath = search.file;
  const docType = search.doc === "outline" || search.doc === "deviation" ? search.doc : null;
  const tenderParam = search.tender ? Number(search.tender) : null;

  if (!Number.isFinite(projectId) || projectId <= 0) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center text-sm text-danger">
          无效的项目 ID
        </main>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      {docType ? (
        <MarkdownViewerWrapper
          projectId={projectId}
          tenderParam={null}
          filePath={undefined}
          documentType={docType}
        />
      ) : filePath ? (
        <MarkdownViewerWrapper
          projectId={projectId}
          tenderParam={tenderParam}
          filePath={filePath}
          documentType="file"
        />
      ) : (
        <ChatThread projectId={projectId} />
      )}
    </div>
  );
}

function MarkdownViewerWrapper({
  projectId,
  tenderParam,
  filePath,
  documentType = "file",
}: {
  projectId: number;
  tenderParam: number | null;
  filePath?: string;
  documentType?: "file" | "outline" | "deviation";
}) {
  const router = useRouter();
  const [tenderId, setTenderId] = useState<number | null>(null);

  useEffect(() => {
    if (documentType !== "file") {
      setTenderId(0);
      return;
    }
    if (tenderParam && Number.isFinite(tenderParam)) {
      setTenderId(tenderParam);
      return;
    }
    // 拉取项目获取当前主标 tender id
    fetch(`/api/projects/${projectId}`)
      .then(res => res.json())
      .then(data => setTenderId(data.active_main_tender_id || data.tender_id || null))
      .catch(console.error);
  }, [projectId, tenderParam, documentType]);

  const handleClose = () => {
    router.replace(`/projects/${projectId}`, { scroll: false });
  };

  if (documentType === "file" && !tenderId) {
    return (
      <main className="flex-1 flex items-center justify-center bg-[var(--color-paper)]">
        <div className="text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-[var(--color-border)] shadow-sm text-[12px] text-[var(--color-ink-mute)]">
            <span className="w-1.5 h-1.5 bg-[var(--color-primary)] rounded-full pulse-warm" />
            加载文件…
          </div>
        </div>
      </main>
    );
  }

  return (
    <MarkdownViewer
      projectId={projectId}
      tenderId={tenderId || undefined}
      filePath={filePath}
      documentType={documentType}
      onClose={handleClose}
    />
  );
}
