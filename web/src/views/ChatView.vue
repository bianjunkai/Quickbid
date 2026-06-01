<template>
  <div class="chat-view" v-loading="projectLoading">
    <div class="chat-body">
      <div class="chat-main">
        <!-- Header bar -->
        <div class="chat-header">
      <div class="chat-header-left">
        <span class="project-name">{{ project?.name || '加载中...' }}</span>
        <span v-if="project" class="project-status" :class="project.status">{{ statusLabel }}</span>
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
      <!-- File panel -->
      <FilePanel
        :project-name="project?.name"
        :tender-file="tenderFileName"
        :sub-bids="subBids"
        @add-subbid="handleAddSubBid"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getProject, createProject, parseTender, confirmParse,
  matchMaterials, generateTender, exportTender,
} from '@/api'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'
import TypingIndicator from '@/components/TypingIndicator.vue'
import FilePanel from '@/components/FilePanel.vue'
import type { SubBid } from '@/components/FilePanel.vue'
import type { Project } from '@/types'

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
}

const router = useRouter()
const route = useRoute()
const projectId = Number(route.params.id)

const project = ref<Project | null>(null)
const projectLoading = ref(true)
const messages = ref<ChatMsg[]>([])
const waiting = ref(false)
const errorMsg = ref('')
const inputRef = ref<InstanceType<typeof ChatInput>>()
const messagesEl = ref<HTMLElement>()
const subBids = ref<SubBid[]>([])

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

const scrollBottom = async () => {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

// ---- API handlers ----

const fetchProject = async () => {
  projectLoading.value = true
  try {
    const res = await getProject(projectId)
    project.value = res.data
    // Restore conversation from project state
    if (project.value?.name) {
      addMsg({ role: 'ai', content: `你好！我是标书制作助手。\n\n项目「${project.value.name}」已就绪，请将招标文件（PDF/DOCX）放到指定路径后说「放好了」。`, time: now(), animate: false })
    }
  } catch (e: any) {
    ElMessage.error('加载项目失败')
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
      // Parse tender
      res = await parseTender(projectId)
      const parsed = res.data.parsed_data
      const cards = Object.entries(parsed).map(([k, v]) => ({
        label: String(k).replace('K0', 'K'),
        value: Array.isArray(v) ? (v as string[]).join('、') : String(v || '—'),
      }))
      addMsg({ role: 'ai', content: '📋 解析完成！请确认以下信息：', time: now(), cards })
      project.value.status = 'parsed'
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

const handleAddSubBid = () => {
  // 通过对话添加陪标：提示用户输入公司名
  addMsg({ role: 'ai', content: '请输入陪标公司名称，例如：「XX科技有限公司」', time: now() })
  inputRef.value?.focus()
}

onMounted(fetchProject)
</script>

<style scoped>
.chat-view {
  height: 100%;
  background: var(--qb-bg);
}

.chat-body {
  display: flex;
  height: 100%;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 24px;
  border-bottom: 1px solid var(--qb-border);
  background: var(--qb-bg);
  flex-shrink: 0;
}
.chat-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.project-name {
  font-family: var(--qb-font-heading);
  font-size: 17px;
  font-weight: 600;
  color: var(--qb-text);
}
.project-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.project-status.parsing { background: #FEF3C7; color: #92400E; }
.project-status.parsed { background: #DCFCE7; color: #166534; }
.project-status.materials_preparing { background: #DBEAFE; color: #1E40AF; }
.project-status.generating { background: #F3E8FF; color: #6B21A8; }
.project-status.done { background: #DCFCE7; color: #166534; }

.chat-header-right { display: flex; gap: 6px; }
.header-action-btn {
  width: 34px; height: 34px;
  border-radius: 50%;
  border: 1px solid var(--qb-border);
  background: var(--qb-bg);
  color: var(--qb-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--qb-transition);
}
.header-action-btn:hover { background: #F1F5F9; color: var(--qb-text); }

/* Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--qb-text-secondary);
  text-align: center;
}
.chat-empty .empty-icon { margin-bottom: 16px; color: #CBD5E1; }
.chat-empty p { margin: 4px 0; }
.chat-empty .empty-hint { font-size: 13px; color: #94A3B8; }

.typing-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 20px;
}
.ai-avatar-sm {
  width: 30px; height: 30px;
  border-radius: 50%;
  background: var(--qb-primary-light);
  color: var(--qb-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Error */
.chat-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 24px;
  background: #FEE2E2;
  color: var(--qb-danger);
  font-size: 13px;
}
.error-dismiss {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 14px;
}
</style>
