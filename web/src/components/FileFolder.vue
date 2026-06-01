<template>
  <div class="fr" :class="{ open }">
    <div class="fr-row" @click="open = !open">
      <svg class="fr-chev" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6" /></svg>
      <span class="fr-name">{{ name }}</span>
    </div>
    <div v-if="open" class="fr-sub">
      <slot><div class="fr-empty">—</div></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
defineProps<{ name: string; icon?: string; kind?: string }>()
const open = ref(false)
</script>

<style scoped>
.fr { margin-bottom: 1px; }
.fr-row {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 6px; cursor: pointer; border-radius: 2px;
  font-size: 12px; color: var(--qb-ink-light); transition: background 100ms;
}
.fr-row:hover { background: var(--qb-paper); }
.fr-chev { color: var(--qb-stone); transition: transform 120ms; flex-shrink:0; }
.open .fr-chev { transform: rotate(90deg); }
.fr-name { flex:1; }
.fr-sub { padding: 4px 0 4px 16px; }
.fr-empty { font-size: 11px; color: var(--qb-stone); padding: 2px 4px; }
</style>
