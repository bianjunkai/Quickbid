"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getProject,
  saveMessages,
  type ProjectDetail,
  uploadTender,
} from "@/lib/api";
import { ChatHeader } from "./chat-header";
import { MessageList } from "./message-list";
import { Composer } from "./composer";
import { FileSidebar } from "./file-sidebar";
import { ParserReport } from "./tools/parser-report";

type ViewMode = "chat" | "report";

export function ChatThread({ projectId }: { projectId: number }) {
  const router = useRouter();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("chat");
  const [initialMessages, setInitialMessages] = useState<UIMessage[] | undefined>(undefined);
  const scrollRef = useRef<HTMLDivElement>(null);
  const projectRef = useRef<ProjectDetail | null>(null);

  useEffect(() => {
    setLoading(true);
    setView("chat");
    setInitialMessages(undefined);
    projectRef.current = null;
    getProject(projectId)
      .then((p) => {
        setProject(p);
        projectRef.current = p;
        setInitialMessages((p.messages as UIMessage[] | undefined) ?? []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  const { messages, sendMessage, status, stop, error: chatError } = useChat({
    id: `project-${projectId}`,
    transport: new DefaultChatTransport({
      api: `/api/projects/${projectId}/chat`,
    }),
    messages: initialMessages,
    onFinish: ({ messages: finalMessages }) => {
      saveMessages(projectId, finalMessages as any).catch((e) => {
        console.error("保存对话历史失败：", e);
      });
    },
    onError: (e) => {
      console.error("chat error:", e);
    },
  });

  // Force per-frame re-render during streaming to bypass React 19 batching
  const [, setTick] = useState(0);
  useEffect(() => {
    if (status !== "streaming" && status !== "submitted") return;
    let raf = 0;
    const loop = () => {
      setTick((t) => (t + 1) % 1024);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [status]);

  useEffect(() => {
    if (view === "chat" && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, view]);

  const isStreaming = status === "streaming" || status === "submitted";
  const hasReport = !!project?.parsed_data;

  const handleUpload = async (file: File) => {
    await uploadTender(projectId, file);
    const updated = await getProject(projectId);
    setProject(updated);
    projectRef.current = updated;
  };

  const handleClearHistory = async () => {
    if (!confirm("确定清空当前项目的对话历史？")) return;
    await saveMessages(projectId, []);
    setInitialMessages([]);
    router.refresh();
  };

  if (loading) {
    return (
      <main className="flex-1 flex items-center justify-center bg-[var(--color-paper)]">
        <div className="text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-[var(--color-border)] shadow-sm text-[12px] text-[var(--color-ink-mute)]">
            <span className="w-1.5 h-1.5 bg-[var(--color-primary)] rounded-full pulse-warm" />
            加载项目…
          </div>
        </div>
      </main>
    );
  }
  if (error || !project) {
    return (
      <main className="flex-1 flex items-center justify-center bg-[var(--color-paper)]">
        <div className="card-soft max-w-md p-6 text-center">
          <div className="text-[11px] text-[var(--color-danger)] font-semibold uppercase tracking-wider mb-1.5">错误</div>
          <div className="text-[14px] text-[var(--color-ink)]">{error || "项目不存在"}</div>
        </div>
      </main>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-paper)]">
      <ChatHeader
        project={project}
        onUpload={handleUpload}
        view={view}
        onViewChange={setView}
        canShowReport={hasReport}
        onClearHistory={handleClearHistory}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Main: chat or report */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          {view === "chat" ? (
            <>
              <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto bg-dotgrid px-6 py-7"
              >
                <MessageList messages={messages} isStreaming={isStreaming} />
                {chatError && (
                  <div className="max-w-3xl mx-auto mt-4">
                    <div className="card-soft p-4 border-[var(--color-danger)]">
                      <div className="text-[11px] text-[var(--color-danger)] font-semibold uppercase tracking-wider mb-1">流式错误</div>
                      <div className="text-[13px] text-[var(--color-ink)]">{chatError.message}</div>
                    </div>
                  </div>
                )}
              </div>
              <Composer
                onSend={(text) => sendMessage({ text })}
                onStop={stop}
                isStreaming={isStreaming}
                status={project.status}
              />
            </>
          ) : (
            <div className="flex-1 overflow-y-auto bg-[var(--color-paper)]">
              <ParserReport data={project.parsed_data} />
            </div>
          )}
        </div>

        {/* Right sidebar: project files */}
        <FileSidebar
          project={project}
          onOpenReport={hasReport ? () => setView("report") : undefined}
        />
      </div>
    </div>
  );
}
