<template>
  <label class="upload-hint">
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
    <span>补充文件</span>
    <input type="file" hidden @change="onChange" />
  </label>
</template>

<script setup lang="ts">
const emit = defineEmits<{ upload: [file: File] }>()
const onChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) emit('upload', input.files[0])
}
</script>

<style scoped>
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
