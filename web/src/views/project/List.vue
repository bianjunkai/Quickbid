<template>
  <div class="project-page">
    <div class="page-header">
      <h2>项目管理</h2>
      <el-button type="primary" size="small" @click="showCreateDialog = true">+ 新建项目</el-button>
    </div>

    <el-table :data="projects" v-loading="loading" stripe size="small" @row-click="goDetail">
      <el-table-column prop="name" label="项目名称" min-width="200" />
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="goDetail(row.id)">进入对话</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无项目" :image-size="60">
          <el-button size="small" type="primary" @click="showCreateDialog = true">新建项目</el-button>
        </el-empty>
      </template>
    </el-table>

    <!-- Create dialog -->
    <el-dialog v-model="showCreateDialog" title="新建项目" width="420px">
      <el-form :model="createForm" label-width="80px" size="small">
        <el-form-item label="项目名称" required>
          <el-input v-model="createForm.name" placeholder="例如：XX医院信息系统投标" @keydown.enter="handleCreate" />
        </el-form-item>
        <p class="form-hint">创建后请在对话页上传招标文件（PDF / DOCX）</p>
      </el-form>
      <template #footer>
        <el-button size="small" @click="showCreateDialog = false">取消</el-button>
        <el-button size="small" type="primary" @click="handleCreate" :loading="creating">创建并进入对话</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listProjects, createProject } from '@/api'
import type { Project } from '@/types'

const router = useRouter()
const projects = ref<Project[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({ name: '', tender_file_name: 'tender.pdf' })

const S: Record<string, any> = {
  parsing: { type: 'warning', text: '解析中' },
  parsed: { type: 'success', text: '已解析' },
  materials_preparing: { type: '', text: '材料匹配' },
  generating: { type: 'info', text: '生成中' },
  done: { type: 'success', text: '已完成' },
}
const statusType = (s: string) => S[s]?.type || ''
const statusText = (s: string) => S[s]?.text || s

const fetchData = async () => {
  loading.value = true
  try { projects.value = (await listProjects()).data } catch { /* ignore */ }
  finally { loading.value = false }
}

const handleCreate = async () => {
  if (!createForm.value.name) { ElMessage.warning('请输入项目名称'); return }
  creating.value = true
  try {
    const res = await createProject(createForm.value)
    showCreateDialog.value = false
    createForm.value = { name: '', tender_file_name: 'tender.pdf' }
    router.push(`/projects/${res.data.project_id}`)
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '创建失败') }
  finally { creating.value = false }
}

const goDetail = (id: number) => router.push(`/projects/${id}`)

onMounted(fetchData)
</script>

<style scoped>
.project-page { padding: 24px; height: 100%; overflow-y: auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-family: var(--qb-font-heading); font-size: 20px; font-weight: 600; }
.form-hint { font-size: 12px; color: var(--qb-stone); margin: 4px 0 0; }
</style>
