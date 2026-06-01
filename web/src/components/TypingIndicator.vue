<template>
  <div class="typing">
    <span class="typing-dot" />
    <span class="typing-dot" />
    <span class="typing-dot" />
  </div>
</template>

<style scoped>
.typing {
  display: inline-flex;
  gap: 5px;
  padding: 14px 18px;
  background: var(--qb-ai-bubble);
  border: 1px solid var(--qb-ai-bubble-border);
  border-radius: var(--qb-radius);
  border-bottom-left-radius: 4px;
  align-items: center;
}
.typing-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--qb-primary);
  opacity: 0.3;
  animation: dotPulse 1.4s ease-in-out infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.75); }
  40% { opacity: 0.8; transform: scale(1); }
}
</style>
