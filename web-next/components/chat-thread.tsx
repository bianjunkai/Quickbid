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
  apiBase,
} from "@/lib/api";
import { ChatHeader } from "./chat-header";
import { MessageList } from "./message-list";
import { Composer } from "./composer";
import { FileSidebar } from "./file-sidebar";
import { ParserReport } from "./tools/parser-report";

type ViewMode = "chat" | "report";

/**
 * 外层 ChatThread：只负责"加载项目数据"这件事。
 * 不直接用 useChat —— 因为 useChat 的 Chat 实例只在 useRef 首次 new 一次
 * 读 messages，后续 prop 变更它不重读。要让 useChat 在数据加载后能拿到正确的
 * 历史，必须保证它是在"数据已就绪"的第一次 render 时被 new 出来。
 *
 * 办法：把 useChat 挪到内部组件 ChatView，key 绑定到 projectId，
 * projectId 变化或数据清空时 React 会真卸载+重建 ChatView，useChat 第一次
 * 渲染就能读到 initialMessages。
 */
export function ChatThread({ projectId }: { projectId: number }) {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatKey, setChatKey] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setProject(null);
    // 切项目时强制 ChatView 重建，丢弃上一个项目的 in-flight chat state
    setChatKey((v) => v + 1);
    getProject(projectId)
      .then((p) => setProject(p))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectId]);

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

  const handleClearHistory = async () => {
    if (!confirm("确定清空当前项目的对话历史？")) return;
    await saveMessages(projectId, []);
    setProject((p) => (p ? { ...p, messages: [] } : p));
    // 让 ChatView 用空 initialMessages 重建
    setChatKey((v) => v + 1);
  };

  // 关键：key 同时包含 projectId 和 chatKey，任意一个变化都会让 ChatView 真重建
  return (
    <ChatView
      key={`${projectId}-${chatKey}`}
      projectId={projectId}
      project={project}
      onProjectChange={setProject}
      onClearHistory={handleClearHistory}
    />
  );
}

function ChatView({
  projectId,
  project,
  onProjectChange,
  onClearHistory,
}: {
  projectId: number;
  project: ProjectDetail;
  onProjectChange: (p: ProjectDetail) => void;
  onClearHistory: () => void;
}) {
  const router = useRouter();
  const [view, setView] = useState<ViewMode>("chat");
  const scrollRef = useRef<HTMLDivElement>(null);
  const projectRef = useRef<ProjectDetail>(project);

  useEffect(() => {
    projectRef.current = project;
  }, [project]);

  // 在 ChatView 第一次渲染时拍下 initial messages，
  // 后续 project 对象变化（upload 后）不影响 useChat 已建立的历史
  const initialMessages = (project.messages as UIMessage[] | undefined) ?? [];

  const { messages, sendMessage, status, stop, error: chatError } = useChat({
    id: `project-${projectId}`,
    transport: new DefaultChatTransport({
      api: apiBase
        ? `${apiBase}/projects/${projectId}/chat`
        : `/api/projects/${projectId}/chat`,
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
    onProjectChange(updated);
    projectRef.current = updated;
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-paper)]">
      <ChatHeader
        project={project}
        onUpload={handleUpload}
        view={view}
        onViewChange={setView}
        canShowReport={hasReport}
        onClearHistory={onClearHistory}
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
