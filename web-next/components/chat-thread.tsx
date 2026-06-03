"use client";

import { useEffect, useState } from "react";
import { getProject, type ProjectDetail } from "@/lib/api";
import { ChatStage } from "./chat-stage";

// Stage 2.B 占位：展示项目状态 + 跳转入口
// Stage 2.C 替换为 assistant-ui thread + useChat

export function ChatThread({ projectId }: { projectId: number }) {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getProject(projectId)
      .then(setProject)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectId]);

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

  return <ChatStage project={project} />;
}
