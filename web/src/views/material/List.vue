<template>
  <div class="material-list">
    <div class="header">
      <h2>材料库</h2>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon> 添加材料
      </el-button>
    </div>

    <el-card class="filter-card">
      <el-form inline>
        <el-form-item label="分类">
          <el-select v-model="filterCategory" placeholder="全部" clearable>
            <el-option label="公司简介" value="company" />
            <el-option label="业绩案例" value="case" />
            <el-option label="技术方案" value="technical" />
            <el-option label="资质证书" value="certificate" />
            <el-option label="商务条款" value="commercial" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filterKeyword" placeholder="搜索标题" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchData">搜索</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table :data="materials" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="title" label="材料标题" min-width="200" />
      <el-table-column prop="category" label="分类" width="120">
        <template #default="{ row }">
          <el-tag>{{ categoryText(row.category) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="tags" label="标签" width="200" />
      <el-table-column prop="char_count" label="字数" width="100" />
      <el-table-column prop="ai_summary" label="AI摘要" min-width="200" show-overflow-tooltip />
      <el-table-column prop="version" label="版本" width="80" />
    </el-table>

    <el-dialog v-model="showAddDialog" title="添加材料" width="600px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="标题" required>
          <el-input v-model="addForm.title" />
        </el-form-item>
        <el-form-item label="分类" required>
          <el-select v-model="addForm.category">
            <el-option label="公司简介" value="company" />
            <el-option label="业绩案例" value="case" />
            <el-option label="技术方案" value="technical" />
            <el-option label="资质证书" value="certificate" />
            <el-option label="商务条款" value="commercial" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="addForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="addForm.content" type="textarea" :rows="6" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="addForm.tags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd" :loading="adding">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { listMaterials, createMaterial } from '@/api'
import type { Material } from '@/types'

const materials = ref<Material[]>([])
const loading = ref(false)
const showAddDialog = ref(false)
const adding = ref(false)
const filterCategory = ref('')
const filterKeyword = ref('')
const addForm = ref({ title: '', category: '', description: '', content: '', tags: '' })

const categoryText = (cat: string) => ({
  company: '公司简介', case: '业绩案例', technical: '技术方案',
  certificate: '资质证书', commercial: '商务条款',
}[cat] || cat)

const fetchData = async () => {
  loading.value = true
  try {
    const res = await listMaterials({ category: filterCategory.value || undefined, keyword: filterKeyword.value || undefined })
    materials.value = res.data
  } finally {
    loading.value = false
  }
}

const handleAdd = async () => {
  if (!addForm.value.title || !addForm.value.category) {
    ElMessage.warning('请填写标题和分类')
    return
  }
  adding.value = true
  try {
    await createMaterial({ ...addForm.value })
    ElMessage.success('添加成功')
    showAddDialog.value = false
    addForm.value = { title: '', category: '', description: '', content: '', tags: '' }
    fetchData()
  } catch (e: any) {
    ElMessage.error(e?.message || '添加失败')
  } finally {
    adding.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.material-list { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header h2 { margin: 0; }
.filter-card { margin-bottom: 16px; }
</style>
