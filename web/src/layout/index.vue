<template>
  <div class="app-shell">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand" @click="$router.push('/projects')">
        <div class="brand-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
        </div>
        <div class="brand-text">
          <span class="brand-name">QuickBid</span>
          <span class="brand-tag">AI 标书助手</span>
        </div>
      </div>

      <!-- Project list (compact) -->
      <div class="sidebar-section">
        <div class="sidebar-section-header">
          <span>项目</span>
          <button class="sidebar-add-btn" @click="showNewProject = true" title="新建项目">+</button>
        </div>
        <div class="project-list">
          <div
            v-for="p in projects"
            :key="p.id"
            class="project-item"
            :class="{ active: p.id === activeProjectId }"
            @click="$router.push(`/projects/${p.id}`)"
          >
            <span class="project-item-name">{{ p.name }}</span>
          </div>
          <div v-if="projects.length === 0" class="sidebar-empty">暂无项目</div>
        </div>
      </div>

      <!-- Navigation -->
      <div class="sidebar-nav">
        <router-link to="/materials" class="sidebar-nav-item" active-class="active">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
          <span>材料库</span>
        </router-link>
      </div>

      <!-- New project dialog (simple) -->
      <Teleport to="body">
        <div v-if="showNewProject" class="modal-overlay" @click.self="showNewProject = false">
          <div class="modal-card">
            <h3>新建项目</h3>
            <input
              ref="newProjectInput"
              v-model="newProjectName"
              class="modal-input"
              placeholder="项目名称，例如：XX医院HIS投标"
              @keydown.enter="createNewProject"
            />
            <div class="modal-actions">
              <button class="modal-btn cancel" @click="showNewProject = false">取消</button>
              <button class="modal-btn confirm" @click="createNewProject" :disabled="!newProjectName.trim()">创建</button>
            </div>
          </div>
        </div>
      </Teleport>
    </aside>

    <!-- Main content -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listProjects, createProject } from '@/api'
import type { Project } from '@/types'
import router from '@/router'

const route = useRoute()

const projects = ref<Project[]>([])
const showNewProject = ref(false)
const newProjectName = ref('')
const newProjectInput = ref<HTMLInputElement>()

const activeProjectId = computed(() => {
  const id = Number(route.params.id)
  return isNaN(id) ? null : id
})

const fetchProjects = async () => {
  try {
    const res = await listProjects()
    projects.value = res.data
  } catch { /* sidebar is non-critical */ }
}

const createNewProject = async () => {
  const name = newProjectName.value.trim()
  if (!name) return
  try {
    const res = await createProject({ name, tender_file_name: 'tender.pdf' })
    showNewProject.value = false
    newProjectName.value = ''
    router.push(`/projects/${res.data.project_id}`)
    fetchProjects()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '创建失败')
  }
}

onMounted(fetchProjects)
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  background: var(--qb-bg);
}

/* Sidebar */
.sidebar {
  width: 240px;
  background: var(--qb-sidebar);
  border-right: 1px solid var(--qb-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-brand {
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--qb-border);
  cursor: pointer;
  transition: background var(--qb-transition);
}
.sidebar-brand:hover { background: rgba(0,0,0,0.02); }
.brand-icon { color: var(--qb-primary); }
.brand-name {
  font-family: var(--qb-font-heading);
  font-size: 17px;
  font-weight: 600;
  color: var(--qb-text);
}
.brand-tag {
  display: block;
  font-size: 11px;
  color: var(--qb-text-secondary);
  letter-spacing: 0.3px;
}

/* Section header */
.sidebar-section {
  padding: 16px 16px 8px;
  flex: 1;
  overflow-y: auto;
}
.sidebar-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--qb-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
  padding: 0 4px;
}
.sidebar-add-btn {
  width: 22px; height: 22px;
  border-radius: 50%;
  border: 1px solid var(--qb-border);
  background: white;
  color: var(--qb-text-secondary);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--qb-transition);
}
.sidebar-add-btn:hover { background: var(--qb-primary); color: white; border-color: var(--qb-primary); }

.project-list { display: flex; flex-direction: column; }
.project-item {
  padding: 8px 12px;
  border-radius: var(--qb-radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--qb-text);
  transition: all var(--qb-transition);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.project-item:hover { background: rgba(37,99,235,0.06); }
.project-item.active {
  background: rgba(37,99,235,0.1);
  color: var(--qb-primary);
  font-weight: 500;
}
.sidebar-empty { font-size: 12px; color: #94A3B8; padding: 8px 12px; }

/* Nav */
.sidebar-nav {
  padding: 8px 16px 16px;
  border-top: 1px solid var(--qb-border);
}
.sidebar-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--qb-radius-sm);
  font-size: 13px;
  color: var(--qb-text-secondary);
  text-decoration: none;
  transition: all var(--qb-transition);
}
.sidebar-nav-item:hover { background: rgba(0,0,0,0.03); color: var(--qb-text); }
.sidebar-nav-item.active { background: rgba(37,99,235,0.08); color: var(--qb-primary); font-weight: 500; }

/* Main */
.main-content { flex: 1; min-width: 0; }

/* New project modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  width: 400px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.modal-card h3 {
  margin: 0 0 16px;
  font-family: var(--qb-font-heading);
  font-size: 18px;
}
.modal-input {
  width: 100%;
  padding: 10px 14px;
  font-size: 15px;
  font-family: var(--qb-font-body);
  border: 1px solid var(--qb-border);
  border-radius: 8px;
  outline: none;
  box-sizing: border-box;
}
.modal-input:focus { border-color: var(--qb-primary); }
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}
.modal-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-family: var(--qb-font-body);
  cursor: pointer;
  border: none;
  transition: all var(--qb-transition);
}
.modal-btn.cancel { background: #F1F5F9; color: var(--qb-text-secondary); }
.modal-btn.cancel:hover { background: #E2E8F0; }
.modal-btn.confirm { background: var(--qb-primary); color: white; }
.modal-btn.confirm:hover { background: #1D4ED8; }
.modal-btn.confirm:disabled { background: #CBD5E1; cursor: not-allowed; }
</style>
