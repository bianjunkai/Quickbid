// QuickBid API client — fetch wrapper
// 后端：FastAPI @ :8000（开发时由 next.config.ts 代理到 /api/*）

export interface Project {
  id: number;
  name: string;
  status: string;
  created_at: string;
}

export interface ProjectDetail extends Project {
  tender_file_path?: string;
  project_name?: string;
  tender_no?: string;
  budget?: number;
  deadline?: string;
  open_time?: string;
  parsed_data?: any;
  messages?: UIMessageData[];
}

export interface Material {
  id: number;
  title: string;
  category: string;
  tags?: string;
  description?: string;
  char_count?: number;
  ai_summary?: string;
  version?: number;
}

// AI SDK UIMessage 简化类型（用于持久化往返）
export interface UIMessageData {
  id: string;
  role: "user" | "assistant" | "system";
  parts: any[];
  metadata?: unknown;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const data = await res.json();
      if (data?.detail) {
        msg = Array.isArray(data.detail)
          ? data.detail.map((d: any) => d?.msg || JSON.stringify(d)).join("；")
          : typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail);
      }
    } catch { /* ignore */ }
    throw new ApiError(res.status, msg);
  }
  return res.json();
}

// ---- 项目管理 ----
export const listProjects = () => request<Project[]>("/api/projects");
export const getProject = (id: number) =>
  request<ProjectDetail>(`/api/projects/${id}`);
export const createProject = (data: { name: string; tender_file_name: string }) =>
  request<{ project_id: number; project_name: string; tender_file_path: string; message: string }>(
    "/api/projects",
    { method: "POST", body: JSON.stringify(data) }
  );
export const deleteProject = (id: number) =>
  request<{ message: string }>(`/api/projects/${id}`, { method: "DELETE" });

// ---- 招标文件上传 ----
export const uploadTender = (id: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return fetch(`/api/projects/${id}/upload`, {
    method: "POST",
    body: form,
    // 不要设置 Content-Type — 浏览器会自动生成 multipart boundary
  }).then(async (res) => {
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, err.detail || "上传失败");
    }
    return res.json();
  });
};

export const saveMessages = (id: number, messages: UIMessageData[]) =>
  request<{ message: string; count: number }>(`/api/projects/${id}/messages`, {
    method: "PUT",
    body: JSON.stringify({ messages }),
  });

// ---- 材料库 ----
export const listMaterials = (params?: { category?: string; keyword?: string }) => {
  const search = new URLSearchParams();
  if (params?.category) search.set("category", params.category);
  if (params?.keyword) search.set("keyword", params.keyword);
  const qs = search.toString();
  return request<Material[]>(`/api/materials${qs ? `?${qs}` : ""}`);
};

export const createMaterial = (data: {
  title: string;
  category: string;
  description: string;
  content: string;
  content_type?: string;
  tags?: string;
}) =>
  request<{ id: number; title: string; message: string }>("/api/materials", {
    method: "POST",
    body: JSON.stringify(data),
  });

export { ApiError };
