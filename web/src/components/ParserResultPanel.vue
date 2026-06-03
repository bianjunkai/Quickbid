<template>
  <aside class="prp" :class="{ 'prp--embedded': embedded }" v-if="data">
    <!-- Meta header -->
    <div class="prp-hd">
      <div class="prp-hd-row">
        <span class="prp-hd-title">解析报告</span>
        <el-tag size="small" :type="modeTagType" effect="dark">{{ modeLabel }}</el-tag>
      </div>
      <div class="prp-meta">
        <div v-if="data.meta?.source_file" class="prp-meta-item">
          <span class="prp-meta-k">文件</span>
          <span class="prp-meta-v" :title="data.meta.source_file">{{ truncate(data.meta.source_file, 28) }}</span>
        </div>
        <div v-if="data.meta?.page_count" class="prp-meta-item">
          <span class="prp-meta-k">页数</span>
          <span class="prp-meta-v">{{ data.meta.page_count }}</span>
        </div>
        <div v-if="data.meta?.parse_time" class="prp-meta-item">
          <span class="prp-meta-k">时间</span>
          <span class="prp-meta-v">{{ formatTime(data.meta.parse_time) }}</span>
        </div>
        <div v-if="data._text_length" class="prp-meta-item">
          <span class="prp-meta-k">文本</span>
          <span class="prp-meta-v">{{ data._text_length.toLocaleString() }} 字</span>
        </div>
        <div v-if="data._marker_summary?.total_hits != null" class="prp-meta-item">
          <span class="prp-meta-k">标记</span>
          <span class="prp-meta-v">{{ data._marker_summary.total_hits }} hits</span>
        </div>
      </div>
      <el-alert
        v-if="data._hint"
        :title="data._hint"
        type="info" :closable="false" show-icon
        class="prp-hint"
      />
      <el-alert
        v-if="data._error"
        :title="data._error"
        type="error" :closable="false" show-icon
        class="prp-hint"
      />
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" class="prp-tabs" type="border-card">
      <!-- K01-K14 -->
      <el-tab-pane label="K01-K14 关键字段" name="k01k14">
        <el-descriptions :column="1" border size="small" class="prp-desc">
          <el-descriptions-item
            v-for="item in k01k14Items" :key="item.key" :label="item.label"
          >
            <template v-if="item.type === 'array'">
              <div v-if="item.value.length" class="prp-chips">
                <el-tag
                  v-for="(v, i) in item.value" :key="i" size="small"
                  :type="item.danger ? 'danger' : 'warning'" effect="plain"
                >{{ v }}</el-tag>
              </div>
              <span v-else class="prp-muted">—</span>
            </template>
            <template v-else-if="item.type === 'long'">
              <pre class="prp-mono">{{ item.value }}</pre>
            </template>
            <template v-else>
              <span :class="{ 'prp-muted': !item.value }">{{ item.value || '—' }}</span>
            </template>
          </el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>

      <!-- 标记扫描 -->
      <el-tab-pane label="标记扫描" name="markers">
        <div v-if="markerSummary" class="prp-stats">
          <el-statistic title="总标记数" :value="markerSummary.total_hits" />
          <el-statistic title="扫描页数" :value="markerSummary.page_count" />
        </div>

        <h4 class="prp-section-h">按符号</h4>
        <el-table v-if="symbolRows.length" :data="symbolRows" size="small" stripe>
          <el-table-column prop="symbol" label="符号" width="80" />
          <el-table-column prop="count" label="次数" width="80" sortable />
          <el-table-column label="分布">
            <template #default="{ row }">
              <div class="prp-bar">
                <div class="prp-bar-fill" :style="{ width: row.pct + '%' }" />
                <span class="prp-bar-text">{{ row.pct }}%</span>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="无标记扫描数据" :image-size="60" />

        <h4 class="prp-section-h">按页码</h4>
        <div v-if="pageBars.length" class="prp-page-bars">
          <div v-for="row in pageBars" :key="row.page" class="prp-page-bar">
            <span class="prp-page-num">P{{ row.page }}</span>
            <div class="prp-bar prp-bar--full">
              <div class="prp-bar-fill" :style="{ width: row.pct + '%' }" />
              <span class="prp-bar-text">{{ row.count }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else description="无页码分布数据" :image-size="60" />

        <template v-if="data.marker_semantics?.detection">
          <h4 class="prp-section-h">符号语义（LLM 识别）</h4>
          <el-table
            v-if="data.marker_semantics.detection.markers?.length"
            :data="data.marker_semantics.detection.markers" size="small" stripe
          >
            <el-table-column prop="symbol" label="符号" width="80" />
            <el-table-column prop="semantic_label" label="语义" min-width="120" />
            <el-table-column prop="priority" label="优先级" width="80" />
            <el-table-column prop="maps_to_field" label="映射字段" min-width="120" />
          </el-table>
          <el-empty v-else description="无符号语义数据" :image-size="60" />
        </template>

        <template v-if="data.marker_extractions?.extraction_summary">
          <h4 class="prp-section-h">抽取摘要</h4>
          <div class="prp-stats prp-stats--4">
            <el-statistic title="总出现" :value="data.marker_extractions.extraction_summary.total_marker_occurrences || 0" />
            <el-statistic title="已映射" :value="data.marker_extractions.extraction_summary.total_mapped || 0" />
            <el-statistic title="未映射" :value="data.marker_extractions.extraction_summary.unmapped_count || 0" />
            <el-statistic
              title="未映射率"
              :value="unmappedRate"
              :suffix="`%`"
            />
          </div>
        </template>
      </el-tab-pane>

      <!-- 风险条款 -->
      <el-tab-pane label="风险条款" name="risks">
        <div v-if="riskGroups.length" class="prp-risks">
          <div v-for="g in riskGroups" :key="g.severity" class="prp-risk-group">
            <div class="prp-risk-hd" @click="g.open = !g.open">
              <el-tag size="small" :type="g.tagType" effect="dark">{{ g.label }}</el-tag>
              <span class="prp-risk-count">{{ g.items.length }} 项</span>
              <span class="prp-risk-toggle">{{ g.open ? '▾' : '▸' }}</span>
            </div>
            <div v-if="g.open" class="prp-risk-body">
              <div v-for="(it, i) in g.items" :key="i" class="prp-risk-item">
                <div class="prp-risk-item-hd">
                  <el-tag v-if="it.marker" size="small">{{ it.marker }}</el-tag>
                  <el-tag v-if="it.source_page != null" size="small" type="info">P{{ it.source_page }}</el-tag>
                  <span v-if="it.semantic" class="prp-risk-semantic">{{ it.semantic }}</span>
                </div>
                <pre v-if="it.raw_text" class="prp-mono prp-mono--sm">{{ it.raw_text }}</pre>
                <pre v-else class="prp-mono prp-mono--sm">{{ JSON.stringify(it, null, 2) }}</pre>
              </div>
            </div>
          </div>
        </div>
        <el-empty
          v-else
          :description="data._mode === 'manual' ? '降级模式未抽取条款（需 LLM 智能解析）' : '未发现风险条款'"
          :image-size="60"
        />
      </el-tab-pane>

      <!-- 结构化数据 -->
      <el-tab-pane label="结构化数据" name="schema">
        <el-collapse v-model="openModules">
          <el-collapse-item
            v-for="mod in schemaModules" :key="mod.key" :name="mod.key"
          >
            <template #title>
              <div class="prp-mod-hd">
                <span class="prp-mod-name">{{ mod.label }}</span>
                <el-tag v-if="mod.missing" size="small" type="info">降级模式</el-tag>
              </div>
            </template>
            <div v-if="mod.missing" class="prp-mod-missing">
              <p class="prp-muted">该模块需要 LLM 智能解析。当前为 manual 模式，仅完成文本提取与标记扫描。</p>
              <template v-if="data._text_preview">
                <h5 class="prp-section-h prp-section-h--sm">文本预览（前 2000 字）</h5>
                <pre class="prp-mono">{{ data._text_preview }}</pre>
              </template>
            </div>
            <SchemaRenderer v-else :value="mod.value" />
          </el-collapse-item>
          <el-collapse-item v-if="data._validation" name="_validation" title="校验报告">
            <SchemaRenderer :value="data._validation" />
          </el-collapse-item>
        </el-collapse>
      </el-tab-pane>
    </el-tabs>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ParsedData, MarkerItem } from '@/types'
import SchemaRenderer from './SchemaRenderer.vue'

const props = withDefaults(defineProps<{ data: ParsedData | null; embedded?: boolean }>(), { embedded: false })

const activeTab = ref('k01k14')

// ---- K01-K14 normalization ----
const K_LABELS: Record<string, string> = {
  K01: '项目名称', K02: '招标编号', K03: '招标人', K04: '预算金额',
  K05: '投标截止时间', K06: '开标时间', K07: '评分标准', K08: '技术要求',
  K09: '商务资质要求', K10: '★ 星标项', K11: '✕ 废标条款',
  K12: '章节模板要求', K13: '偏离表格式要求', K14: '演示要求',
}
const K_DANGER = new Set(['K10', 'K11'])

const k01k14Items = computed(() => {
  if (!props.data) return []
  return Object.keys(K_LABELS).map((k) => {
    const key = `${k}_${K_LABELS[k].replace(/^[★✕]\s*/, '')}`
    const value = (props.data as any)[key]
    if (Array.isArray(value)) {
      return { key, label: K_LABELS[k], value, type: 'array', danger: K_DANGER.has(k) }
    }
    if (typeof value === 'string' && value.length > 200) {
      return { key, label: K_LABELS[k], value, type: 'long' }
    }
    return { key, label: K_LABELS[k], value: value ?? '', type: 'text' }
  })
})

// ---- Mode badge ----
const modeLabel = computed(() => {
  const m = props.data?._mode
  if (m === 'full') return 'FULL · 五步管道'
  if (m === 'quick') return 'QUICK · 快速'
  if (m === 'manual') return 'MANUAL · 降级'
  if (m === 'error') return 'ERROR'
  return m ? m.toUpperCase() : 'UNKNOWN'
})
const modeTagType = computed<'success' | 'warning' | 'danger' | 'info'>(() => {
  const m = props.data?._mode
  if (m === 'full') return 'success'
  if (m === 'quick') return 'warning'
  if (m === 'manual' || m === 'error') return 'danger'
  return 'info'
})

// ---- Markers ----
const markerSummary = computed(() => props.data?._marker_summary)
const symbolRows = computed(() => {
  const s = markerSummary.value?.by_symbol || {}
  const total = Object.values(s).reduce((a, b) => a + b, 0) || 1
  return Object.entries(s)
    .map(([symbol, count]) => ({
      symbol, count,
      pct: Math.round((count / total) * 100),
    }))
    .sort((a, b) => b.count - a.count)
})
const pageBars = computed(() => {
  const p = markerSummary.value?.by_page || {}
  const entries = Object.entries(p)
    .map(([page, count]) => ({ page: Number(page), count: Number(count) }))
    .sort((a, b) => a.page - b.page)
  const max = Math.max(...entries.map((e) => e.count), 1)
  return entries.map((e) => ({ ...e, pct: Math.round((e.count / max) * 100) }))
})
const unmappedRate = computed(() => {
  const es = props.data?.marker_extractions?.extraction_summary
  if (!es?.total_marker_occurrences) return 0
  return Math.round(((es.unmapped_count || 0) / es.total_marker_occurrences) * 100)
})

// ---- Risks ----
const RISK_GROUPS: Array<{ key: keyof NonNullable<ParsedData['marker_extractions']>; label: string; tagType: 'danger' | 'warning' | 'info' }> = [
  { key: 'fatal_items', label: '致命', tagType: 'danger' },
  { key: 'critical_items', label: '严重', tagType: 'danger' },
  { key: 'high_items', label: '高危', tagType: 'warning' },
  { key: 'medium_items', label: '中等', tagType: 'warning' },
  { key: 'low_items', label: '低', tagType: 'info' },
]
const riskGroups = computed(() => {
  if (!props.data?.marker_extractions) return []
  return RISK_GROUPS
    .map((g) => ({
      severity: g.key,
      label: g.label,
      tagType: g.tagType,
      items: (props.data!.marker_extractions as any)?.[g.key] as MarkerItem[] || [],
      open: false,
    }))
    .filter((g) => g.items.length > 0)
})

// ---- Schema modules ----
const SCHEMA_MODULES = [
  { key: 'base', label: '基础信息' },
  { key: 'qualification', label: '资质要求' },
  { key: 'rejection', label: '废标条款' },
  { key: 'scoring', label: '评分标准' },
  { key: 'tech', label: '技术要求' },
  { key: 'commercial', label: '商务要求' },
  { key: 'templates', label: '模板与格式' },
  { key: 'logistics', label: '时间地点' },
] as const

const schemaModules = computed(() => {
  if (!props.data) return []
  return SCHEMA_MODULES.map((m) => {
    const v = (props.data as any)[m.key]
    return {
      key: m.key,
      label: m.label,
      value: v,
      missing: !v,
    }
  })
})
const openModules = ref<string[]>(['base'])

// ---- Utils ----
function truncate(s: string, n: number) {
  if (!s) return ''
  return s.length > n ? s.slice(0, n) + '…' : s
}
function formatTime(s: string) {
  if (!s) return ''
  try {
    const d = new Date(s)
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return s }
}
</script>

<style scoped>
.prp {
  background: var(--qb-surface);
  border-left: 1px solid var(--qb-border);
  width: 360px;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}
.prp--embedded {
  width: 100%;
  border-left: none;
}

.prp-hd {
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--qb-border);
  background: var(--qb-paper);
  flex-shrink: 0;
}
.prp-hd-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.prp-hd-title { font-size: 13px; font-weight: 600; color: var(--qb-ink); }
.prp-meta { display: flex; flex-wrap: wrap; gap: 6px 12px; }
.prp-meta-item { display: flex; align-items: baseline; gap: 4px; font-size: 11px; }
.prp-meta-k { color: var(--qb-stone); text-transform: uppercase; letter-spacing: 0.3px; }
.prp-meta-v { color: var(--qb-ink); font-weight: 500; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.prp-hint { margin-top: 10px; }

.prp-tabs { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.prp-tabs :deep(.el-tabs__content) { flex: 1; overflow-y: auto; padding: 12px 14px; }
.prp-tabs :deep(.el-tab-pane) { height: 100%; }

.prp-desc { margin-top: 4px; }
.prp-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.prp-mono {
  font-family: var(--qb-font-mono);
  font-size: 11px;
  line-height: 1.55;
  background: var(--qb-paper);
  border: 1px solid var(--qb-border);
  border-radius: 2px;
  padding: 8px 10px;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 280px;
  overflow-y: auto;
  color: var(--qb-ink);
}
.prp-mono--sm { max-height: 120px; font-size: 10.5px; }
.prp-muted { color: var(--qb-stone); font-style: italic; }

.prp-stats {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
  padding: 10px 0 14px; border-bottom: 1px solid var(--qb-border); margin-bottom: 12px;
}
.prp-stats--4 { grid-template-columns: repeat(4, 1fr); }
.prp-stats :deep(.el-statistic__head) { font-size: 11px; color: var(--qb-stone); }
.prp-stats :deep(.el-statistic__number) { font-size: 18px; }

.prp-section-h {
  font-size: 11px; font-weight: 600; color: var(--qb-ink-light);
  text-transform: uppercase; letter-spacing: 0.4px; margin: 14px 0 8px;
}
.prp-section-h--sm { margin-top: 4px; }

.prp-bar {
  position: relative; height: 16px; background: var(--qb-paper);
  border: 1px solid var(--qb-border); border-radius: 2px; overflow: hidden;
}
.prp-bar--full { flex: 1; }
.prp-bar-fill { position: absolute; left: 0; top: 0; bottom: 0; background: var(--qb-amber-light); }
.prp-bar-text {
  position: absolute; left: 0; right: 0; top: 0; bottom: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 600; color: var(--qb-ink);
}

.prp-page-bars { display: flex; flex-direction: column; gap: 4px; }
.prp-page-bar { display: flex; align-items: center; gap: 8px; }
.prp-page-num { font-family: var(--qb-font-mono); font-size: 11px; color: var(--qb-stone); width: 32px; flex-shrink: 0; }

.prp-risks { display: flex; flex-direction: column; gap: 8px; }
.prp-risk-group { border: 1px solid var(--qb-border); border-radius: 2px; overflow: hidden; }
.prp-risk-hd {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  background: var(--qb-paper); cursor: pointer; user-select: none;
}
.prp-risk-hd:hover { background: var(--qb-amber-light); }
.prp-risk-count { font-size: 12px; color: var(--qb-ink); font-weight: 500; flex: 1; }
.prp-risk-toggle { font-size: 10px; color: var(--qb-stone); }
.prp-risk-body { padding: 8px 10px; display: flex; flex-direction: column; gap: 6px; background: var(--qb-surface); }
.prp-risk-item { padding: 6px 0; border-top: 1px dashed var(--qb-border); }
.prp-risk-item:first-child { border-top: none; }
.prp-risk-item-hd { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.prp-risk-semantic { font-size: 11px; color: var(--qb-stone); }

.prp-mod-hd { display: flex; align-items: center; gap: 8px; }
.prp-mod-name { font-weight: 500; }
.prp-mod-missing { padding: 4px 0; }
</style>
