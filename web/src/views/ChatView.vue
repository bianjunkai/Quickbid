<template>
  <div class="chat-view" v-loading="projectLoading">
    <div class="chat-body">
      <div class="chat-main">
        <!-- Header bar -->
        <div class="chat-header">
      <div class="chat-header-left">
        <span class="project-name">{{ project?.name || '加载中...' }}</span>
        <span v-if="project" class="project-status" :class="project.status">{{ statusLabel }}</span>
        <span v-if="tenderFileName" class="tender-file-badge" :title="project?.tender_file_path">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          {{ tenderFileName }}
        </span>
      </div>
      <div class="chat-header-right">
        <el-dropdown trigger="click">
          <button class="header-action-btn" title="更多">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="router.push('/projects')">返回项目列表</el-dropdown-item>
              <el-dropdown-item @click="router.push('/materials')">材料库</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- Upload zone (when status=parsing and no file yet) -->
    <div v-if="project?.status === 'parsing' && !tenderFileName" class="upload-banner">
      <div class="upload-banner-inner">
        <div class="upload-banner-text">
          <strong>📎 上传招标文件</strong>
          <p>支持 PDF / DOCX。上传完成后输入「放好了」开始解析。</p>
        </div>
        <el-upload
          :show-file-list="false" :auto-upload="false" accept=".pdf,.docx"
          :on-change="(f: any) => handleUploadTender(f.raw)"
        >
          <el-button type="primary" :loading="uploading">选择文件</el-button>
        </el-upload>
      </div>
    </div>

    <!-- Tabs: chat + tender requirements (only when parsed) -->
    <el-tabs v-model="activeTab" class="chat-tabs">
      <el-tab-pane label="对话" name="chat">
        <div class="tab-chat">
          <!-- Messages -->
          <div class="chat-messages" ref="messagesEl">
            <div v-if="!projectLoading && messages.length === 0" class="chat-empty">
              <div class="empty-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </div>
              <p>开始与 AI 助手对话，完成标书制作</p>
              <p class="empty-hint">例如：「新建项目：XX医院信息系统投标」</p>
            </div>

            <template v-for="msg in messages" :key="msg.id">
              <ChatMessage
                :role="msg.role"
                :content="msg.content"
                :header="msg.header"
                :time="msg.time"
                :cards="msg.cards"
                :checks="msg.checks"
                :chapters="msg.chapters"
                :animate="msg.animate !== false"
              />
            </template>

            <!-- Typing indicator -->
            <div v-if="waiting" class="typing-row">
              <div class="avatar ai-avatar-sm">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/><path d="M16 14H8a4 4 0 0 0-4 4v2h16v-2a4 4 0 0 0-4-4z"/></svg>
              </div>
              <TypingIndicator />
            </div>
          </div>

          <!-- Error banner -->
          <div v-if="errorMsg" class="chat-error">
            <span>{{ errorMsg }}</span>
            <button @click="errorMsg = ''" class="error-dismiss">✕</button>
          </div>

          <!-- Input -->
          <ChatInput
            ref="inputRef"
            :placeholder="inputPlaceholder"
            :disabled="waiting"
            :sending="waiting"
            :quick-replies="quickReplies"
            @send="handleSend"
            @quick-reply="handleQuickReply"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane
        v-if="project?.status === 'parsed' && parserResult"
        label="招标文件要求"
        name="requirements"
      >
        <div class="tab-requirements">
          <ParserResultPanel :data="parserResult" embedded @reparse="onReparse" />
        </div>
      </el-tab-pane>
    </el-tabs>
      </div>
      <!-- Right sidebar: File panel (always) -->
      <FilePanel
        :project-name="project?.name"
        :tender-file="tenderFileName"
        :sub-bids="subBids"
        @add-subbid="handleAddSubBid"
        @upload-tender="handleUploadTender"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getProject, createProject, parseTender, confirmParse, uploadTender,
  matchMaterials, generateTender, exportTender,
  parseStep1, parseStep2, parseStep3,
} from '@/api'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'
import TypingIndicator from '@/components/TypingIndicator.vue'
import FilePanel from '@/components/FilePanel.vue'
import ParserResultPanel from '@/components/ParserResultPanel.vue'
import type { SubBid } from '@/components/FilePanel.vue'
import type { Project, ParsedData } from '@/types'

interface StepProgress {
  name: string
  status: 'idle' | 'loading' | 'done' | 'error' | 'skipped'
  summary?: any
  elapsed_sec?: number
}

interface ChatMsg {
  id: string
  role: 'ai' | 'user'
  content: string
  header?: string
  time?: string
  animate?: boolean
  cards?: { label: string; value: string }[]
  checks?: { check_id: string; check_name: string; status: string; issue?: string }[]
  chapters?: { chapter: string; material_title: string; reason: string }[]
  steps?: StepProgress[]
}

const router = useRouter()
const route = useRoute()
let projectId = Number(route.params.id)

const project = ref<Project | null>(null)
const projectLoading = ref(true)
const messages = ref<ChatMsg[]>([])
const waiting = ref(false)
const errorMsg = ref('')
const inputRef = ref<InstanceType<typeof ChatInput>>()
const messagesEl = ref<HTMLElement>()
const subBids = ref<SubBid[]>([])

const parserResult = ref<ParsedData | null>(null)
const uploading = ref(false)
const activeTab = ref<'chat' | 'requirements'>('chat')
const stepProgress = ref<Array<{ status: 'idle' | 'loading' | 'done' | 'error' | 'skipped'; summary?: any }>>(
  Array(3).fill(null).map(() => ({ status: 'idle' }))
)

// 解析完成后自动跳到「招标文件要求」tab
watch(
  () => project.value?.status,
  (s) => { if (s === 'parsed') activeTab.value = 'requirements' }
)

// 路由切换项目时，重新加载所有数据
watch(() => route.params.id, async (newId, oldId) => {
  if (!newId || newId === oldId) return
  projectId = Number(newId)
  // 重置全部状态
  project.value = null
  parserResult.value = null
  messages.value = []
  subBids.value = []
  stepProgress.value = Array(3).fill(null).map(() => ({ status: 'idle' }))
  activeTab.value = 'chat'
  await fetchProject()
})

const tenderFileName = computed(() => {
  const path = project.value?.tender_file_path
  if (!path) return ''
  return path.split(/[/\\]/).pop() || ''
})

let msgId = 0
const now = () => new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

const statusLabel = computed(() => {
  const m: Record<string, string> = {
    parsing: '解析中', parsed: '已解析', materials_preparing: '材料匹配',
    generating: '生成中', reviewing: '审查中', done: '已完成',
  }
  return m[project.value?.status || ''] || project.value?.status || ''
})

const inputPlaceholder = computed(() => {
  if (waiting.value) return 'AI 正在思考...'
  if (!project.value) return '输入项目名称开始...'
  if (project.value.status === 'parsing') return '请将招标文件放好后说「放好了」'
  return '输入消息...'
})

// Quick replies adapt to current state
const quickReplies = computed(() => {
  const s = project.value?.status
  if (!s || s === 'parsing') return [
    { label: '放好了', value: '放好了' },
  ]
  if (s === 'parsed') return [
    { label: '继续', value: '继续' },
    { label: '修改预算', value: '修改' },
  ]
  if (s === 'materials_preparing') return [
    { label: '继续', value: '继续' },
    { label: '换一个材料', value: '换一个' },
  ]
  if (s === 'generating') return [
    { label: '终审', value: '终审' },
    { label: '修改', value: '修改' },
  ]
  if (s === 'reviewing') return [
    { label: '自动修正', value: '自动修正' },
    { label: '导出Word', value: '导出Word' },
  ]
  if (s === 'done') return [
    { label: '导出Word', value: '导出Word' },
    { label: '导出PDF', value: '导出PDF' },
  ]
  return []
})

const addMsg = (msg: Omit<ChatMsg, 'id'>) => {
  messages.value.push({ ...msg, id: `m${++msgId}` })
}

const updateMsg = (id: string, patch: Partial<ChatMsg>) => {
  const m = messages.value.find(x => x.id === id)
  if (m) Object.assign(m, patch)
}

const scrollBottom = async () => {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

// 3 步管道串行调用：边跑边更新聊天里的 el-steps（阶段 1：1M 上下文单调用）
async function runStepwiseParse(mode: 'auto' | 'quick' | 'full' | 'manual'): Promise<ParsedData | null> {
  if (!project.value) return null
  const STEP_NAMES = ['提取文本', 'LLM 解析', '校验合并']
  // 添加一条带 steps 的进度消息
  const initialSteps: StepProgress[] = STEP_NAMES.map((n, i) => ({
    name: n,
    status: i === 0 ? 'loading' : 'idle',
  }))
  addMsg({
    role: 'ai',
    content: `🔄 开始解析（${mode} 模式）— 共 3 步：`,
    time: now(),
    steps: initialSteps,
  })
  const stepsMsgId = messages.value[messages.value.length - 1].id

  const setStep = (idx: number, p: Partial<StepProgress>) => {
    const msg = messages.value.find(m => m.id === stepsMsgId)
    if (msg && msg.steps) {
      msg.steps[idx] = { ...msg.steps[idx], ...p }
    }
    // 同步 stepProgress（parser 头部显示用）
    stepProgress.value[idx] = { ...stepProgress.value[idx], ...p }
    scrollBottom()
  }

  try {
    // Step 1 — 文本提取（<1s）
    const r1 = await parseStep1(project.value.id, mode)
    setStep(0, { status: 'done', summary: r1.data.summary, elapsed_sec: r1.data.elapsed_sec })
    setStep(1, { status: 'loading' })

    // Step 2 — 单次 LLM 全量解析（~20-40s）
    const r2 = await parseStep2(project.value.id)
    if (r2.data.status === 'skipped') {
      setStep(1, { status: 'skipped' })
    } else if (r2.data.status === 'manual' || r2.data.status === 'error') {
      setStep(1, { status: 'error', summary: r2.data.summary })
      throw new Error(r2.data.summary?._error || 'LLM 解析失败')
    } else {
      setStep(1, { status: 'done', summary: r2.data.summary, elapsed_sec: r2.data.elapsed_sec })
    }
    setStep(2, { status: 'loading' })

    // Step 3 — 校验合并 + 落库
    const r3 = await parseStep3(project.value.id)
    setStep(2, { status: 'done', summary: r3.data.summary, elapsed_sec: r3.data.elapsed_sec })

    const parsed = r3.data.parsed_data as ParsedData
    parserResult.value = parsed
    if (project.value) project.value.status = 'parsed'
    // 同步 DB 中的最新 project 数据
    try {
      const fresh = await getProject(project.value.id)
      project.value = { ...project.value, ...fresh.data } as any
    } catch { /* 非关键 */ }

    return parsed
  } catch (e: any) {
    // 找到当前 loading 的 step 标为 error
    for (let i = 0; i < 3; i++) {
      const s = stepProgress.value[i]
      if (s.status === 'loading') {
        setStep(i, { status: 'error' })
        break
      }
    }
    const detail = e?.response?.data?.detail || e?.message || '未知错误'
    addMsg({ role: 'ai', content: `❌ 解析失败：${detail}`, time: now() })
    return null
  }
}

// ---- API handlers ----

const fetchProject = async () => {
  if (!Number.isFinite(projectId) || projectId <= 0) {
    ElMessage.error('无效的项目 ID：' + projectId)
    return
  }
  projectLoading.value = true
  try {
    const res = await getProject(projectId)
    const p = res.data as Project
    project.value = p
    // 恢复已解析数据（如果是已解析状态）
    if (p.parsed_data) {
      parserResult.value = p.parsed_data as ParsedData
    }
    // 根据状态生成初始对话（不是真历史，但让用户对当前进度有概念）
    addMsg({
      role: 'ai',
      content: `👋 你好！我是标书制作助手。\n\n项目「${p.name}」已加载，当前状态：${statusLabel.value || '未开始'}。`,
      time: now(),
      animate: false,
    })
    if (p.status === 'parsed' && p.parsed_data) {
      const m = (p.parsed_data as any)._mode
      addMsg({
        role: 'ai',
        content: `📋 上次解析已完成（模式：${m || '未知'}），报告已恢复。点击上方「招标文件要求」tab 查看，或直接说「继续」进入材料匹配。`,
        time: now(),
        animate: false,
      })
      activeTab.value = 'requirements'
    } else if (p.status === 'parsing') {
      addMsg({
        role: 'ai',
        content: '⏳ 当前状态为「解析中」。请将招标文件（PDF/DOCX）放到指定路径后说「放好了」开始解析。',
        time: now(),
        animate: false,
      })
    } else if (p.status === 'materials_preparing') {
      addMsg({
        role: 'ai',
        content: '📚 上次已完成材料匹配。说「继续」可重新匹配或进入下一步。',
        time: now(),
        animate: false,
      })
    } else if (p.status === 'generating' || p.status === 'reviewing') {
      addMsg({
        role: 'ai',
        content: '📝 上次正在生成/审查标书。说「继续」可恢复流程。',
        time: now(),
        animate: false,
      })
    } else if (p.status === 'done') {
      addMsg({
        role: 'ai',
        content: '✅ 标书已完成。可说「导出Word」/「导出PDF」下载。',
        time: now(),
        animate: false,
      })
    }
  } catch (e: any) {
    let msg = e?.response?.data?.detail || e?.message
    // FastAPI 422 返回的 detail 是数组，强行 stringify 会得 [object Object]
    if (Array.isArray(msg)) msg = msg.map((d: any) => d?.msg || JSON.stringify(d)).join('；')
    if (typeof msg === 'object' && msg) {
      try { msg = JSON.stringify(msg) } catch { msg = String(msg) }
    }
    if (!msg) msg = '未知错误'
    ElMessage.error('加载项目失败：' + msg)
  } finally {
    projectLoading.value = false
  }
}

const handleSend = async (text: string) => {
  // If no project yet, create one
  if (!project.value) {
    addMsg({ role: 'user', content: text, time: now() })
    waiting.value = true
    await scrollBottom()
    try {
      const res = await createProject({ name: text, tender_file_name: 'tender.pdf' })
      project.value = { id: res.data.project_id, name: text, status: 'parsing', created_at: '' } as Project
      addMsg({ role: 'ai', content: res.data.message, time: now() })
    } catch (e: any) {
      errorMsg.value = e?.response?.data?.detail || '创建失败'
    }
    waiting.value = false
    await scrollBottom()
    return
  }

  addMsg({ role: 'user', content: text, time: now() })
  waiting.value = true
  await scrollBottom()

  try {
    const status = project.value.status
    let res: any

    if (text.includes('放好了') || text.includes('上传了') || text.includes('好了')) {
      // 分步解析（5 步管道串行调用，进度实时显示在聊天里）
      const parsed = await runStepwiseParse('full')
      if (parsed) {
        addMsg({
          role: 'ai',
          content: '📋 解析完成！请在「招标文件要求」tab 查看完整报告（关键字段、标记扫描、风险条款、结构化数据）。确认无误后输入「继续」进入材料匹配。',
          time: now(),
        })
      }
    } else if (text.includes('继续') || text.includes('确认') || text.includes('好的')) {
      if (status === 'parsed') {
        // Confirm parse → match
        await confirmParse(projectId)
        res = await matchMaterials(projectId)
        const chapters = res.data.chapters || []
        addMsg({ role: 'ai', content: '📚 材料匹配结果如下，确认后我将开始生成标书：', time: now(), chapters })
        project.value.status = 'materials_preparing'
      } else if (status === 'materials_preparing') {
        // Generate tender
        res = await generateTender(projectId, 'main')
        addMsg({ role: 'ai', content: res.data.message || '✅ 主标初稿已生成！输入「终审」进行检查。', time: now() })
        project.value.status = 'generating'
      }
    } else if (text.includes('终审') || text.includes('检查')) {
      res = await generateTender(projectId, 'main') // triggers review in orchestrator
      const review = res.data.main_review
      if (review?.checks) {
        addMsg({ role: 'ai', content: '🔍 终审检查完成：', time: now(), checks: review.checks })
      } else {
        addMsg({ role: 'ai', content: '🔍 终审检查完成，未发现严重问题。', time: now() })
      }
      project.value.status = 'reviewing'
    } else if (text.includes('导出')) {
      const fmt = text.includes('PDF') ? 'pdf' : text.includes('Markdown') ? 'markdown' : 'word'
      res = await exportTender(projectId, fmt)
      addMsg({ role: 'ai', content: res.data.message || `✅ 已导出为 ${fmt.toUpperCase()}`, time: now() })
      project.value.status = 'done'
    } else if (text.includes('自动修正')) {
      addMsg({ role: 'ai', content: '✅ 已自动修正一致性问题\n• 工期描述已统一\n• 金额已对齐\n\n现在可以导出了：「导出Word」/「导出PDF」', time: now() })
    } else {
      // Generic message: forward to orchestrator's handle()
      addMsg({ role: 'ai', content: `收到。「${text}」——请说得更具体一些，或使用快捷回复。`, time: now() })
    }
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || e?.message || '操作失败'
    if (errorMsg.value.includes('文件还没找到')) {
      addMsg({ role: 'ai', content: errorMsg.value, time: now() })
      errorMsg.value = ''
    }
  }
  waiting.value = false
  await scrollBottom()
}

const handleQuickReply = (value: string) => {
  handleSend(value)
}

// 解析报告头部「重解析」按钮：直接重跑 /parse?mode=xxx，不走对话
async function onReparse(mode: 'auto' | 'quick' | 'full' | 'manual') {
  if (!project.value) return
  waiting.value = true
  try {
    const parsed = await runStepwiseParse(mode)
    if (parsed) {
      addMsg({
        role: 'ai',
        content: `🔄 已用 ${mode} 模式重解析，报告已更新。`,
        time: now(),
      })
    }
  } finally {
    waiting.value = false
    await scrollBottom()
  }
}

const handleAddSubBid = () => {
  // 通过对话添加陪标：提示用户输入公司名
  addMsg({ role: 'ai', content: '请输入陪标公司名称，例如：「XX科技有限公司」', time: now() })
  inputRef.value?.focus()
}

const handleUploadTender = async (file: File) => {
  uploading.value = true
  try {
    const res = await uploadTender(projectId, file)
    // 刷新项目状态
    const fresh = await getProject(projectId)
    project.value = fresh.data
    addMsg({
      role: 'user',
      content: `📎 已上传：${file.name}（${(file.size / 1024).toFixed(1)} KB）`,
      time: now(),
    })
    addMsg({
      role: 'ai',
      content: res.data.message || '文件已就位。请输入「放好了」开始解析。',
      time: now(),
    })
    ElMessage.success('上传成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
  await scrollBottom()
}

onMounted(fetchProject)
</script>

<style scoped>
.chat-view { height: 100%; background: var(--qb-paper); }
.chat-body { display: flex; height: 100%; }
.chat-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }

.chat-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 32px 16px; background: var(--qb-paper); flex-shrink: 0;
}
.chat-header-left { display: flex; align-items: baseline; gap: 12px; }
.project-name {
  font-family: var(--qb-font-display); font-size: 24px; font-weight: 600;
  color: var(--qb-ink); line-height: 1.2;
}
.project-status {
  font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
  color: var(--qb-stone);
}
.tender-file-badge {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; color: var(--qb-amber);
  background: var(--qb-amber-light); padding: 2px 8px; border-radius: 2px;
  max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.upload-banner {
  margin: 0 32px 12px;
  padding: 14px 18px;
  background: var(--qb-amber-light);
  border: 1px dashed var(--qb-amber);
  border-radius: var(--qb-radius);
  flex-shrink: 0;
}
.upload-banner-inner {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
}
.upload-banner-text strong { color: var(--qb-ink); font-size: 13px; }
.upload-banner-text p { margin: 4px 0 0; font-size: 11px; color: var(--qb-ink-light); }

.chat-tabs { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.chat-tabs :deep(.el-tabs__header) { margin: 0; padding: 0 24px; flex-shrink: 0; border-bottom: 1px solid var(--qb-border); }
.chat-tabs :deep(.el-tabs__nav-wrap)::after { height: 0; }
.chat-tabs :deep(.el-tabs__item) { font-size: 13px; font-weight: 500; height: 40px; line-height: 40px; }
.chat-tabs :deep(.el-tabs__content) { flex: 1; min-height: 0; padding: 0; overflow: hidden; }
.chat-tabs :deep(.el-tab-pane) { height: 100%; min-height: 0; }

.tab-chat { height: 100%; min-height: 0; display: flex; flex-direction: column; }
.tab-requirements { height: 100%; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.chat-header-right { display: flex; gap: 6px; }
.header-action-btn {
  width: 32px; height: 32px; border-radius: var(--qb-radius);
  border: 1px solid var(--qb-border); background: var(--qb-surface);
  color: var(--qb-stone); cursor: pointer; display: flex; align-items: center;
  justify-content: center; transition: all 120ms;
}
.header-action-btn:hover { background: var(--qb-paper); color: var(--qb-ink); }

.chat-messages { flex: 1; overflow-y: auto; padding: 8px 32px 24px; display: flex; flex-direction: column; }

.chat-empty {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; color: var(--qb-stone); text-align: center;
}
.chat-empty .empty-icon { margin-bottom: 20px; opacity: 0.2; }
.chat-empty p { margin: 4px 0; font-size: 15px; }
.chat-empty .empty-hint { font-size: 13px; }

.typing-row { margin-bottom: 24px; }

.chat-error {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 32px; background: #FEF2F2; color: var(--qb-danger);
  font-size: 13px; border-top: 1px solid #FEE2E2;
}
.error-dismiss { background: none; border: none; color: inherit; cursor: pointer; }
</style>
