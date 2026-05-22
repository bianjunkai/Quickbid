<template>
  <div class="project-list">
    <div class="header">
      <h2>项目管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon> 新建项目
      </el-button>
    </div>

    <el-table :data="projects" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="项目名称" min-width="180" />
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="goDetail(row.id)">查看</el-button>
          <el-button link type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreateDialog" title="新建项目" width="500px">
      <el-form :model="createForm" label-width="120px">
        <el-form-item label="项目名称">
          <el-input v-model="createForm.name" placeholder="例如：XX医院信息系统投标" />
        </el-form-item>
        <el-form-item label="招标文件名">
          <el-input v-model="createForm.tender_file_name" placeholder="例如：招标书.pdf" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { listProjects, createProject, deleteProject } from '@/api'
import type { Project } from '@/types'

const router = useRouter()
const projects = ref<Project[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({ name: '', tender_file_name: '' })

const statusType = (status: string) => {
  const map: Record<string, any> = {
    parsed: 'success',
    parsing: 'warning',
    generating: 'info',
  }
  return map[status] || ''
}

const statusText = (status: string) => {
  const map: Record<string, string> = {
    parsing: '解析中',
    parsed: '已解析',
    materials_preparing: '材料准备',
    generating: '生成中',
    generated: '已生成',
  }
  return map[status] || status
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await listProjects()
    projects.value = res.data
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  if (!createForm.value.name) {
    ElMessage.warning('请输入项目名称')
    return
  }
  creating.value = true
  try {
    await createProject(createForm.value)
    ElMessage.success('项目创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', tender_file_name: '' }
    fetchData()
  } catch (e: any) {
    ElMessage.error(e?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const handleDelete = async (id: number) => {
  await ElMessageBox.confirm('确定删除此项目？', '提示', { type: 'warning' })
  await deleteProject(id)
  ElMessage.success('已删除')
  fetchData()
}

const goDetail = (id: number) => {
  router.push(`/projects/${id}`)
}

onMounted(fetchData)
</script>

<style scoped>
.project-list {
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header h2 {
  margin: 0;
}
</style>
