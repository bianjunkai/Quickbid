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

  // 加载项目（含 messages 持久化历史）
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

  // useChat — 绑定 /api/projects/{id}/chat + 初始化历史
  const { messages, sendMessage, status, stop, error: chatError } = useChat({
    id: `project-${projectId}`,
    transport: new DefaultChatTransport({
      api: `/api/projects/${projectId}/chat`,
    }),
    messages: initialMessages,
    onFinish: ({ messages: finalMessages }) => {
      // 流结束 → 落库
      saveMessages(projectId, finalMessages as any).catch((e) => {
        console.error("保存对话历史失败：", e);
      });
    },
    onError: (e) => {
      console.error("chat error:", e);
    },
  });

  // 流式增量：rAF 心跳强制每帧 re-render，避免 React 19 自动批处理
  // 把中间帧吞掉导致 65s 后才一次性显示的问题
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

  // 滚动到底部（仅在 chat 视图）
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
    // 强制重建 useChat：刷新页面最简单
    router.refresh();
  };

  if (loading) {
    return (
      <main className="flex-1 flex items-center justify-center text-sm text-stone">
        加载项目…
      </main>
    );
  }
  if (error || !project) {
    return (
      <main className="flex-1 flex items-center justify-center text-sm text-danger">
        加载项目失败：{error || "项目不存在"}
      </main>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <ChatHeader
        project={project}
        onUpload={handleUpload}
        view={view}
        onViewChange={setView}
        canShowReport={hasReport}
        onClearHistory={handleClearHistory}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* 主区：chat thread 或 报告 */}
        <div className="flex-1 flex flex-col overflow-hidden bg-paper">
          {view === "chat" ? (
            <>
              <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto px-8 py-6"
              >
                <MessageList messages={messages} isStreaming={isStreaming} />
                {chatError && (
                  <div className="mt-4 text-xs text-danger bg-red-50 border border-red-200 rounded-sm px-3 py-2">
                    {chatError.message}
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
            <div className="flex-1 overflow-y-auto">
              <ParserReport data={project.parsed_data} />
            </div>
          )}
        </div>

        {/* 侧栏：项目结构 */}
        <FileSidebar
          project={project}
          onOpenReport={hasReport ? () => setView("report") : undefined}
        />
      </div>
    </div>
  );
}
