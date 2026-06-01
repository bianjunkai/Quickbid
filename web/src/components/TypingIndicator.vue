<template>
  <div class="typing-indicator">
    <span class="dot" />
    <span class="dot" />
    <span class="dot" />
  </div>
</template>

<style scoped>
.typing-indicator {
  display: inline-flex;
  gap: 4px;
  padding: 12px 16px;
  background: var(--qb-primary-light);
  border-radius: var(--qb-radius);
  align-items: center;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--qb-primary);
  opacity: 0.4;
  animation: pulse 1.4s ease-in-out infinite;
}

.dot:nth-child(1) { animation-delay: 0s; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 80%, 100% { opacity: 0.4; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}
</style>
