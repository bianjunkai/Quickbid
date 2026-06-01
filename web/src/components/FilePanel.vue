<template>
  <aside class="file-panel" :class="{ collapsed }">
    <button class="panel-toggle" @click="collapsed = !collapsed" :title="collapsed ? '展开文件' : '收起文件'">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <polyline v-if="collapsed" points="15 18 9 12 15 6" />
        <polyline v-else points="9 18 15 12 9 6" />
      </svg>
    </button>

    <div v-if="!collapsed" class="panel-content">
      <div class="panel-header">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
        <span>项目文件</span>
      </div>

      <div class="file-tree">
        <!-- 招标文件 -->
        <div class="tree-section">
          <div class="section-title">招标文件</div>
          <label class="upload-area">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <span>上传招标文件</span>
            <input type="file" hidden @change="e => onTenderUpload(e)" />
          </label>
          <div v-if="tenderFile" class="file-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <span class="file-name">{{ tenderFile }}</span>
          </div>
        </div>

        <!-- 主标 -->
        <div class="tree-section">
          <div class="section-title">主标</div>
          <FileFolder name="商务文件" />
          <FileFolder name="技术方案" />
          <FileFolder name="实施计划" />
          <FileFolder name="公司资质" />
          <FileFolder name="配图附件" icon="image" />
        </div>

        <!-- 陪标（动态，多个公司） -->
        <div v-for="sub in subBids" :key="sub.id" class="tree-section">
          <div class="section-title">{{ sub.companyName || '未命名陪标' }}</div>
          <FileFolder name="商务文件" />
          <FileFolder name="技术方案" />
          <FileFolder name="实施计划" />
          <FileFolder name="公司资质" />
          <FileFolder name="配图附件" icon="image" />
        </div>

        <!-- 添加陪标 -->
        <div class="tree-section">
          <button class="add-subbid-btn" @click="$emit('add-subbid')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            <span>添加陪标</span>
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileFolder from './FileFolder.vue'

export interface SubBid {
  id: number
  companyName: string
}

defineProps<{
  projectName?: string
  tenderFile?: string
  subBids?: SubBid[]
}>()

defineEmits<{
  'upload-tender': [file: File]
  'add-subbid': []
}>()

const collapsed = ref(false)

const onTenderUpload = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (input.files?.length) {
    // emit upload
  }
}
</script>

<style scoped>
.file-panel {
  position: relative;
  background: var(--qb-sidebar);
  border-left: 1px solid var(--qb-border);
  flex-shrink: 0;
  transition: width 200ms ease;
}
.file-panel:not(.collapsed) { width: 252px; }
.file-panel.collapsed { width: 36px; }

.panel-toggle {
  position: absolute;
  left: -12px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px; height: 24px;
  border-radius: 50%;
  border: 1px solid var(--qb-border);
  background: white;
  color: var(--qb-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  transition: all var(--qb-transition);
}
.panel-toggle:hover {
  background: var(--qb-primary-light);
  color: var(--qb-primary);
  border-color: var(--qb-primary);
}

.panel-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--qb-text);
  border-bottom: 1px solid var(--qb-border);
  flex-shrink: 0;
}
.panel-header svg { color: var(--qb-text-secondary); }

.file-tree {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.tree-section {
  margin-bottom: 16px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--qb-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--qb-border);
}

/* Upload zone */
.upload-area {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  font-size: 12px;
  color: var(--qb-text-secondary);
  border: 1px dashed var(--qb-border);
  border-radius: var(--qb-radius-sm);
  cursor: pointer;
  transition: all var(--qb-transition);
  margin-bottom: 4px;
}
.upload-area:hover {
  border-color: var(--qb-primary);
  color: var(--qb-primary);
  background: rgba(37,99,235,0.04);
}

.file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  font-size: 12px;
  color: var(--qb-success);
}
.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Add sub-bid button */
.add-subbid-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 10px;
  font-size: 12px;
  font-family: var(--qb-font-body);
  color: var(--qb-text-secondary);
  background: none;
  border: 1px dashed var(--qb-border);
  border-radius: var(--qb-radius-sm);
  cursor: pointer;
  transition: all var(--qb-transition);
}
.add-subbid-btn:hover {
  border-color: var(--qb-primary);
  color: var(--qb-primary);
  background: rgba(37,99,235,0.04);
}
</style>
