<template>
  <div class="app-shell">
    <aside class="sidebar">
      <!-- Brand -->
      <div class="sidebar-brand" @click="$router.push('/projects')">
        <div class="brand-mark">
          <svg width="24" height="24" viewBox="0 0 32 32" fill="none">
            <rect x="4" y="8" width="24" height="18" rx="2" stroke="currentColor" stroke-width="1.8" />
            <line x1="8" y1="14" x2="18" y2="14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            <line x1="8" y1="18" x2="14" y2="18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            <line x1="8" y1="22" x2="22" y2="22" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            <circle cx="25" cy="16" r="3.5" fill="var(--qb-accent)" stroke="var(--qb-accent)" stroke-width="1" />
          </svg>
        </div>
        <div class="brand-text">
          <span class="brand-name">QuickBid</span>
          <span class="brand-sub">标书制作引擎</span>
        </div>
      </div>

      <!-- Projects -->
      <div class="sidebar-section">
        <div class="sidebar-label">
          <span>项目</span>
          <button class="sidebar-add" @click="showNewProject = true" title="新建">+</button>
        </div>
        <div class="project-list">
          <div
            v-for="p in projects" :key="p.id"
            class="project-item"
            :class="{ active: p.id === activeId }"
            @click="$router.push(`/projects/${p.id}`)"
          >
            <span class="project-item-name">{{ p.name }}</span>
            <span class="project-item-status" :class="p.status" />
          </div>
          <div v-if="!projects.length" class="sidebar-empty">暂无项目</div>
        </div>
      </div>

      <!-- Nav -->
      <div class="sidebar-nav">
        <router-link to="/materials" class="nav-item" active-class="active">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
          <span>材料库</span>
        </router-link>
      </div>

      <!-- Footer -->
      <div class="sidebar-footer">
        <span class="footer-dot" />
        <span class="footer-text">系统就绪</span>
      </div>
    </aside>

    <main class="main-content">
      <router-view />
    </main>

    <!-- New project modal -->
    <Teleport to="body">
      <div v-if="showNewProject" class="modal-backdrop" @click.self="showNewProject = false">
        <div class="modal-card anim-scale-in">
          <h3 class="modal-title">新建标书项目</h3>
          <p class="modal-desc">输入项目名称，AI 助手将引导你完成标书制作。</p>
          <input
            ref="newProjectInput"
            v-model="newProjectName"
            class="modal-input"
            placeholder="例如：XX医院HIS系统投标"
            @keydown.enter="createNewProject"
          />
          <div class="modal-actions">
            <button class="btn btn-ghost" @click="showNewProject = false">取消</button>
            <button class="btn btn-primary" @click="createNewProject" :disabled="!newProjectName.trim()">创建项目</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listProjects, createProject } from '@/api'
import type { Project } from '@/types'

const route = useRoute()
const router = useRouter()

const projects = ref<Project[]>([])
const showNewProject = ref(false)
const newProjectName = ref('')
const newProjectInput = ref<HTMLInputElement>()

const activeId = computed(() => Number(route.params.id) || null)

const fetchProjects = async () => {
  try { projects.value = (await listProjects()).data } catch { /* */ }
}

const createNewProject = async () => {
  const name = newProjectName.value.trim()
  if (!name) return
  try {
    const res = await createProject({ name, tender_file_name: 'tender.pdf' })
    showNewProject.value = false; newProjectName.value = ''
    router.push(`/projects/${res.data.project_id}`)
    fetchProjects()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '创建失败') }
}

onMounted(fetchProjects)
</script>

<style scoped>
.app-shell { display: flex; height: 100vh; }

/* ── Sidebar ── */
.sidebar {
  width: 248px;
  background: var(--qb-surface);
  border-right: 1px solid var(--qb-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 18px;
  border-bottom: 1px solid var(--qb-border);
  cursor: pointer;
  transition: background 150ms var(--qb-ease);
}
.sidebar-brand:hover { background: var(--qb-paper); }
.brand-mark { color: var(--qb-primary); flex-shrink: 0; }
.brand-name {
  font-family: var(--qb-font-display);
  font-size: 19px;
  font-weight: 400;
  color: var(--qb-ink);
  line-height: 1.2;
}
.brand-sub {
  display: block;
  font-size: 11px;
  color: var(--qb-ink-light);
  opacity: 0.6;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-top: 1px;
}

/* ── Section ── */
.sidebar-section { padding: 16px 16px 8px; flex: 1; overflow-y: auto; }
.sidebar-label {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 10px; font-weight: 700; color: var(--qb-ink-light);
  text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 8px; padding: 0 4px;
}
.sidebar-add {
  width: 20px; height: 20px; border-radius: 50%;
  border: 1px solid var(--qb-border); background: var(--qb-surface);
  color: var(--qb-ink-light); cursor: pointer; font-size: 13px;
  display: flex; align-items: center; justify-content: center;
  transition: all 150ms var(--qb-ease);
}
.sidebar-add:hover { background: var(--qb-primary); color: white; border-color: var(--qb-primary); }

.project-item {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; border-radius: var(--qb-radius-sm); cursor: pointer;
  font-size: 13px; color: var(--qb-ink); transition: all 150ms var(--qb-ease);
}
.project-item:hover { background: var(--qb-primary-pale); }
.project-item.active { background: var(--qb-primary-pale); color: var(--qb-primary); font-weight: 500; }
.project-item-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.project-item-status {
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
  background: #CBD5E1;
}
.project-item-status.parsed { background: var(--qb-success); }
.project-item-status.generating { background: var(--qb-accent); }
.project-item-status.done { background: var(--qb-primary); }
.sidebar-empty { font-size: 12px; color: #B5AFA5; padding: 8px 12px; }

/* ── Nav ── */
.sidebar-nav { padding: 8px 16px 12px; border-top: 1px solid var(--qb-border); }
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; border-radius: var(--qb-radius-sm);
  font-size: 13px; color: var(--qb-ink-light); text-decoration: none;
  transition: all 150ms var(--qb-ease);
}
.nav-item:hover { background: var(--qb-primary-pale); color: var(--qb-primary); }
.nav-item.active { background: var(--qb-primary-pale); color: var(--qb-primary); font-weight: 500; }

/* ── Footer ── */
.sidebar-footer {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 20px; border-top: 1px solid var(--qb-border);
}
.footer-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--qb-success); }
.footer-text { font-size: 11px; color: var(--qb-ink-light); opacity: 0.6; }

/* ── Main ── */
.main-content { flex: 1; min-width: 0; }

/* ── Modal ── */
.modal-backdrop {
  position: fixed; inset: 0; background: rgba(26,26,46,0.4);
  backdrop-filter: blur(4px); display: flex; align-items: center;
  justify-content: center; z-index: 1000;
}
.modal-card {
  background: var(--qb-surface); border-radius: var(--qb-radius-lg);
  padding: 32px; width: 420px; max-width: 90vw;
  box-shadow: var(--qb-shadow-lg);
}
.modal-title { margin: 0 0 8px; font-family: var(--qb-font-display); font-size: 22px; font-weight: 400; color: var(--qb-ink); }
.modal-desc { font-size: 14px; color: var(--qb-ink-light); opacity: 0.7; margin: 0 0 20px; }
.modal-input {
  width: 100%; padding: 10px 14px; font-size: 15px; font-family: var(--qb-font-body);
  border: 1px solid var(--qb-border); border-radius: var(--qb-radius-sm); outline: none;
  box-sizing: border-box; transition: border-color 150ms var(--qb-ease);
  color: var(--qb-ink); background: var(--qb-paper);
}
.modal-input:focus { border-color: var(--qb-primary); background: var(--qb-surface); }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.btn {
  padding: 9px 22px; border-radius: var(--qb-radius-sm); font-size: 14px;
  font-family: var(--qb-font-body); cursor: pointer; border: none; font-weight: 500;
  transition: all 150ms var(--qb-ease);
}
.btn-ghost { background: var(--qb-paper); color: var(--qb-ink-light); }
.btn-ghost:hover { background: var(--qb-border); }
.btn-primary { background: var(--qb-primary); color: white; }
.btn-primary:hover { background: var(--qb-primary-light); }
.btn-primary:disabled { background: #CBD5E1; cursor: not-allowed; }
</style>
