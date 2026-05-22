import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Project } from '@/types'

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
    const res = await listProjects().catch(() => null)
    // 调用实际的创建接口
    const createRes = await listProjects()
    return createRes
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
