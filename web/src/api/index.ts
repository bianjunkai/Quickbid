import axios from 'axios'

// 5 分钟 — full 模式解析 ~10 次 LLM 串行调用约 1-2 分钟；generate/review
// /export 同样需要较长时间
const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

// ---- 项目管理 ----
export const createProject = (data: { name: string; tender_file_name: string }) =>
  api.post('/projects', data)

export const listProjects = () => api.get('/projects')

export const getProject = (id: number) => api.get(`/projects/${id}`)

export const deleteProject = (id: number) => api.delete(`/projects/${id}`)

// ---- 招标文件上传 ----
export const uploadTender = (id: number, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post(`/projects/${id}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ---- 招标文件解析 ----
export const parseTender = (id: number, mode?: 'auto' | 'quick' | 'full' | 'manual') =>
  api.post(`/projects/${id}/parse`, null, { params: mode ? { mode } : {} })

// ---- 分步解析（前端串行调用显示进度）— 阶段 1：3 步 ----
export const parseStep1 = (id: number, mode?: string) =>
  api.post(`/projects/${id}/parse/step1`, null, { params: mode ? { mode } : {} })
export const parseStep2 = (id: number) => api.post(`/projects/${id}/parse/step2`)
export const parseStep3 = (id: number) => api.post(`/projects/${id}/parse/step3`)

export const confirmParse = (id: number, corrections?: Record<string, any>) =>
  api.post(`/projects/${id}/parse/confirm`, { corrections })

// ---- 材料匹配 ----
export const matchMaterials = (id: number, tenderType: 'main' | 'sub' = 'main') =>
  api.get(`/projects/${id}/match`, { params: { tender_type: tenderType } })

// ---- 标书生成 ----
export const generateTender = (id: number, tenderType: 'main' | 'sub', confirmedChapters?: Record<string, number>) =>
  api.post(`/projects/${id}/generate`, { tender_type: tenderType, confirmed_chapters: confirmedChapters })

// ---- 标书终审 ----
export const reviewTender = (id: number) => api.post(`/tenders/${id}/review`)

// ---- 导出 ----
export const exportTender = (id: number, format: 'markdown' | 'word' | 'pdf') =>
  api.post(`/tenders/${id}/export`, { format })

// ---- 材料库 ----
export const listMaterials = (params?: { category?: string; keyword?: string }) =>
  api.get('/materials', { params })

export const createMaterial = (data: {
  title: string; category: string; description: string;
  content: string; content_type?: string; tags?: string;
}) => api.post('/materials', data)

export default api
