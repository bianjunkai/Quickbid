<template>
  <div class="entry" :class="[role, { 'anim-fade-in': animate }]">
    <!-- Label -->
    <div class="entry-label">{{ role === 'ai' ? '系统' : '你' }}</div>

    <!-- Body -->
    <div class="entry-body">
      <div v-if="header" class="entry-header">{{ header }}</div>
      <div class="entry-text" v-html="rendered" />

      <!-- K01-K14 cards -->
      <div v-if="cards?.length" class="entry-grid">
        <div v-for="c in cards" :key="c.label" class="k-card">
          <span class="k-label">{{ c.label }}</span>
          <span class="k-value">{{ c.value }}</span>
        </div>
      </div>

      <!-- Review checks -->
      <div v-if="checks?.length" class="entry-checks">
        <div v-for="c in checks" :key="c.check_id" class="chk-row" :class="c.status">
          <span class="chk-mark">{{ c.status === 'pass' ? '✓' : c.status === 'warning' ? '!' : '✕' }}</span>
          <span class="chk-name">{{ c.check_name }}</span>
          <span v-if="c.issue" class="chk-note">{{ c.issue }}</span>
        </div>
      </div>

      <!-- Chapters -->
      <div v-if="chapters?.length" class="entry-chapters">
        <div v-for="ch in chapters" :key="ch.chapter" class="ch-row">
          <div class="ch-name">{{ ch.chapter }}</div>
          <div class="ch-mat">{{ ch.material_title }}</div>
          <div v-if="ch.reason" class="ch-reason">{{ ch.reason }}</div>
        </div>
      </div>

      <!-- Step progress（5 步管道进度条） -->
      <div v-if="steps?.length" class="entry-steps">
        <el-steps :active="stepsActive" finish-status="success" align-center size="small">
          <el-step
            v-for="(s, i) in steps" :key="i"
            :title="s.name"
            :description="stepDesc(s)"
            :status="s.status === 'loading' ? 'process' : s.status === 'error' ? 'error' : s.status === 'skipped' ? 'wait' : (s.status === 'done' ? 'success' : 'wait')"
          />
        </el-steps>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  role: 'ai' | 'user'
  content?: string; header?: string; time?: string; animate?: boolean
  cards?: { label: string; value: string }[]
  checks?: { check_id: string; check_name: string; status: string; issue?: string }[]
  chapters?: { chapter: string; material_title: string; reason?: string }[]
  steps?: { name: string; status: 'idle' | 'loading' | 'done' | 'error' | 'skipped'; summary?: any; elapsed_sec?: number }[]
}>(), { animate: true })

const rendered = computed(() => {
  if (!props.content) return ''
  return props.content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/`(.+?)`/g, '<code>$1</code>').replace(/\n/g, '<br>')
})

// el-steps 的 active 是「完成到第几步」，0 表示还没开始
const stepsActive = computed(() => {
  if (!props.steps) return 0
  const done = props.steps.filter(s => s.status === 'done' || s.status === 'skipped').length
  return done
})

function stepDesc(s: any): string {
  if (s.status === 'skipped') return '（当前模式不需要）'
  if (s.status === 'loading') return '进行中...'
  if (s.status === 'error') return '失败'
  if (s.status === 'idle') return '等待'
  if (s.status === 'done') {
    const sum = s.summary || {}
    const t = s.elapsed_sec != null ? ` · ${s.elapsed_sec}s` : ''
    // 阶段 1：3 步管道（提取文本 / LLM 解析 / 校验合并）
    if (s.name === '提取文本') return `${sum.text_length || 0} 字符${t}`
    if (s.name === 'LLM 解析') {
      const k = sum.k_filled ?? 0
      const m = (sum.modules_filled || []).length
      return `K ${k}/14 · 模块 ${m}/8${t}`
    }
    if (s.name === '校验合并') return `${sum.validation_issues || 0} 问题${t}`
    return t
  }
  return ''
}
</script>

<style scoped>
.entry {
  display: flex; gap: 16px; margin-bottom: 24px; max-width: 88%;
}
.entry.ai { align-self: flex-start; }
.entry.user { align-self: flex-end; flex-direction: row-reverse; }

/* Label — replaces avatar */
.entry-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.8px; padding-top: 4px; flex-shrink: 0;
  width: 36px;
}
.ai .entry-label { color: var(--qb-stone); }
.user .entry-label { color: var(--qb-ink-light); text-align: right; }

/* Body */
.entry-body { min-width: 0; }

/* AI entry: clean typographic card */
.ai .entry-body {
  background: none; border: none;
  border-left: 2px solid var(--qb-border); padding-left: 16px;
}

/* User entry: subtle warm card */
.user .entry-body {
  background: var(--qb-paper); border: 1px solid var(--qb-border);
  border-radius: var(--qb-radius); padding: 12px 16px;
}

.entry-header {
  font-size: 10px; font-weight: 700; letter-spacing: 0.8px;
  color: var(--qb-stone); text-transform: uppercase; margin-bottom: 6px;
}
.entry-text { font-size: 14px; line-height: 1.7; color: var(--qb-ink); word-break: break-word; }
.entry-text :deep(strong) { font-weight: 600; }
.entry-text :deep(code) {
  font-family: var(--qb-font-mono); font-size: 0.9em;
  background: rgba(0,0,0,0.04); padding: 1px 5px; border-radius: 2px;
}

/* Grid cards */
.entry-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px;
  margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--qb-border);
}
.k-card { background: var(--qb-surface); border: 1px solid var(--qb-border); border-radius: 2px; padding: 8px 10px; }
.k-label { display: block; font-size: 9px; color: var(--qb-stone); text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 2px; }
.k-value { font-size: 13px; font-weight: 500; color: var(--qb-ink); }

/* Checks */
.entry-checks { margin-top: 12px; }
.chk-row { display: flex; align-items: center; gap: 8px; padding: 5px 0; font-size: 13px; border-bottom:1px solid var(--qb-border);}
.chk-row:last-child { border-bottom: none; }
.chk-mark {
  width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; flex-shrink: 0;
}
.chk-row.pass .chk-mark { background: var(--qb-success-light); color: var(--qb-success); }
.chk-row.warning .chk-mark { background: var(--qb-amber-light); color: var(--qb-amber); }
.chk-row.fail .chk-mark { background: #FEE2E2; color: var(--qb-danger); }
.chk-name { flex: 1; }
.chk-note { font-size: 12px; color: var(--qb-amber); }

/* Chapters */
.entry-chapters { margin-top: 10px; }
.entry-steps { margin-top: 12px; padding: 10px 12px; background: var(--qb-surface); border: 1px solid var(--qb-border); border-radius: 2px; }
.ch-row { padding: 8px 10px; margin-bottom: 3px; background: var(--qb-surface); border: 1px solid var(--qb-border); border-radius: 2px; }
.ch-name { font-weight: 600; font-size: 13px; }
.ch-mat { font-size: 12px; color: var(--qb-amber); margin-top: 2px; }
.ch-reason { font-size: 11px; color: var(--qb-stone); margin-top: 1px; }
</style>
