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

// K01-K14 与 ParserAgent 输出一致
export interface ParsedData {
  K01_项目名称: string
  K02_招标编号: string
  K03_招标人: string
  K04_预算金额: string
  K05_投标截止时间: string
  K06_开标时间: string
  K07_评分标准: string
  K08_技术要求: string
  K09_商务资质要求: string
  K10_星标项: string[]
  K11_废标条款: string[]
  K12_章节模板要求: string
  K13_偏离表格式要求: string
  K14_演示要求: string
  [key: string]: any
}

// MatcherAgent 返回的章节推荐
export interface Chapter {
  chapter: string
  material_id: number
  material_title: string
  match_score: string
  reason: string
}

// ReviewerAgent 返回的 check 结构
export interface ReviewCheck {
  check_id: string
  check_name: string
  status: 'pass' | 'warning' | 'fail'
  issue: string
  suggestion: string
}

export interface ReviewSummary {
  high: number
  medium: number
  low: number
}

// 后端材质分类常量，与 config.yaml 对齐
export const MATERIAL_CATEGORIES = [
  { value: '01_公司资质', label: '公司资质' },
  { value: '02_业绩案例', label: '业绩案例' },
  { value: '03_技术方案', label: '技术方案' },
  { value: '04_实施方案', label: '实施方案' },
  { value: '05_商务文件', label: '商务文件' },
  { value: '06_其他', label: '其他' },
] as const
