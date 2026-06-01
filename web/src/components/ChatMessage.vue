<template>
  <div class="chat-msg" :class="[role, { 'anim-fade-up': animate }]">
    <!-- AI avatar -->
    <div v-if="role === 'ai'" class="msg-avatar ai-avatar">
      <svg width="16" height="16" viewBox="0 0 32 32" fill="none">
        <rect x="5" y="10" width="22" height="14" rx="2" stroke="currentColor" stroke-width="1.6"/>
        <line x1="8" y1="15" x2="16" y2="15" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
        <line x1="8" y1="19" x2="20" y2="19" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      </svg>
    </div>

    <div class="msg-body">
      <!-- Bubble -->
      <div class="msg-bubble" :class="{ 'has-cards': cards?.length, 'has-checks': checks?.length }">
        <div v-if="header" class="msg-header">{{ header }}</div>
        <div class="msg-text" v-html="rendered" />

        <!-- K01-K14 cards -->
        <div v-if="cards?.length" class="msg-cards">
          <div v-for="c in cards" :key="c.label" class="k-card">
            <span class="k-label">{{ c.label }}</span>
            <span class="k-value">{{ c.value }}</span>
          </div>
        </div>

        <!-- Review checklist -->
        <div v-if="checks?.length" class="msg-checks">
          <div v-for="c in checks" :key="c.check_id" class="check-row" :class="c.status">
            <span class="check-dot" /> {{ c.check_name }}
            <span v-if="c.issue" class="check-note">{{ c.issue }}</span>
          </div>
        </div>

        <!-- Chapters -->
        <div v-if="chapters?.length" class="msg-chapters">
          <div v-for="ch in chapters" :key="ch.chapter" class="ch-row">
            <div class="ch-name">{{ ch.chapter }}</div>
            <div class="ch-material">{{ ch.material_title }}</div>
          </div>
        </div>
      </div>

      <div v-if="time" class="msg-time">{{ time }}</div>
    </div>

    <!-- User avatar -->
    <div v-if="role === 'user'" class="msg-avatar user-avatar">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-7 8-7s8 3 8 7"/></svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  role: 'ai' | 'user'
  content?: string
  header?: string
  time?: string
  animate?: boolean
  cards?: { label: string; value: string }[]
  checks?: { check_id: string; check_name: string; status: string; issue?: string }[]
  chapters?: { chapter: string; material_title: string; reason?: string }[]
}>(), { animate: true })

const rendered = computed(() => {
  if (!props.content) return ''
  return props.content
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
})
</script>

<style scoped>
.chat-msg {
  display: flex;
  gap: 10px;
  margin-bottom: 22px;
  max-width: 82%;
}
.chat-msg.ai { align-self: flex-start; }
.chat-msg.user { align-self: flex-end; flex-direction: row-reverse; }

/* Avatar */
.msg-avatar {
  width: 32px; height: 32px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.ai-avatar { background: var(--qb-primary-pale); color: var(--qb-primary); }
.user-avatar { background: var(--qb-primary); color: white; border-radius: 50%; }

/* Body */
.msg-body { min-width: 0; }

/* Bubble */
.msg-bubble {
  padding: 14px 18px;
  border-radius: var(--qb-radius);
  line-height: 1.65;
  font-size: 14px;
  position: relative;
}
.ai .msg-bubble {
  background: var(--qb-ai-bubble);
  border: 1px solid var(--qb-ai-bubble-border);
  color: var(--qb-ink);
  border-bottom-left-radius: 4px;
}
.user .msg-bubble {
  background: var(--qb-primary);
  color: var(--qb-user-text);
  border-bottom-right-radius: 4px;
}
.msg-bubble.has-cards,
.msg-bubble.has-checks { padding: 18px 20px; }

.msg-header {
  font-size: 10px; font-weight: 700; letter-spacing: 1px;
  text-transform: uppercase; margin-bottom: 8px;
  opacity: 0.5;
}

.msg-text { word-break: break-word; }
.msg-text :deep(strong) { font-weight: 600; color: inherit; }
.msg-text :deep(code) {
  font-family: var(--qb-font-mono); font-size: 0.9em;
  background: rgba(0,0,0,0.06); padding: 1px 6px; border-radius: 3px;
}

.msg-time { font-size: 10px; margin-top: 4px; opacity: 0.35; padding: 0 4px; }
.user .msg-time { text-align: right; }

/* K-cards grid */
.msg-cards {
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px;
  margin-top: 14px; padding-top: 12px;
  border-top: 1px solid rgba(0,0,0,0.06);
}
.k-card {
  background: rgba(255,255,255,0.6); border-radius: 6px; padding: 8px 10px;
}
.k-label {
  display: block; font-size: 9px; text-transform: uppercase;
  letter-spacing: 0.5px; opacity: 0.5; margin-bottom: 2px;
}
.k-value { font-size: 13px; font-weight: 500; color: var(--qb-ink); }

/* Review checks */
.msg-checks { margin-top: 14px; }
.check-row {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 0; font-size: 13px; border-bottom: 1px solid rgba(0,0,0,0.04);
}
.check-row:last-child { border-bottom: none; }
.check-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  background: var(--qb-success);
}
.check-row.warning .check-dot { background: var(--qb-accent); }
.check-row.fail .check-dot { background: var(--qb-danger); }
.check-note { font-size: 12px; opacity: 0.6; margin-left: auto; }

/* Chapters */
.msg-chapters { margin-top: 12px; }
.ch-row {
  padding: 8px 10px; margin-bottom: 4px;
  background: rgba(255,255,255,0.5); border-radius: 6px;
}
.ch-name { font-weight: 600; font-size: 13px; color: var(--qb-ink); }
.ch-material { font-size: 12px; color: var(--qb-primary); margin-top: 2px; }
</style>
