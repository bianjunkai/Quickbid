<template>
  <div class="project-detail">
    <el-page-header @back="router.push('/projects')" content="项目详情" />

    <!-- 项目信息 -->
    <el-card class="project-info" v-loading="projectLoading">
      <template v-if="project">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="项目名称">{{ project.name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(project.status)">{{ statusText(project.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="招标文件">{{ project.tender_file_path || '—' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ project.created_at }}</el-descriptions-item>
          <el-descriptions-item label="招标编号">{{ project.tender_no || '—' }}</el-descriptions-item>
          <el-descriptions-item label="预算">{{ project.budget ? `${project.budget.toLocaleString()}` : '—' }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <el-skeleton v-else :rows="3" animated />
    </el-card>

    <!-- 工作流步骤条 -->
    <el-steps :active="stepIndex" finish-status="success" class="workflow-steps">
      <el-step title="上传文件" />
      <el-step title="AI解析" />
      <el-step title="确认信息" />
      <el-step title="材料匹配" />
      <el-step title="生成标书" />
      <el-step title="终审检查" />
      <el-step title="导出" />
    </el-steps>

    <!-- 步骤内容区 -->
    <div class="step-content">
      <!-- Step 0: 上传/提交文件 -->
      <el-card v-if="stepIndex === 0">
        <template #header>步骤1：上传招标文件</template>
        <p>请将招标文件（PDF/Word）放到以下路径后点击"开始解析"。</p>
        <el-alert
          v-if="project?.tender_file_path"
          :title="`文件路径：${project.tender_file_path}`"
          type="info" show-icon style="margin-bottom:12px"
        />
        <el-result
          v-if="parseError"
          icon="error"
          title="解析失败"
          :sub-title="parseError"
        >
          <template #extra>
            <el-button type="primary" @click="handleParse">重试</el-button>
          </template>
        </el-result>
        <div style="margin-top:16px;text-align:right">
          <el-button type="primary" @click="handleParse" :loading="parsing" :disabled="!project">
            {{ parsing ? '解析中...' : '开始解析' }}
          </el-button>
        </div>
      </el-card>

      <!-- Step 1: AI解析结果 -->
      <el-card v-if="stepIndex === 1">
        <template #header>步骤2：AI 解析结果</template>
        <el-descriptions :column="2" border size="small" v-if="parsedData">
          <el-descriptions-item
            v-for="(val, key) in parsedData" :key="key"
            :label="String(key).replace('K0', 'K')"
          >
            <template v-if="Array.isArray(val)">
              <el-tag v-for="(item, i) in val" :key="i" size="small" style="margin:2px">{{ item }}</el-tag>
            </template>
            <template v-else>
              {{ val || '—' }}
            </template>
          </el-descriptions-item>
        </el-descriptions>
        <el-skeleton v-else :rows="6" animated />
        <div style="margin-top:16px;text-align:right">
          <el-button @click="stepIndex = 0">上一步</el-button>
          <el-button type="primary" @click="stepIndex = 2">信息正确，继续</el-button>
        </div>
      </el-card>

      <!-- Step 2: 确认/纠错 -->
      <el-card v-if="stepIndex === 2">
        <template #header>步骤3：确认信息</template>
        <p style="margin-bottom:12px;color:#666">如有错误请在下方修正，否则直接确认。</p>
        <el-form label-width="140px">
          <el-form-item label="招标编号">
            <el-input v-model="corrections.tender_no" placeholder="修正招标编号" />
          </el-form-item>
          <el-form-item label="预算金额（万元）">
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
          <el-button type="primary" @click="handleConfirmParse" :loading="confirming">确认并匹配材料</el-button>
        </div>
      </el-card>

      <!-- Step 3: 材料匹配结果 -->
      <el-card v-if="stepIndex === 3">
        <template #header>步骤4：材料匹配</template>
        <div v-if="chapters.length" class="chapter-list">
          <div v-for="(ch, idx) in chapters" :key="idx" class="chapter-item">
            <div class="chapter-header">
              <strong>{{ ch.chapter }}</strong>
              <el-tag size="small" :type="ch.match_score === '高' ? 'success' : 'warning'">
                匹配度：{{ ch.match_score }}
              </el-tag>
            </div>
            <p class="chapter-material">→ {{ ch.material_title }}</p>
            <p class="chapter-reason">{{ ch.reason }}</p>
          </div>
        </div>
        <el-skeleton v-else-if="matching" :rows="4" animated />
        <el-empty v-else description="暂无匹配结果" />
        <div style="margin-top:16px;text-align:right">
          <el-button @click="stepIndex = 2">上一步</el-button>
          <el-button type="primary" @click="stepIndex = 4">确认匹配，进入生成</el-button>
        </div>
      </el-card>

      <!-- Step 4: 生成标书 -->
      <el-card v-if="stepIndex === 4">
        <template #header>步骤5：生成标书</template>
        <el-form label-width="100px">
          <el-form-item label="标书类型">
            <el-radio-group v-model="tenderType">
              <el-radio label="main">主标</el-radio>
              <el-radio label="sub">陪标</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="tenderType === 'sub'" label="生成陪标">
            <el-checkbox v-model="needSubBid">同时生成陪标（生成后自动审查）</el-checkbox>
          </el-form-item>
          <el-form-item v-else label="生成主标">
            <el-checkbox v-model="needSubBid">同时生成陪标（生成后自动审查）</el-checkbox>
          </el-form-item>
        </el-form>
        <el-alert v-if="generateError" :title="generateError" type="error" show-icon style="margin-bottom:12px" closable @close="generateError = ''" />
        <el-alert v-if="generateMessage" :title="generateMessage" type="success" show-icon style="margin-bottom:12px" />
        <div style="margin-top:16px;text-align:right">
          <el-button @click="stepIndex = 3">上一步</el-button>
          <el-button type="primary" @click="handleGenerateTender" :loading="generating">
            {{ generating ? '生成中...' : '开始生成' }}
          </el-button>
        </div>
      </el-card>

      <!-- Step 5: 终审 -->
      <el-card v-if="stepIndex === 5">
        <template #header>步骤6：终审检查</template>
        <div v-if="reviewChecks.length">
          <el-row :gutter="12" style="margin-bottom:16px">
            <el-col :span="8">
              <el-statistic title="通过" :value="reviewSummary.low || 0">
                <template #suffix><span style="font-size:14px;color:#67c23a">项</span></template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="警告" :value="reviewSummary.medium || 0">
                <template #suffix><span style="font-size:14px;color:#e6a23c">项</span></template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="失败" :value="reviewSummary.high || 0">
                <template #suffix><span style="font-size:14px;color:#f56c6c">项</span></template>
              </el-statistic>
            </el-col>
          </el-row>
          <el-table :data="reviewChecks" size="small" stripe>
            <el-table-column prop="check_id" label="编号" width="100" />
            <el-table-column prop="check_name" label="检查项" min-width="180" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'pass' ? 'success' : row.status === 'warning' ? 'warning' : 'danger'" size="small">
                  {{ row.status === 'pass' ? '通过' : row.status === 'warning' ? '警告' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="issue" label="问题描述" min-width="200">
              <template #default="{ row }">
                <span :style="{ color: row.status !== 'pass' ? '#e6a23c' : '' }">{{ row.issue || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="suggestion" label="建议" min-width="150">
              <template #default="{ row }">{{ row.suggestion || '—' }}</template>
            </el-table-column>
          </el-table>
          <!-- 陪标审查结果 -->
          <el-divider v-if="subReviewChecks.length" />
          <h4 v-if="subReviewChecks.length" style="margin-bottom:12px">陪标审查结果</h4>
          <el-table v-if="subReviewChecks.length" :data="subReviewChecks" size="small" stripe>
            <el-table-column prop="check_id" label="编号" width="100" />
            <el-table-column prop="check_name" label="检查项" min-width="180" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'pass' ? 'success' : row.status === 'warning' ? 'warning' : 'danger'" size="small">
                  {{ row.status === 'pass' ? '通过' : row.status === 'warning' ? '警告' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="issue" label="问题描述" min-width="200" />
          </el-table>
        </div>
        <el-skeleton v-else-if="reviewing" :rows="4" animated />
        <el-empty v-else description="暂无审查结果" />
        <div style="margin-top:16px;text-align:right">
          <el-button @click="stepIndex = 4">上一步</el-button>
          <el-button type="primary" @click="stepIndex = 6">进入导出</el-button>
        </div>
      </el-card>

      <!-- Step 6: 导出 -->
      <el-card v-if="stepIndex === 6">
        <template #header>步骤7：导出</template>
        <el-form label-width="80px">
          <el-form-item label="导出格式">
            <el-radio-group v-model="exportFormat">
              <el-radio label="word">Word (.docx)</el-radio>
              <el-radio label="pdf">PDF</el-radio>
              <el-radio label="markdown">Markdown</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
        <el-alert v-if="exportResult" :title="exportResult" type="success" show-icon style="margin-top:12px" />
        <div style="margin-top:16px;text-align:right">
          <el-button @click="stepIndex = 5">上一步</el-button>
          <el-button type="primary" @click="handleExportTender" :loading="exporting">
            {{ exporting ? '导出中...' : '导出' }}
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getProject, parseTender, confirmParse, matchMaterials,
  generateTender, reviewTender, exportTender,
} from '@/api'
import type { Project, ParsedData, Chapter, ReviewCheck, ReviewSummary } from '@/types'

const router = useRouter()
const route = useRoute()
const projectId = Number(route.params.id)

const project = ref<Project | null>(null)
const projectLoading = ref(true)
const parsedData = ref<ParsedData | null>(null)
const chapters = ref<Chapter[]>([])
const reviewChecks = ref<ReviewCheck[]>([])
const subReviewChecks = ref<ReviewCheck[]>([])
const reviewSummary = ref<ReviewSummary>({ high: 0, medium: 0, low: 0 })

const stepIndex = ref(0)
const parsing = ref(false)
const confirming = ref(false)
const matching = ref(false)
const generating = ref(false)
const reviewing = ref(false)
const exporting = ref(false)

const tenderType = ref<'main' | 'sub'>('main')
const needSubBid = ref(false)
const exportFormat = ref<'word' | 'pdf' | 'markdown'>('word')
const corrections = ref<Record<string, any>>({})
const tenderId = ref<number | null>(null)

const parseError = ref('')
const generateError = ref('')
const generateMessage = ref('')
const exportResult = ref('')

const STATUS_MAP: Record<string, { type: string; text: string }> = {
  parsing: { type: 'warning', text: '解析中' },
  parsed: { type: 'success', text: '已解析' },
  materials_preparing: { type: '', text: '材料准备' },
  generating: { type: 'info', text: '生成中' },
  reviewing: { type: 'info', text: '审查中' },
  done: { type: 'success', text: '已完成' },
}

const statusType = (s: string) => STATUS_MAP[s]?.type || ''
const statusText = (s: string) => STATUS_MAP[s]?.text || s

const fetchProject = async () => {
  projectLoading.value = true
  try {
    const res = await getProject(projectId)
    project.value = res.data
  } catch (e: any) {
    ElMessage.error('加载项目失败')
  } finally {
    projectLoading.value = false
  }
}

const handleParse = async () => {
  parseError.value = ''
  parsing.value = true
  try {
    const res = await parseTender(projectId)
    parsedData.value = res.data.parsed_data
    stepIndex.value = 1
    ElMessage.success('解析完成')
  } catch (e: any) {
    parseError.value = e?.response?.data?.detail || '解析失败，请确认文件已放置'
  } finally {
    parsing.value = false
  }
}

const handleConfirmParse = async () => {
  confirming.value = true
  try {
    await confirmParse(projectId, Object.keys(corrections.value).length ? corrections.value : undefined)
    ElMessage.success('信息已确认')

    // 确认后自动加载材料匹配
    matching.value = true
    stepIndex.value = 3
    const matchRes = await matchMaterials(projectId, tenderType.value)
    chapters.value = matchRes.data.chapters || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    confirming.value = false
    matching.value = false
  }
}

const handleGenerateTender = async () => {
  generateError.value = ''
  generateMessage.value = ''
  generating.value = true
  try {
    // 调用 generate API（走 Orchestrator 自动工作流）
    const genRes = await generateTender(projectId, tenderType.value, undefined, needSubBid.value)

    tenderId.value = genRes.data?.tender_id || genRes.data?.main_review ? projectId : projectId

    // 如果有 main_review（自动工作流返回），直接展示
    if (genRes.data.main_review?.checks) {
      reviewChecks.value = genRes.data.main_review.checks
      reviewSummary.value = genRes.data.main_review.summary || { high: 0, medium: 0, low: 0 }
    }

    if (genRes.data.sub_review?.checks) {
      subReviewChecks.value = genRes.data.sub_review.checks
    }

    generateMessage.value = genRes.data.message || '标书生成完成'
    stepIndex.value = 5
    ElMessage.success('生成完成')
  } catch (e: any) {
    generateError.value = e?.response?.data?.detail || '生成失败'
  } finally {
    generating.value = false
  }
}

const handleExportTender = async () => {
  exporting.value = true
  try {
    const res = await exportTender(tenderId.value || projectId, exportFormat.value)
    exportResult.value = res.data.message || res.data.export_path || '导出成功'
    ElMessage.success('导出成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(fetchProject)
</script>

<style scoped>
.project-detail { padding: 20px; }
.project-info { margin: 20px 0; }
.workflow-steps { margin: 20px 0; }
.step-content { margin-top: 20px; }

.chapter-list { margin-bottom: 16px; }
.chapter-item {
  padding: 12px;
  border-bottom: 1px solid #eee;
}
.chapter-item:last-child { border-bottom: none; }
.chapter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.chapter-material { margin: 4px 0; color: #409eff; }
.chapter-reason { color: #999; font-size: 13px; margin: 0; }
</style>
