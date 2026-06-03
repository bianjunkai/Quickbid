import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Project } from '@/types'
import {
  listProjects,
  getProject,
  createProject as apiCreateProject,
  deleteProject,
} from '@/api'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)

  const fetchProjects = async () => {
    loading.value = true
    try {
      const res = await listProjects()
      projects.value = res.data
    } finally {
      loading.value = false
    }
  }

  const fetchProject = async (id: number) => {
    loading.value = true
    try {
      const res = await getProject(id)
      currentProject.value = res.data
    } finally {
      loading.value = false
    }
  }

  const createProject = async (name: string, tenderFileName: string) => {
    const res = await apiCreateProject({ name, tender_file_name: tenderFileName })
    // 立刻追加到本地列表，sidebar 和 List.vue 会同步刷新
    const created = (res as any).data
    if (created?.project_id) {
      projects.value = [
        {
          id: created.project_id,
          name: created.project_name || name,
          tender_file_path: created.tender_file_path,
          status: 'parsing',
          created_at: new Date().toISOString(),
        },
        ...projects.value,
      ]
    }
    return res
  }

  const removeProject = async (id: number) => {
    await deleteProject(id)
    projects.value = projects.value.filter((p) => p.id !== id)
  }

  return {
    projects,
    currentProject,
    loading,
    fetchProjects,
    fetchProject,
    createProject,
    removeProject,
  }
})
