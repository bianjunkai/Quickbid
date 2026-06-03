<template>
  <div class="sr" :class="{ 'sr--inline': inline }">
    <!-- Inline 模式（嵌套在表格/列表单元格里）：不递归，渲染为摘要文本 -->
    <span v-if="inline" class="sr-inline">{{ summarizeInline(value) }}</span>

    <!-- 数组 -->
    <template v-else-if="isArray">
      <el-table v-if="allObjects" :data="value" size="small" stripe>
        <el-table-column
          v-for="col in arrayColumns" :key="col" :prop="col" :label="col"
          :min-width="80"
        >
          <template #default="{ row }">
            <SchemaRenderer :value="row[col]" :inline="true" />
          </template>
        </el-table-column>
      </el-table>
      <ul v-else class="sr-list">
        <li v-for="(item, i) in value" :key="i">
          <SchemaRenderer :value="item" :inline="true" />
        </li>
      </ul>
    </template>

    <!-- 对象 -->
    <el-descriptions v-else-if="isObject" :column="1" border size="small">
      <el-descriptions-item v-for="k in objectKeys" :key="k" :label="k">
        <SchemaRenderer :value="(value as any)[k]" />
      </el-descriptions-item>
    </el-descriptions>

    <!-- 标量 -->
    <span v-else class="sr-scalar">{{ formatScalar(value) }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ value: any; inline?: boolean }>(), { inline: false })

const isArray = computed(() => Array.isArray(props.value))
const isObject = computed(() => props.value !== null && typeof props.value === 'object' && !Array.isArray(props.value))

const objectKeys = computed(() => (props.value && typeof props.value === 'object') ? Object.keys(props.value) : [])

const allObjects = computed(() => isArray.value && props.value.length > 0 && props.value.every((x: any) => x !== null && typeof x === 'object' && !Array.isArray(x)))

const arrayColumns = computed(() => {
  if (!isArray.value || props.value.length === 0) return []
  // union of keys, ordered by first occurrence
  const seen: string[] = []
  for (const item of props.value) {
    if (item && typeof item === 'object') {
      for (const k of Object.keys(item)) {
        if (!seen.includes(k)) seen.push(k)
      }
    }
  }
  return seen.slice(0, 8) // cap to 8 columns
})

function isScalar(v: any) {
  return v === null || v === undefined || typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean'
}

function formatScalar(v: any): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'string' && v.length > 200) return v.slice(0, 200) + '…'
  return String(v)
}

/**
 * Inline 模式：用于嵌套在表格/列表单元格里。
 * - 标量 → 直接显示
 * - 小对象（≤4 个标量字段）→ 渲染为 "k1=v1, k2=v2" 列表
 * - 小数组（≤3 项）→ 渲染为 "a, b, c" 列表
 * - 大对象/数组 → 摘要 "{N 字段} / [N 项]"
 */
function summarizeInline(v: any): string {
  if (v === null || v === undefined) return '—'
  if (isScalar(v)) return formatScalar(v)

  if (Array.isArray(v)) {
    if (v.length === 0) return '[]'
    if (v.length <= 3 && v.every(isScalar)) {
      return v.map(formatScalar).join('、')
    }
    return `[${v.length} 项]`
  }

  if (typeof v === 'object') {
    const entries = Object.entries(v)
    if (entries.length === 0) return '{}'
    if (entries.length <= 4 && entries.every(([_, val]) => isScalar(val))) {
      return entries.map(([k, val]) => `${k}: ${formatScalar(val)}`).join('；')
    }
    return `{${entries.length} 字段}`
  }
  return formatScalar(v)
}
</script>

<style scoped>
.sr-scalar { color: var(--qb-ink); font-size: 13px; }
.sr-inline { color: var(--qb-ink); font-size: 12px; line-height: 1.5; word-break: break-word; }
.sr-list { margin: 0; padding-left: 18px; font-size: 12px; color: var(--qb-ink); }
.sr-list li { margin: 2px 0; }
</style>
