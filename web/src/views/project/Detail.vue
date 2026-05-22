<template>
  <div class="project-detail">
    <el-page-header @back="router.push('/projects')" content="项目详情">
      <template #extra>
        <el-button size="small" @click="router.push('/projects')">返回列表</el-button>
      </template>
    </el-page-header>

    <el-card class="project-info" v-if="project">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="项目名称">{{ project.name }}</el-descriptions-item>
        <el-descriptions-item label="项目状态">
          <el-tag :type="statusType(project.status)">{{ statusText(project.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="招标文件">{{ project.tender_file_path }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ project.created_at }}</el-descriptions-item>
        <el-descriptions-item label="招标编号">{{ project.tender_no || '—' }}</el-descriptions-item>
        <el-descriptions-item label="预算金额">{{ project.budget ? `¥${project.budget.toLocaleString()}` : '—' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 工作流步骤条 -->
    <el-steps :active="stepIndex" finish-status="success" class="workflow-steps">
      <el-step title="上传招标文件" />
      <el-step title="AI解析" />
      <el-step title="确认信息" />
      <el-step title="材料匹配" />
      <el-step title="生成标书" />
      <el-step title="终审检查" />
      <el-step title="导出" />
    </el-steps>

    <!-- 步骤内容区 -->
    <div class="step-content">
      <!-- 步骤1: 上传/填写文件 -->
      <el-card v-if="stepIndex === 0">
        <template #header>步骤1：招标文件</template>
        <p>请将招标文件（PDF/Word）上传到服务器指定目录。</p>
        <el-alert v-if="project?.tender_file_path" :title="`文件路径：${project.tender_file_path}`" type="info" show-icon />
        <p style="margin-top:12px;color:#888">文件路径已在创建项目时指定，如需修改请重新创建项目。</p>
        <div style="margin-top:16px;text-align:right">
          <el-button type="primary" @click="handleParse" :loading="parsing">开始解析</el-button>
        </div>
      </el-card>

      <!-- 步骤2: AI解析结果 -->
      <el-card v-if="stepIndex === 1">
        <template #header>步骤2：AI解析结果</template>
        <el-descriptions :column="2" border size="small" v-if="parsedData">
          <el-descriptions-item v-for="(val, key) in parsedData" :key="key" :label="String(key)">
            {{ Array.isArray(val) ? val.join('、') : (val || '—') }}
          </el-descriptions-item>
        </el-descriptions>
        <div style="margin-top:16px;text-align:right">
          <el-button @click="stepIndex = 0">上一步</el-button>
          <el-button type="primary" @click="stepIndex = 2">信息正确，继续</el-button>
        </div>
      </el-card>

      <!-- 步骤3: 确认/纠错 -->
      <el-card v-if="stepIndex === 2">
        <template #header>步骤3：确认信息</template>
        <p>请检查上述解析结果，如有错误请在下方修正：</p>
        <el-form label-width="140px" style="margin-top:16px">
          <el-form-item label="招标编号">
            <el-input v-model="corrections.tender_no" placeholder="修正招标编号" />
          </el-form-item>
          <el-form-item label="预算金额">
            <el-input-number v-model="corrections.budget" :min="0" />
          </el-form-item>
          <el-form-item label="投标截止时间">
            <el-date-picker v-model="corrections.deadline" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="开标时间">
            <el-date-picker v-model="corrections.open_time" type="datetime" value-format="YYYY-MM-DD HH:mm" />
          </el-form-item>
        </el-form>
        <div style="margin-top:16px;text-align:right">
          <el-button @click="stepIndex = 1">上一步</el-button>
          <el-button type="primary" @click="handleConfirmParse">确认并继续</el-button>
        </div>
      </el-card>

      <!-- 步骤4: 材料匹配 -->
      <el-card v-if="stepIndex === 3">
        <template #header>步骤4：材料匹配</template>
        <el-alert v-if="matchMessage" :title="matchMessage" type="success" show-icon style="margin-bottom:16px" />
        <div v-for="(ch, idx) in chapters" :key="idx" class="chapter-item">
          <h4>{{ ch.chapter }}</h4>
          <el-tag v-for="m in ch.recommended" :key="m.id" style="margin-right:8px">
            {{ m.title }}（匹配度：{{ m.match_score }}）
          </el-tag>
        </div>
        <div style="margin-top:16px;text-align:right">
          <el-button @click="stepIndex = 2">上一步</el-button>
          <el-button type="primary" @click="handleGenerate">开始生成标书</el-button>
        </div>
      </el-card>

      <!-- 步骤5: 生成标书 -->
      <el-card v-if="stepIndex === 4">
        <template #header>步骤5：生成标书</template>
        <el-radio-group v-model="tenderType" style="margin-bottom:16px">
          <el-radio label="main">主标</el-radio>
          <el-radio label="sub">陪标</el-radio>
        </el-radio-group>
        <el-alert v-if="generateResult" :title="generateResult.message" type="success" show-icon />
        <div style="margin-top:16px;text-align:right">
          <el-button @click="stepIndex = 3">上一步</el-button>
          <el-button type="primary" @click="handleGenerateTender" :loading="generating">生成</el-button>
        </div>
      </el-card>

      <!-- 步骤6: 终审 -->
      <el-card v-if="stepIndex === 5">
        <template #header>步骤6：终审检查</template>
        <div v-if="reviewReport">
          <el-row :gutter="12" style="margin-bottom:16px">
            <el-col :span="6">
              <el-statistic title="通过" :value="summary.high" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="警告" :value="summary.medium" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="失败" :value="summary.low" />
            </el-col>
          </el-row>
          <el-table :data="reviewTableData" size="small">
            <el-table-column prop="name" label="检查项" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'pass' ? 'success' : row.status === 'warning' ? 'warning' : 'danger'">
                  {{ row.status === 'pass' ? '通过' : row.status === 'warning' ? '警告' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="issues" label="问题" />
          </el-table>
        </div>
        <div style="margin-top:16px;text-align:right">
          <el-button @click="stepIndex = 4">上一步</el-button>
          <el-button type="primary" @click="handleExport">导出标书</el-button>
        </div>
      </el-card>

      <!-- 步骤7: 导出 -->
      <el-card v-if="stepIndex === 6">
        <template #header>步骤7：导出</template>
        <el-radio-group v-model="exportFormat">
          <el-radio label="markdown">Markdown</el-radio>
          <el-radio label="word">Word</el-radio>
          <el-radio label="pdf">PDF</el-radio>
        </el-radio-group>
        <el-alert v-if="exportResult" :title="exportResult.message" type="success" show-icon style="margin-top:16px" />
        <div style="margin-top:16px;text-align:right">
          <el-button @click="stepIndex = 5">上一步</el-button>
          <el-button type="primary" @click="handleExportTender" :loading="exporting">导出</el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProject, parseTender, confirmParse, matchMaterials, generateTender, reviewTender, exportTender } from '@/api'
import type { Project, ParsedData, Chapter } from '@/types'

const router = useRouter()
const route = useRoute()
const projectId = Number(route.params.id)

const project = ref<Project | null>(null)
const parsedData = ref<ParsedData | null>(null)
const matchMessage = ref('')
const chapters = ref<Chapter[]>([])
const generateResult = ref<any>(null)
const reviewReport = ref<any>(null)
const summary = ref({ high: 0, medium: 0, low: 0 })
const exportResult = ref<any>(null)

const stepIndex = ref(0)
const parsing = ref(false)
const generating = ref(false)
const exporting = ref(false)
const tenderType = ref<'main' | 'sub'>('main')
const exportFormat = ref<'markdown' | 'word' | 'pdf'>('markdown')
const corrections = ref<Record<string, any>>({})

const statusType = (status: string) => ({ parsing: 'warning', parsed: 'success', materials_preparing: '', generating: 'info' }[status] || '')
const statusText = (status: string) => ({ parsing: '解析中', parsed: '已解析', materials_preparing: '材料准备', generating: '生成中' }[status] || status)

const reviewTableData = computed(() => {
  if (!reviewReport.value) return []
  return Object.entries(reviewReport.value).map(([name, val]: [string, any]) => ({
    name,
    status: val.status,
    issues: val.issues?.join('；') || '—',
  }))
})

const fetchProject = async () => {
  const res = await getProject(projectId)
  project.value = res.data
  // 根据状态推进步骤
  if (project.value.status === 'parsed') stepIndex.value = 2
  if (project.value.status === 'materials_preparing') stepIndex.value = 3
}

const handleParse = async () => {
  parsing.value = true
  try {
    const res = await parseTender(projectId)
    parsedData.value = res.data.parsed_data
    stepIndex.value = 1
  } catch (e: any) {
    ElMessage.error(e?.message || '解析失败')
  } finally {
    parsing.value = false
  }
}

const handleConfirmParse = async () => {
  await confirmParse(projectId, corrections.value)
  ElMessage.success('信息已确认')
  stepIndex.value = 3
}

const handleGenerate = async () => {
  const res = await matchMaterials(projectId, tenderType.value)
  matchMessage.value = res.data.message
  chapters.value = res.data.chapters
  stepIndex.value = 4
}

const handleGenerateTender = async () => {
  generating.value = true
  try {
    generateResult.value = await generateTender(projectId, tenderType.value)
    const review = await reviewTender(generateResult.value.tender_id)
    reviewReport.value = review.data.report
    summary.value = review.data.summary
    stepIndex.value = 5
  } catch (e: any) {
    ElMessage.error(e?.message || '生成失败')
  } finally {
    generating.value = false
  }
}

const handleExport = () => {
  stepIndex.value = 6
}

const handleExportTender = async () => {
  exporting.value = true
  try {
    exportResult.value = await exportTender(generateResult.value.tender_id, exportFormat.value)
    ElMessage.success('导出成功')
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(fetchProject)
</script>

<style scoped>
.project-detail {
  padding: 20px;
}
.project-info {
  margin: 20px 0;
}
.workflow-steps {
  margin: 20px 0;
}
.step-content {
  margin-top: 20px;
}
.chapter-item {
  padding: 12px;
  border-bottom: 1px solid #eee;
}
.chapter-item:last-child {
  border-bottom: none;
}
.chapter-item h4 {
  margin: 0 0 8px;
}
</style>
