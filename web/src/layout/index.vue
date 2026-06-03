<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="sb-brand" @click="$router.push('/projects')">
        <div class="brand-mark">
          <svg width="22" height="22" viewBox="0 0 32 32" fill="none">
            <rect x="5" y="9" width="22" height="16" rx="1.5" stroke="currentColor" stroke-width="1.6"/>
            <line x1="9" y1="14" x2="17" y2="14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            <line x1="9" y1="18" x2="20" y2="18" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            <line x1="9" y1="22" x2="14" y2="22" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          </svg>
        </div>
        <div>
          <div class="brand-name">QuickBid</div>
          <div class="brand-sub">标书制作工具</div>
        </div>
      </div>

      <div class="sb-section">
        <div class="sb-label">项目</div>
        <div class="sb-list">
          <div v-for="p in projects" :key="p.id"
            class="sb-item" :class="{ active: p.id === activeId }"
            @click="$router.push(`/projects/${p.id}`)"
          >
            <span class="sb-item-name">{{ p.name }}</span>
          </div>
          <div v-if="!projects.length" class="sb-empty">暂无项目</div>
        </div>
        <button class="sb-add" @click="showNew = true">+ 新建项目</button>
      </div>

      <div class="sb-nav">
        <router-link to="/materials" class="sb-nav-item" active-class="active">材料库</router-link>
      </div>
    </aside>

    <main class="main"><router-view /></main>

    <Teleport to="body">
      <div v-if="showNew" class="modal-bg" @click.self="showNew = false">
        <div class="modal-card anim-fade-in">
          <h3 class="modal-title">新建标书项目</h3>
          <input ref="newInp" v-model="newName" class="modal-inp" placeholder="项目名称，例如：XX医院HIS系统投标" @keydown.enter="create" />
          <div class="modal-btns">
            <button class="btn-ghost" @click="showNew = false">取消</button>
            <button class="btn-fill" @click="create" :disabled="!newName.trim()">创建项目</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import router from '@/router'
import { ElMessage } from 'element-plus'
import { useProjectStore } from '@/store/project'

const route = useRoute()
const store = useProjectStore()
const projects = computed(() => store.projects)
const showNew = ref(false)
const newName = ref('')
const activeId = computed(() => Number(route.params.id) || null)

const create = async () => {
  if (!newName.value.trim()) return
  try {
    const res = await store.createProject(newName.value.trim(), 'tender.pdf')
    showNew.value = false; newName.value = ''
    router.push(`/projects/${(res as any).data.project_id}`)
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '创建失败') }
}
// 初始拉取 + 路由切换时刷新（确保从 List.vue 创建的项目也能出现在 sidebar）
onMounted(() => { store.fetchProjects() })
watch(() => route.fullPath, () => { store.fetchProjects() })
</script>

<style scoped>
.app-shell { display: flex; height: 100vh; }

/* Sidebar */
.sidebar {
  width: 240px; background: var(--qb-surface);
  border-right: 1px solid var(--qb-border); display: flex; flex-direction: column;
}
.sb-brand {
  display: flex; align-items: center; gap: 12px; padding: 20px;
  border-bottom: 1px solid var(--qb-border); cursor: pointer;
}
.brand-mark { color: var(--qb-ink); }
.brand-name { font-family: var(--qb-font-display); font-size: 20px; font-weight: 600; color: var(--qb-ink); line-height:1.2; }
.brand-sub { font-size: 11px; color: var(--qb-stone); }

.sb-section { padding: 16px; flex:1; overflow-y:auto; }
.sb-label { font-size: 10px; font-weight: 700; color: var(--qb-stone); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
.sb-item {
  padding: 7px 10px; border-radius: var(--qb-radius); cursor: pointer; font-size: 13px;
  color: var(--qb-ink); margin-bottom: 1px; transition: background 120ms;
}
.sb-item:hover { background: var(--qb-paper); }
.sb-item.active { background: var(--qb-amber-light); color: var(--qb-ink); font-weight: 500; }
.sb-item-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }
.sb-empty { font-size: 12px; color: var(--qb-stone); padding: 8px 10px; }
.sb-add {
  margin-top: 8px; width: 100%; padding: 7px; font-size: 12px; font-family: var(--qb-font-body);
  color: var(--qb-ink-light); background: none; border: 1px dashed var(--qb-border);
  border-radius: var(--qb-radius); cursor: pointer; transition: all 120ms;
}
.sb-add:hover { border-color: var(--qb-ink); color: var(--qb-ink); }

.sb-nav { padding: 12px 16px; border-top: 1px solid var(--qb-border); }
.sb-nav-item {
  display: block; padding: 7px 10px; font-size: 13px; color: var(--qb-ink-light);
  text-decoration: none; border-radius: var(--qb-radius); transition: background 120ms;
}
.sb-nav-item:hover { background: var(--qb-paper); }
.sb-nav-item.active { background: var(--qb-amber-light); color: var(--qb-ink); font-weight: 500; }

.main { flex:1; min-width:0; min-height:0; display:flex; flex-direction:column; }

/* Modal */
.modal-bg {
  position:fixed; inset:0; background:rgba(0,0,0,0.3);
  display:flex; align-items:center; justify-content:center; z-index:1000;
}
.modal-card { background:var(--qb-surface); border-radius: var(--qb-radius); padding:28px 32px; width:420px; max-width:90vw; }
.modal-title { margin:0 0 6px; font-family:var(--qb-font-display); font-size:22px; font-weight:600; color:var(--qb-ink); }
.modal-inp {
  margin-top:16px; width:100%; padding:10px 14px; font-size:15px; font-family:var(--qb-font-body);
  border:1px solid var(--qb-border); border-radius: var(--qb-radius); outline:none; color:var(--qb-ink);
}
.modal-inp:focus { border-color:var(--qb-ink); }
.modal-btns { display:flex; justify-content:flex-end; gap:10px; margin-top:16px; }
.btn-ghost {
  padding:8px 20px; font-size:14px; font-family:var(--qb-font-body); border:1px solid var(--qb-border);
  border-radius: var(--qb-radius); background:white; color:var(--qb-ink-light); cursor:pointer;
}
.btn-fill {
  padding:8px 20px; font-size:14px; font-family:var(--qb-font-body); border:none;
  border-radius: var(--qb-radius); background:var(--qb-ink); color:white; cursor:pointer; font-weight:500;
}
.btn-fill:disabled { background: var(--qb-stone); cursor:not-allowed; }
</style>
