<template>
  <aside class="file-panel" :class="{ collapsed }">
    <button class="panel-toggle" @click="collapsed = !collapsed" :title="collapsed ? '展开' : '收起'">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline :points="collapsed ? '15 18 9 12 15 6' : '9 18 15 12 9 6'" /></svg>
    </button>

    <div v-if="!collapsed" class="panel-inner">
      <!-- Header -->
      <div class="panel-hd">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
        <span>项目文件</span>
      </div>

      <div class="panel-body">

        <!-- 招标文件 -->
        <div class="section">
          <div class="sec-title">招标文件</div>
          <div class="sec-label">用户上传</div>
          <label class="upload-box">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <span>{{ tenderFile || '上传招标文件' }}</span>
            <input type="file" hidden accept=".pdf,.docx" />
          </label>
        </div>

        <!-- 主标 -->
        <div class="section">
          <div class="sec-title">主标</div>
          <div class="sec-label">AI 生成</div>
          <TreeFolder name="商务文件" :kind="'ai'" />
          <TreeFolder name="技术方案" :kind="'ai'" />
          <TreeFolder name="实施计划" :kind="'ai'" />
          <TreeFolder name="公司资质" :kind="'ai'" />
          <TreeFolder name="配图附件" :kind="'ai'" icon="img" />
        </div>

        <!-- 陪标 -->
        <div v-for="sub in subBids" :key="sub.id" class="section">
          <div class="sec-title">{{ sub.companyName }}</div>
          <div class="sec-label">AI 生成 · 可补充</div>
          <TreeFolder name="商务文件" :kind="'hybrid'" />
          <TreeFolder name="技术方案" :kind="'hybrid'" />
          <TreeFolder name="实施计划" :kind="'hybrid'" />
          <TreeFolder name="公司资质" :kind="'hybrid'" />
          <TreeFolder name="配图附件" :kind="'hybrid'" icon="img" />
        </div>

        <button class="add-sub-btn" @click="$emit('add-subbid')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          <span>添加陪标</span>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import TreeFolder from './FileFolder.vue'

defineProps<{ tenderFile?: string; subBids?: { id: number; companyName: string }[] }>()
defineEmits<{ 'add-subbid': [] }>()

const collapsed = ref(false)
</script>

<style scoped>
.file-panel {
  position: relative; background: var(--qb-surface);
  border-left: 1px solid var(--qb-border); flex-shrink: 0;
  transition: width 200ms var(--qb-ease);
}
.file-panel:not(.collapsed) { width: 260px; }
.file-panel.collapsed { width: 36px; }

.panel-toggle {
  position: absolute; left: -12px; top: 50%; transform: translateY(-50%);
  width: 24px; height: 24px; border-radius: 50%;
  border: 1px solid var(--qb-border); background: var(--qb-surface);
  color: var(--qb-ink-light); cursor: pointer; display: flex;
  align-items: center; justify-content: center; z-index: 2;
  transition: all 150ms var(--qb-ease);
}
.panel-toggle:hover { background: var(--qb-primary); color: white; border-color: var(--qb-primary); }

.panel-inner { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.panel-hd {
  display: flex; align-items: center; gap: 8px;
  padding: 16px 18px; font-size: 13px; font-weight: 600; color: var(--qb-ink);
  border-bottom: 1px solid var(--qb-border); flex-shrink: 0;
}
.panel-hd svg { color: var(--qb-ink-light); opacity: 0.5; }

.panel-body { flex: 1; overflow-y: auto; padding: 14px 16px; }

.section { margin-bottom: 18px; }
.sec-title { font-size: 12px; font-weight: 600; color: var(--qb-ink); margin-bottom: 2px; }
.sec-label { font-size: 10px; color: var(--qb-ink-light); opacity: 0.5; margin-bottom: 8px; letter-spacing: 0.3px; }

.upload-box {
  display: flex; align-items: center; gap: 6px; padding: 9px 12px;
  font-size: 12px; color: var(--qb-primary); border: 1px dashed var(--qb-primary);
  border-radius: var(--qb-radius-sm); cursor: pointer; transition: all 150ms var(--qb-ease);
  background: rgba(30,58,95,0.02);
}
.upload-box:hover { background: rgba(30,58,95,0.06); border-style: solid; }

.add-sub-btn {
  display: flex; align-items: center; gap: 6px; width: 100%;
  padding: 8px 12px; font-size: 12px; font-family: var(--qb-font-body);
  color: var(--qb-ink-light); background: none; border: 1px dashed var(--qb-border);
  border-radius: var(--qb-radius-sm); cursor: pointer; transition: all 150ms var(--qb-ease);
  opacity: 0.6;
}
.add-sub-btn:hover { opacity: 1; border-color: var(--qb-primary); color: var(--qb-primary); }
</style>
