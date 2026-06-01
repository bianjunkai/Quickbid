<template>
  <div class="folder" :class="{ expanded }">
    <div class="folder-row" @click="expanded = !expanded">
      <svg class="chevron" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <polyline points="9 18 15 12 9 6" />
      </svg>
      <svg class="kind-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <template v-if="icon === 'image'">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" />
        </template>
        <template v-else>
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </template>
      </svg>
      <span class="folder-name">{{ name }}</span>
      <span class="kind-badge" :class="kind">{{ kindLabel }}</span>
    </div>
    <div v-if="expanded" class="folder-children">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  name: string
  icon?: string
  kind?: 'agent' | 'hybrid'  // agent=只读AI产物, hybrid=可上传补充
}>()

const expanded = ref(false)

const kindLabel = computed(() =>
  props.kind === 'agent' ? 'AI' : '上传'
)
</script>

<style scoped>
.folder { margin-bottom: 1px; }

.folder-row {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 6px;
  cursor: pointer;
  border-radius: 5px;
  transition: background var(--qb-transition);
}
.folder-row:hover { background: rgba(37,99,235,0.04); }

.chevron {
  color: var(--qb-text-secondary);
  transition: transform 150ms ease;
  flex-shrink: 0;
}
.expanded .chevron { transform: rotate(90deg); }

.kind-icon { color: var(--qb-text-secondary); flex-shrink: 0; }
.folder-name { font-size: 12px; color: var(--qb-text); flex: 1; }

.kind-badge {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 6px;
  font-weight: 600;
  letter-spacing: 0.3px;
  flex-shrink: 0;
}
.kind-badge.agent { background: #DBEAFE; color: var(--qb-primary); }
.kind-badge.hybrid { background: #FEF3C7; color: #92400E; }

.folder-children {
  padding: 2px 0 2px 19px;
}
</style>
