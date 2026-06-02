<template>
  <aside class="fp" :class="{ shut }">
    <button class="fp-toggle" @click="shut = !shut" :title="shut ? '展开' : '收起'">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline :points="shut ? '15 18 9 12 15 6' : '9 18 15 12 9 6'" /></svg>
    </button>
    <div v-if="!shut" class="fp-inner">
      <div class="fp-hd">项目文件</div>
      <div class="fp-body">
        <div class="fp-sec">
          <div class="fp-sec-title">招标文件</div>
          <el-upload
            :show-file-list="false" :auto-upload="false" accept=".pdf,.docx"
            :on-change="(f: any) => $emit('upload-tender', f.raw)"
          >
            <label class="fp-upload">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <span>{{ tenderFile || '点击上传' }}</span>
          </label>
          </el-upload>
        </div>
        <div class="fp-sec">
          <div class="fp-sec-title">主标</div>
          <FolderRow name="商务文件" />
          <FolderRow name="技术方案" />
          <FolderRow name="实施计划" />
          <FolderRow name="公司资质" />
          <FolderRow name="配图附件" />
        </div>
        <div v-for="sub in subBids" :key="sub.id" class="fp-sec">
          <div class="fp-sec-title">{{ sub.companyName }}</div>
          <FolderRow name="商务文件" />
          <FolderRow name="技术方案" />
          <FolderRow name="实施计划" />
          <FolderRow name="公司资质" />
          <FolderRow name="配图附件" />
        </div>
        <button class="fp-add" @click="$emit('add-subbid')">+ 添加陪标</button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FolderRow from './FileFolder.vue'
defineProps<{ tenderFile?: string; subBids?: { id: number; companyName: string }[] }>()
defineEmits<{ 'add-subbid': []; 'upload-tender': [file: File] }>()
const shut = ref(false)
</script>

<style scoped>
.fp { position:relative; background:var(--qb-surface); border-left:1px solid var(--qb-border); transition:width 200ms; flex-shrink:0; }
.fp:not(.shut) { width: 240px; }
.fp.shut { width: 32px; }
.fp-toggle {
  position:absolute; left:-11px; top:50%; transform:translateY(-50%);
  width:22px;height:22px;border-radius:50%;border:1px solid var(--qb-border);
  background:var(--qb-surface);color:var(--qb-stone);cursor:pointer;
  display:flex;align-items:center;justify-content:center;z-index:2;transition:all 120ms;
}
.fp-toggle:hover { background:var(--qb-ink);color:white;border-color:var(--qb-ink); }
.fp-inner { display:flex;flex-direction:column;height:100%;overflow:hidden; }
.fp-hd { padding:16px 18px;font-size:12px;font-weight:600;color:var(--qb-ink);text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid var(--qb-border); }
.fp-body { flex:1;overflow-y:auto;padding:12px 16px; }
.fp-sec { margin-bottom: 16px; }
.fp-sec-title { font-size:11px;font-weight:600;color:var(--qb-ink-light);text-transform:uppercase;letter-spacing:0.3px;margin-bottom:6px; }
.fp-upload {
  display:flex;align-items:center;gap:6px;padding:7px 10px;font-size:12px;
  color:var(--qb-amber);border:1px dashed var(--qb-amber);border-radius:2px;
  cursor:pointer;transition:all 120ms;background:var(--qb-amber-light);
}
.fp-upload:hover { background:var(--qb-amber);color:white;border-style:solid; }
.fp-add {
  width:100%;padding:7px;font-size:12px;font-family:var(--qb-font-body);
  color:var(--qb-stone);background:none;border:1px dashed var(--qb-border);
  border-radius:var(--qb-radius);cursor:pointer;transition:all 120ms;
}
.fp-add:hover { border-color:var(--qb-ink);color:var(--qb-ink); }
</style>
