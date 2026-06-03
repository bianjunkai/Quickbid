"use client";

import { use } from "react";
import { Sidebar } from "@/components/sidebar";
import { ChatThread } from "@/components/chat-thread";

export default function ProjectChatPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const projectId = Number(id);
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
      <ChatThread projectId={projectId} />
    </div>
  );
}
