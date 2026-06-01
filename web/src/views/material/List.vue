<template>
  <div class="material-page">
    <div class="page-header">
      <h2>材料库</h2>
      <el-button type="primary" size="small" @click="showAddDialog = true">
        + 添加材料
      </el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterCategory" placeholder="全部分类" clearable size="small" style="width:160px">
        <el-option v-for="cat in MATERIAL_CATEGORIES" :key="cat.value" :label="cat.label" :value="cat.value" />
      </el-select>
      <el-input v-model="filterKeyword" placeholder="搜索..." clearable size="small" style="width:200px" @keyup.enter="fetchData" />
      <el-button size="small" @click="fetchData">搜索</el-button>
    </div>

    <el-table :data="materials" v-loading="loading" stripe size="small">
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column prop="category" label="分类" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ categoryText(row.category) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="char_count" label="字数" width="80" />
      <el-table-column prop="ai_summary" label="摘要" min-width="200" show-overflow-tooltip />
      <template #empty>
        <el-empty description="暂无材料" :image-size="60" />
      </template>
    </el-table>

    <!-- Add dialog -->
    <el-dialog v-model="showAddDialog" title="添加材料" width="520px">
      <el-form :model="addForm" label-width="80px" size="small">
        <el-form-item label="标题" required><el-input v-model="addForm.title" /></el-form-item>
        <el-form-item label="分类" required>
          <el-select v-model="addForm.category">
            <el-option v-for="cat in MATERIAL_CATEGORIES" :key="cat.value" :label="cat.label" :value="cat.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="addForm.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="addForm.content" type="textarea" :rows="5" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="addForm.tags" placeholder="逗号分隔" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="showAddDialog = false">取消</el-button>
        <el-button size="small" type="primary" @click="handleAdd" :loading="adding">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listMaterials, createMaterial } from '@/api'
import { MATERIAL_CATEGORIES } from '@/types'
import type { Material } from '@/types'

const materials = ref<Material[]>([])
const loading = ref(false)
const showAddDialog = ref(false)
const adding = ref(false)
const filterCategory = ref('')
const filterKeyword = ref('')
const addForm = ref({ title: '', category: '', description: '', content: '', tags: '' })

const CATEGORY_LABELS = Object.fromEntries(MATERIAL_CATEGORIES.map(c => [c.value, c.label]))
const categoryText = (cat: string) => CATEGORY_LABELS[cat] || cat

const fetchData = async () => {
  loading.value = true
  try {
    const res = await listMaterials({ category: filterCategory.value || undefined, keyword: filterKeyword.value || undefined })
    materials.value = res.data
  } catch { /* ignore */ }
  finally { loading.value = false }
}

const handleAdd = async () => {
  if (!addForm.value.title || !addForm.value.category) { ElMessage.warning('请填写标题和分类'); return }
  adding.value = true
  try {
    await createMaterial({ ...addForm.value })
    ElMessage.success('添加成功')
    showAddDialog.value = false
    addForm.value = { title: '', category: '', description: '', content: '', tags: '' }
    fetchData()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '添加失败') }
  finally { adding.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.material-page { padding: 24px; height: 100%; overflow-y: auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-family: var(--qb-font-heading); font-size: 20px; font-weight: 600; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 16px; }
</style>
