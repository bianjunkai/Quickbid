<template>
  <div class="generated-file">
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
    <span class="gf-name">{{ name }}</span>
    <span class="gf-badge">AI</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ name: string }>()
</script>

<style scoped>
.generated-file {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 4px;
  font-size: 11px;
  color: var(--qb-text);
}
.generated-file svg { color: var(--qb-primary); flex-shrink: 0; }
.gf-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gf-badge {
  font-size: 8px;
  padding: 1px 4px;
  border-radius: 4px;
  background: #DBEAFE;
  color: var(--qb-primary);
  font-weight: 600;
  flex-shrink: 0;
}
</style>
