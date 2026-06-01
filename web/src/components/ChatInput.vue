<template>
  <div class="chat-input-area">
    <div v-if="quickReplies.length" class="quick-replies">
      <button v-for="(qr, i) in quickReplies" :key="i" class="qr-chip" @click="$emit('quick-reply', qr.value)">
        {{ qr.label }}
      </button>
    </div>

    <div class="input-row">
      <div class="input-wrapper">
        <input
          ref="inputEl"
          v-model="text"
          class="chat-input"
          :placeholder="placeholder"
          :disabled="disabled"
          @keydown.enter="send"
        />
        <div class="input-glow" />
      </div>
      <button class="send-btn" :class="{ active: text.trim() && !disabled }" :disabled="!text.trim() || disabled" @click="send">
        <svg v-if="!sending" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
        </svg>
        <span v-else class="sending-dot" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

withDefaults(defineProps<{
  placeholder?: string
  disabled?: boolean
  sending?: boolean
  quickReplies?: { label: string; value: string }[]
}>(), { placeholder: '输入消息...' })

const emit = defineEmits<{ send: [text: string]; 'quick-reply': [value: string] }>()

const text = ref('')
const inputEl = ref<HTMLInputElement>()

const send = () => {
  const val = text.value.trim()
  if (!val || (arguments[0] as any)?.disabled) return
  emit('send', val)
  text.value = ''
}

defineExpose({ focus: () => inputEl.value?.focus() })
</script>

<style scoped>
.chat-input-area {
  padding: 16px 24px 20px;
  border-top: 1px solid var(--qb-border);
  background: var(--qb-surface);
}

.quick-replies { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.qr-chip {
  padding: 5px 14px; font-size: 12px; font-family: var(--qb-font-body);
  font-weight: 500; color: var(--qb-ink-light); background: var(--qb-paper);
  border: 1px solid var(--qb-border); border-radius: 20px; cursor: pointer;
  transition: all 150ms var(--qb-ease); white-space: nowrap;
}
.qr-chip:hover { background: var(--qb-ink); color: white; border-color: var(--qb-ink); }

.input-row { display: flex; gap: 10px; align-items: flex-end; }

.input-wrapper { flex: 1; position: relative; }

.chat-input {
  width: 100%; padding: 11px 16px; font-size: 14px;
  font-family: var(--qb-font-body); color: var(--qb-ink);
  background: var(--qb-paper); border: 1px solid var(--qb-border);
  border-radius: var(--qb-radius); outline: none;
  transition: all 200ms var(--qb-ease);
}
.chat-input:focus { border-color: var(--qb-primary); background: var(--qb-surface); box-shadow: 0 0 0 3px rgba(30,58,95,0.06); }
.chat-input:disabled { background: var(--qb-paper-warm); cursor: not-allowed; opacity: 0.6; }
.chat-input::placeholder { color: #B5AFA5; }

.send-btn {
  width: 42px; height: 42px; border-radius: 12px;
  border: 1px solid var(--qb-border); background: var(--qb-paper);
  color: var(--qb-ink-light); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; transition: all 200ms var(--qb-ease);
}
.send-btn.active { background: var(--qb-primary); color: white; border-color: var(--qb-primary); }
.send-btn.active:hover { background: var(--qb-primary-light); transform: translateY(-1px); box-shadow: var(--qb-shadow); }
.send-btn:disabled { background: var(--qb-paper); color: #CBD5E1; cursor: not-allowed; border-color: var(--qb-border); }

.sending-dot {
  width: 8px; height: 8px; border-radius: 50%; background: currentColor;
  animation: blink 0.8s ease-in-out infinite;
}
@keyframes blink { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
</style>
