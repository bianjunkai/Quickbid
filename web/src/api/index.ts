import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// ---- 项目管理 ----
export const createProject = (data: { name: string; tender_file_name: string }) =>
  api.post('/projects', data)

export const listProjects = () => api.get('/projects')

export const getProject = (id: number) => api.get(`/projects/${id}`)

export const deleteProject = (id: number) => api.delete(`/projects/${id}`)

// ---- 招标文件解析 ----
export const parseTender = (id: number) => api.post(`/projects/${id}/parse`)

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
