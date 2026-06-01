<template>
  <div class="folder" :class="{ expanded }">
    <div class="folder-row" @click="expanded = !expanded">
      <svg class="chevron" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <polyline points="9 18 15 12 9 6" />
      </svg>
      <svg class="folder-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path v-if="icon === 'image'" d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z"/><circle v-if="icon === 'image'" cx="8.5" cy="8.5" r="1.5"/><polyline v-if="icon === 'image'" points="21 15 16 10 5 21"/>
        <path v-else d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      </svg>
      <span class="folder-name">{{ name }}</span>
    </div>
    <div v-if="expanded" class="folder-children">
      <label class="upload-hint">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        <span>添加文件</span>
        <input type="file" hidden />
      </label>
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  name: string
  icon?: string
}>()

const expanded = ref(false)
</script>

<style scoped>
.folder { margin-bottom: 1px; }

.folder-row {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 4px;
  cursor: pointer;
  border-radius: 4px;
  transition: background var(--qb-transition);
}
.folder-row:hover { background: rgba(37,99,235,0.05); }

.chevron {
  color: var(--qb-text-secondary);
  transition: transform 150ms ease;
  flex-shrink: 0;
}
.expanded .chevron { transform: rotate(90deg); }

.folder-icon {
  color: var(--qb-text-secondary);
  flex-shrink: 0;
}
.folder-name {
  font-size: 12px;
  color: var(--qb-text);
}

.folder-children {
  padding: 2px 0 2px 19px;
}

.upload-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  font-size: 11px;
  color: #94A3B8;
  cursor: pointer;
  border-radius: 3px;
  transition: all var(--qb-transition);
}
.upload-hint:hover { color: var(--qb-primary); background: rgba(37,99,235,0.04); }
</style>
