<template>
  <div class="chat-input-area">
    <!-- Quick replies -->
    <div v-if="quickReplies.length" class="quick-replies">
      <button
        v-for="(qr, i) in quickReplies" :key="i"
        class="quick-reply-btn"
        @click="$emit('quick-reply', qr.value)"
      >{{ qr.label }}</button>
    </div>

    <!-- Input row -->
    <div class="input-row">
      <input
        ref="inputEl"
        v-model="text"
        class="chat-input"
        :placeholder="placeholder"
        :disabled="disabled"
        @keydown.enter="send"
      />
      <button
        class="send-btn"
        :disabled="!text.trim() || disabled"
        @click="send"
        :title="'发送'"
      >
        <svg v-if="!sending" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        <span v-else class="sending-dot" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  placeholder?: string
  disabled?: boolean
  sending?: boolean
  quickReplies?: { label: string; value: string }[]
}>(), {
  placeholder: '输入消息...',
})

const emit = defineEmits<{
  send: [text: string]
  'quick-reply': [value: string]
}>()

const text = ref('')
const inputEl = ref<HTMLInputElement>()

const send = () => {
  const val = text.value.trim()
  if (!val || props.disabled) return
  emit('send', val)
  text.value = ''
}

defineExpose({ focus: () => inputEl.value?.focus() })
</script>

<style scoped>
.chat-input-area {
  padding: 16px 24px;
  border-top: 1px solid var(--qb-border);
  background: var(--qb-bg);
}

.quick-replies {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.quick-reply-btn {
  padding: 6px 14px;
  font-size: 13px;
  font-family: var(--qb-font-body);
  color: var(--qb-primary);
  background: var(--qb-primary-light);
  border: 1px solid #DBEAFE;
  border-radius: 20px;
  cursor: pointer;
  transition: all var(--qb-transition);
  white-space: nowrap;
}
.quick-reply-btn:hover {
  background: var(--qb-primary);
  color: white;
  border-color: var(--qb-primary);
}

.input-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.chat-input {
  flex: 1;
  padding: 10px 16px;
  font-size: 15px;
  font-family: var(--qb-font-body);
  color: var(--qb-text);
  background: var(--qb-bg);
  border: 1px solid var(--qb-border);
  border-radius: 24px;
  outline: none;
  transition: border-color var(--qb-transition);
}
.chat-input:focus { border-color: var(--qb-primary); }
.chat-input:disabled { background: #F1F5F9; cursor: not-allowed; }
.chat-input::placeholder { color: #94A3B8; }

.send-btn {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: none;
  background: var(--qb-primary);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--qb-transition);
}
.send-btn:hover:not(:disabled) { background: #1D4ED8; transform: scale(1.05); }
.send-btn:disabled { background: #CBD5E1; cursor: not-allowed; }

.sending-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: white;
  animation: pulse 1s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 0.5; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1); }
}
</style>
