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
            <el-option
              v-for="cat in MATERIAL_CATEGORIES"
              :key="cat.value"
              :label="cat.label"
              :value="cat.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filterKeyword" placeholder="搜索标题" clearable @keyup.enter="fetchData" />
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
      <template #empty>
        <el-empty description="暂无材料">
          <el-button type="primary" @click="showAddDialog = true">添加第一条材料</el-button>
        </el-empty>
      </template>
    </el-table>

    <el-dialog v-model="showAddDialog" title="添加材料" width="600px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="标题" required>
          <el-input v-model="addForm.title" />
        </el-form-item>
        <el-form-item label="分类" required>
          <el-select v-model="addForm.category">
            <el-option
              v-for="cat in MATERIAL_CATEGORIES"
              :key="cat.value"
              :label="cat.label"
              :value="cat.value"
            />
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
import { MATERIAL_CATEGORIES } from '@/types'
import type { Material } from '@/types'

const materials = ref<Material[]>([])
const loading = ref(false)
const showAddDialog = ref(false)
const adding = ref(false)
const filterCategory = ref('')
const filterKeyword = ref('')
const addForm = ref({ title: '', category: '', description: '', content: '', tags: '' })

const CATEGORY_LABELS = Object.fromEntries(
  MATERIAL_CATEGORIES.map(c => [c.value, c.label])
)
const categoryText = (cat: string) => CATEGORY_LABELS[cat] || cat

const fetchData = async () => {
  loading.value = true
  try {
    const res = await listMaterials({
      category: filterCategory.value || undefined,
      keyword: filterKeyword.value || undefined,
    })
    materials.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.message || '加载材料列表失败')
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
    ElMessage.error(e?.response?.data?.detail || e?.message || '添加失败')
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
