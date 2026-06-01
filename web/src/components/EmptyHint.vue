<template>
  <div class="empty-hint">{{ text }}</div>
</template>

<script setup lang="ts">
defineProps<{ text: string }>()
</script>

<style scoped>
.empty-hint {
  padding: 4px 4px;
  font-size: 11px;
  color: #CBD5E1;
  font-style: italic;
}
</style>
