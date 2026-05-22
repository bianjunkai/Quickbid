export interface Project {
  id: number
  name: string
  status: string
  created_at: string
  tender_file_path?: string
  project_name?: string
  tender_no?: string
  budget?: number
  deadline?: string
  open_time?: string
}

export interface Material {
  id: number
  title: string
  category: string
  tags: string
  description: string
  char_count: number
  ai_summary: string
  version: string
}

export interface Tender {
  id: number
  project_id: number
  type: 'main' | 'sub'
  status: string
  draft_path?: string
  deviation_path?: string
}

export interface ParsedData {
  K01_项目名称: string
  K02_招标编号: string
  K03_招标人信息: string
  K04_预算金额: number
  K05_投标截止时间: string | null
  K06_开标时间: string | null
  K07_评分标准: string
  K08_技术要求: string
  K09_商务资质要求: string
  K10_星标项: string[]
  K11_废标条款: string[]
  K12_章节模板要求: string
  K13_偏离表要求: string
  K14_演示要求: string
}

export interface Chapter {
  chapter: string
  recommended: {
    id: number
    title: string
    match_score: string
    reason: string
  }[]
}

export interface ReviewReport {
  [key: string]: {
    status: 'pass' | 'warning' | 'fail'
    issues: string[]
  }
}
