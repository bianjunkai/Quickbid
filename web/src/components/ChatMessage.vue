<template>
  <div class="chat-message" :class="[role, { 'anim-fade-up': animate }]">
    <!-- AI avatar -->
    <div v-if="role === 'ai'" class="avatar ai-avatar">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/><path d="M16 14H8a4 4 0 0 0-4 4v2h16v-2a4 4 0 0 0-4-4z"/></svg>
    </div>

    <!-- Bubble -->
    <div class="bubble">
      <!-- Header (optional) -->
      <div v-if="header" class="bubble-header">{{ header }}</div>

      <!-- Markdown / text content -->
      <div class="bubble-content" v-html="renderedContent" />

      <!-- Data cards (parsed data, match results, review results) -->
      <div v-if="cards && cards.length" class="cards">
        <div v-for="(card, i) in cards" :key="i" class="data-card">
          <div class="data-card-label">{{ card.label }}</div>
          <div class="data-card-value">{{ card.value }}</div>
        </div>
      </div>

      <!-- Review checks -->
      <div v-if="checks && checks.length" class="checks">
        <div v-for="c in checks" :key="c.check_id" class="check-row" :class="c.status">
          <span class="check-icon">{{ c.status === 'pass' ? '✓' : c.status === 'warning' ? '!' : '✕' }}</span>
          <span class="check-name">{{ c.check_name }}</span>
          <span v-if="c.issue" class="check-issue">{{ c.issue }}</span>
        </div>
      </div>

      <!-- Material match chapters -->
      <div v-if="chapters && chapters.length" class="chapters">
        <div v-for="(ch, i) in chapters" :key="i" class="chapter-item">
          <div class="chapter-name">{{ ch.chapter }}</div>
          <div class="chapter-material">→ {{ ch.material_title }}</div>
          <div class="chapter-reason">{{ ch.reason }}</div>
        </div>
      </div>

      <!-- Timestamp -->
      <div v-if="time" class="bubble-time">{{ time }}</div>
    </div>

    <!-- User avatar -->
    <div v-if="role === 'user'" class="avatar user-avatar">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-7 8-7s8 3 8 7"/></svg>
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
  chapters?: { chapter: string; material_title: string; reason: string }[]
}>(), { animate: true })

const renderedContent = computed(() => {
  if (!props.content) return ''
  // Simple markdown: **bold**, `code`, newlines
  return props.content
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
})
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  max-width: 85%;
}

.chat-message.ai { align-self: flex-start; }
.chat-message.user { align-self: flex-end; flex-direction: row-reverse; }

/* Avatar */
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ai-avatar {
  background: var(--qb-primary-light);
  color: var(--qb-primary);
}
.user-avatar {
  background: var(--qb-primary);
  color: white;
}

/* Bubble */
.bubble {
  padding: 12px 16px;
  border-radius: var(--qb-radius);
  line-height: 1.6;
  min-width: 0;
}
.ai .bubble {
  background: var(--qb-primary-light);
  color: var(--qb-text);
  border: 1px solid #DBEAFE;
}
.user .bubble {
  background: var(--qb-user-bubble);
  color: var(--qb-user-text);
}

.bubble-header {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 6px;
  opacity: 0.7;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.bubble-content { word-break: break-word; }
.bubble-content :deep(strong) { font-weight: 600; }
.bubble-content :deep(code) {
  background: rgba(0,0,0,0.06);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 13px;
}

.bubble-time {
  margin-top: 6px;
  font-size: 11px;
  opacity: 0.5;
}

/* Data cards (K01-K14) */
.cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-top: 10px;
}
.data-card {
  background: rgba(255,255,255,0.7);
  border-radius: var(--qb-radius-sm);
  padding: 8px 10px;
  border: 1px solid rgba(0,0,0,0.04);
}
.data-card-label {
  font-size: 11px;
  color: var(--qb-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 2px;
}
.data-card-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--qb-text);
}

/* Review checks */
.checks { margin-top: 10px; }
.check-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 5px 0;
  font-size: 13px;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.check-row:last-child { border-bottom: none; }
.check-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}
.check-row.pass .check-icon { background: #DCFCE7; color: var(--qb-success); }
.check-row.warning .check-icon { background: #FEF3C7; color: var(--qb-warning); }
.check-row.fail .check-icon { background: #FEE2E2; color: var(--qb-danger); }
.check-name { flex: 1; }
.check-issue { color: var(--qb-warning); font-size: 12px; }

/* Chapters */
.chapters { margin-top: 10px; }
.chapter-item {
  padding: 8px 10px;
  margin-bottom: 4px;
  background: rgba(255,255,255,0.6);
  border-radius: var(--qb-radius-sm);
}
.chapter-name { font-weight: 600; font-size: 13px; }
.chapter-material { color: var(--qb-primary); font-size: 13px; margin: 2px 0; }
.chapter-reason { color: var(--qb-text-secondary); font-size: 12px; }
</style>
