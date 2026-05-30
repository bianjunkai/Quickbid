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
