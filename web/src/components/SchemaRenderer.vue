<template>
  <div class="sr">
    <!-- 数组 -->
    <template v-if="isArray">
      <el-table v-if="allObjects" :data="value" size="small" stripe>
        <el-table-column
          v-for="col in arrayColumns" :key="col" :prop="col" :label="col"
          :min-width="80"
        >
          <template #default="{ row }">
            <span v-if="isScalar(row[col])">{{ formatScalar(row[col]) }}</span>
            <span v-else class="sr-obj">{{ summarize(row[col]) }}</span>
          </template>
        </el-table-column>
      </el-table>
      <ul v-else class="sr-list">
        <li v-for="(item, i) in value" :key="i">
          <span v-if="isScalar(item)">{{ formatScalar(item) }}</span>
          <span v-else class="sr-obj">{{ summarize(item) }}</span>
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

const props = defineProps<{ value: any }>()

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

function summarize(v: any): string {
  if (v === null || v === undefined) return '—'
  if (Array.isArray(v)) return `[${v.length} 项]`
  if (typeof v === 'object') {
    const keys = Object.keys(v)
    return `{${keys.length} 字段}`
  }
  return formatScalar(v)
}
</script>

<style scoped>
.sr-scalar { color: var(--qb-ink); font-size: 13px; }
.sr-obj { font-family: var(--qb-font-mono); font-size: 11px; color: var(--qb-stone); }
.sr-list { margin: 0; padding-left: 18px; font-size: 12px; color: var(--qb-ink); }
.sr-list li { margin: 2px 0; }
</style>
