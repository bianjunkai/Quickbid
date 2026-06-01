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

        <!-- ========== 招标文件（用户上传） ========== -->
        <div class="tree-section">
          <div class="section-label">📋 招标文件</div>
          <div class="section-hint">用户上传</div>
          <label class="upload-zone">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <span>{{ tenderFile || '点击上传招标文件' }}</span>
            <input type="file" hidden accept=".pdf,.docx,.doc" @change="e => onUpload('tender', e)" />
          </label>
        </div>

        <!-- ========== 主标（Agent 生成） ========== -->
        <div class="tree-section">
          <div class="section-label">📝 主标</div>
          <div class="section-hint">Agent 生成</div>
          <FileFolder name="商务文件" kind="agent">
            <GeneratedFile v-for="f in agentFiles.main.商务文件" :key="f" :name="f" />
            <EmptyHint v-if="!agentFiles.main.商务文件?.length" text="待 Agent 生成" />
          </FileFolder>
          <FileFolder name="技术方案" kind="agent">
            <GeneratedFile v-for="f in agentFiles.main.技术方案" :key="f" :name="f" />
            <EmptyHint v-if="!agentFiles.main.技术方案?.length" text="待 Agent 生成" />
          </FileFolder>
          <FileFolder name="实施计划" kind="agent">
            <EmptyHint text="待 Agent 生成" />
          </FileFolder>
          <FileFolder name="公司资质" kind="agent">
            <EmptyHint text="待 Agent 生成" />
          </FileFolder>
          <FileFolder name="配图附件" kind="agent" icon="image">
            <EmptyHint text="待 Agent 生成" />
          </FileFolder>
        </div>

        <!-- ========== 陪标（可上传 + Agent 生成） ========== -->
        <div v-for="sub in subBids" :key="sub.id" class="tree-section">
          <div class="section-label">📝 {{ sub.companyName || '未命名陪标' }}</div>
          <div class="section-hint">Agent 生成 · 可补充上传</div>
          <FileFolder name="商务文件" kind="hybrid">
            <GeneratedFile v-for="f in (agentFiles.subBids[sub.id]?.商务文件 || [])" :key="f" :name="f" />
            <UploadHint @upload="f => onSubUpload(sub.id, '商务文件', f)" />
          </FileFolder>
          <FileFolder name="技术方案" kind="hybrid">
            <UploadHint @upload="f => onSubUpload(sub.id, '技术方案', f)" />
          </FileFolder>
          <FileFolder name="实施计划" kind="hybrid">
            <UploadHint @upload="f => onSubUpload(sub.id, '实施计划', f)" />
          </FileFolder>
          <FileFolder name="公司资质" kind="hybrid">
            <UploadHint @upload="f => onSubUpload(sub.id, '公司资质', f)" />
          </FileFolder>
          <FileFolder name="配图附件" kind="hybrid" icon="image">
            <UploadHint @upload="f => onSubUpload(sub.id, '配图附件', f)" />
          </FileFolder>
        </div>

        <!-- 添加陪标 -->
        <button class="add-subbid-btn" @click="$emit('add-subbid')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          <span>添加陪标公司</span>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import FileFolder from './FileFolder.vue'
import GeneratedFile from './GeneratedFile.vue'
import UploadHint from './UploadHint.vue'
import EmptyHint from './EmptyHint.vue'

export interface SubBid {
  id: number
  companyName: string
}

defineProps<{
  tenderFile?: string
  subBids?: SubBid[]
}>()

defineEmits<{
  'upload-tender': [file: File]
  'upload-sub-file': [subId: number, folder: string, file: File]
  'add-subbid': []
}>()

// Agent-generated files (will be populated by backend API in Phase 6)
const agentFiles = reactive({
  main: {
    商务文件: [] as string[],
    技术方案: [] as string[],
  },
  subBids: {} as Record<number, Record<string, string[]>>,
})

const onUpload = (kind: string, e: Event) => {
  const input = e.target as HTMLInputElement
  // handled by parent
}

const onSubUpload = (subId: number, folder: string, e: Event) => {
  // handled by parent
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
.file-panel:not(.collapsed) { width: 248px; }
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
  padding: 12px 14px;
}

.tree-section {
  margin-bottom: 14px;
}

.section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--qb-text);
  margin-bottom: 2px;
}
.section-hint {
  font-size: 10px;
  color: #94A3B8;
  margin-bottom: 8px;
}

/* Upload zone (tender) */
.upload-zone {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  font-size: 12px;
  color: var(--qb-primary);
  border: 1px dashed var(--qb-primary);
  border-radius: var(--qb-radius-sm);
  cursor: pointer;
  transition: all var(--qb-transition);
}
.upload-zone:hover {
  background: rgba(37,99,235,0.06);
  border-style: solid;
}

/* Add sub-bid */
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
