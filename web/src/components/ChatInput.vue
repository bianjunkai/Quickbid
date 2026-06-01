<template>
  <div class="toolbar">
    <div v-if="quickReplies.length" class="toolbar-chips">
      <button v-for="(qr, i) in quickReplies" :key="i" class="chip" @click="$emit('quick-reply', qr.value)">{{ qr.label }}</button>
    </div>
    <div class="toolbar-row">
      <input
        ref="inputEl" v-model="text" class="toolbar-input"
        :placeholder="placeholder" :disabled="disabled"
        @keydown.enter="send"
      />
      <button class="toolbar-send" :class="{ ready: text.trim() && !disabled }" :disabled="!text.trim() || disabled" @click="send">
        发送
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
withDefaults(defineProps<{
  placeholder?: string; disabled?: boolean; sending?: boolean
  quickReplies?: { label: string; value: string }[]
}>(), { placeholder: '输入消息...' })

const emit = defineEmits<{ send: [text: string]; 'quick-reply': [value: string] }>()
const text = ref('')
const inputEl = ref<HTMLInputElement>()
const send = () => { const v = text.value.trim(); if (!v) return; emit('send', v); text.value = '' }
defineExpose({ focus: () => inputEl.value?.focus() })
</script>

<style scoped>
.toolbar { padding: 16px 24px; border-top: 1px solid var(--qb-border); background: var(--qb-surface); }
.toolbar-chips { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.chip {
  padding: 5px 14px; font-size: 12px; font-family: var(--qb-font-body);
  font-weight: 500; color: var(--qb-ink-light); background: var(--qb-surface);
  border: 1px solid var(--qb-border); border-radius: var(--qb-radius); cursor: pointer;
  transition: all 120ms;
}
.chip:hover { background: var(--qb-ink); color: white; border-color: var(--qb-ink); }

.toolbar-row { display: flex; gap: 10px; }
.toolbar-input {
  flex: 1; padding: 10px 14px; font-size: 14px; font-family: var(--qb-font-body);
  color: var(--qb-ink); background: var(--qb-paper); border: 1px solid var(--qb-border);
  border-radius: var(--qb-radius); outline: none; transition: border-color 120ms;
}
.toolbar-input:focus { border-color: var(--qb-ink); }
.toolbar-input::placeholder { color: var(--qb-stone); }
.toolbar-input:disabled { opacity: 0.5; }

.toolbar-send {
  padding: 10px 24px; font-size: 14px; font-family: var(--qb-font-body); font-weight: 500;
  color: var(--qb-stone); background: var(--qb-paper); border: 1px solid var(--qb-border);
  border-radius: var(--qb-radius); cursor: pointer; transition: all 120ms;
}
.toolbar-send.ready { background: var(--qb-ink); color: white; border-color: var(--qb-ink); }
.toolbar-send.ready:hover { background: var(--qb-ink-light); }
.toolbar-send:disabled { cursor: not-allowed; }
</style>
