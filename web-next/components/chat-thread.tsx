"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getProject, type ProjectDetail, uploadTender } from "@/lib/api";
import { ChatHeader } from "./chat-header";
import { MessageList } from "./message-list";
import { Composer } from "./composer";
import { FileSidebar } from "./file-sidebar";

export function ChatThread({ projectId }: { projectId: number }) {
  const router = useRouter();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 加载项目
  useEffect(() => {
    setLoading(true);
    getProject(projectId)
      .then(setProject)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  // useChat 绑定 /api/projects/{id}/chat
  const { messages, sendMessage, status, stop, error: chatError } = useChat({
    id: `project-${projectId}`,
    transport: new DefaultChatTransport({
      api: `/api/projects/${projectId}/chat`,
    }),
  });

  // 滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const isStreaming = status === "streaming" || status === "submitted";

  const handleUpload = async (file: File) => {
    await uploadTender(projectId, file);
    // 刷新项目
    const updated = await getProject(projectId);
    setProject(updated);
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
      <ChatHeader project={project} onUpload={handleUpload} />

      <div className="flex-1 flex overflow-hidden">
        {/* 主区：chat thread */}
        <div className="flex-1 flex flex-col overflow-hidden bg-paper">
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 py-6">
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
        </div>

        {/* 侧栏：项目结构 */}
        <FileSidebar project={project} />
      </div>
    </div>
  );
}
