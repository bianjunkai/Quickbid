<template>
  <div class="processing">
    <span class="proc-dot" />
    <span class="proc-label">处理中</span>
  </div>
</template>

<style scoped>
.processing {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 8px 0; margin-bottom: 24px; margin-left: 52px;
  font-size: 12px; color: var(--qb-stone);
  border-left: 2px solid var(--qb-border); padding-left: 16px;
}
.proc-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--qb-amber);
  animation: pulse 1s ease-in-out infinite;
}
.proc-label { font-family: var(--qb-font-body); }
@keyframes pulse { 0%,100%{opacity:0.3;} 50%{opacity:1;} }
</style>
