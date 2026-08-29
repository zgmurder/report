<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NDataTable,
  NDatePicker,
  NEmpty,
  NIcon,
  NSelect,
  NSpace,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { Bot, Database, FileInput, RefreshCw, Search } from 'lucide-vue-next'
import { useDepartmentStore } from '@/stores/department'
import { useUserStore } from '@/stores/user'
import type { DepartmentItem } from '@/api/department'
import {
  executeReportSearch,
  getReportSearchClassifications,
  getReportSearchOptions,
  type SearchClassificationItem,
  type SearchOptions,
  type SearchResult,
} from '@/api/reportSearch'

const emit = defineEmits<{
  generateDraft: []
  insertHtml: [html: string]
}>()

const message = useMessage()
const userStore = useUserStore()
const departmentStore = useDepartmentStore()
const activeTab = ref<'search' | 'ai'>('search')
const loadingOptions = ref(false)
const querying = ref(false)
const options = ref<SearchOptions | null>(null)
const source = ref<'jjd_jjd' | 'fkd_fkd'>('jjd_jjd')
const range = ref<[number, number] | null>(defaultTimeRange())
const activeTimePreset = ref('yesterday')
const categoryCodes = ref<string[]>([])
const typeCodes = ref<string[]>([])
const detailCodes = ref<string[]>([])
const categories = ref<SearchClassificationItem[]>([])
const types = ref<SearchClassificationItem[]>([])
const details = ref<SearchClassificationItem[]>([])
const loadingClassifications = ref(false)
const result = ref<SearchResult | null>(null)

const currentUnitCode = computed(() => {
  const configured = userStore.user?.unit_code
  if (configured) return configured
  return userStore.user?.roles.includes('admin') ? '330782000000' : ''
})

const currentDepartmentName = computed(() => {
  const code = currentUnitCode.value
  if (!code) return '当前账号未配置部门'
  const findName = (items: DepartmentItem[]): string | null => {
    for (const item of items) {
      if (item.code === code) return item.name
      const childName = item.children?.length ? findName(item.children) : null
      if (childName) return childName
    }
    return null
  }
  return findName(departmentStore.departmentTree) || options.value?.current_department.name || (code === '330782000000' ? '义乌市局' : code)
})

const sourceOptions = computed(() =>
  (options.value?.data_sources || [{ key: 'jjd_jjd', name: '接警单', enabled: true }]).map((item) => ({ label: item.name, value: item.key, disabled: !item.enabled })),
)
const categoryOptions = computed(() => categories.value.map((item) => ({ label: item.name, value: item.code })))
const typeOptions = computed(() => types.value.map((item) => ({ label: item.name, value: item.code })))
const detailOptions = computed(() => details.value.map((item) => ({ label: item.name, value: item.code })))
const tableColumns = computed<DataTableColumns<Record<string, unknown>>>(() =>
  (result.value?.columns || []).map((column) => ({
    title: column.label,
    key: column.key,
    minWidth: column.type === 'number' ? 96 : 120,
    ellipsis: { tooltip: true },
  })),
)

function startOfDay(date = new Date()) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function addDays(date: Date, days: number) {
  const value = new Date(date)
  value.setDate(value.getDate() + days)
  return value
}

function defaultTimeRange(): [number, number] {
  const today = startOfDay()
  return [addDays(today, -1).getTime(), today.getTime()]
}

function lunarNewYear(year: number) {
  const formatter = new Intl.DateTimeFormat('zh-CN-u-ca-chinese', { month: 'numeric', day: 'numeric' })
  for (let date = new Date(year, 0, 15); date <= new Date(year, 2, 1); date = addDays(date, 1)) {
    const parts = formatter.formatToParts(date)
    const month = parts.find((part) => part.type === 'month')?.value
    const day = parts.find((part) => part.type === 'day')?.value
    if (month === '1' && day === '1') return startOfDay(date)
  }
  return new Date(year, 1, 1)
}

const timePresets = [
  { key: 'today', label: '今天' },
  { key: 'yesterday', label: '昨天' },
  { key: 'thisWeek', label: '本周' },
  { key: 'lastWeek', label: '上周' },
  { key: 'thisMonth', label: '本月' },
  { key: 'lastMonth', label: '上月' },
  { key: 'springFestival', label: '春节' },
  { key: 'mayDay', label: '51节' },
]

function applyTimePreset(key: string) {
  const today = startOfDay()
  const year = today.getFullYear()
  let start = today
  let end = addDays(today, 1)

  if (key === 'yesterday') {
    start = addDays(today, -1)
    end = today
  } else if (key === 'thisWeek') {
    const offset = (today.getDay() + 6) % 7
    start = addDays(today, -offset)
    end = addDays(start, 7)
  } else if (key === 'lastWeek') {
    const offset = (today.getDay() + 6) % 7
    end = addDays(today, -offset)
    start = addDays(end, -7)
  } else if (key === 'thisMonth') {
    start = new Date(year, today.getMonth(), 1)
    end = new Date(year, today.getMonth() + 1, 1)
  } else if (key === 'lastMonth') {
    start = new Date(year, today.getMonth() - 1, 1)
    end = new Date(year, today.getMonth(), 1)
  } else if (key === 'springFestival') {
    const newYear = lunarNewYear(year)
    start = addDays(newYear, -1)
    end = addDays(newYear, 7)
  } else if (key === 'mayDay') {
    start = new Date(year, 4, 1)
    end = new Date(year, 4, 6)
  }

  range.value = [start.getTime(), end.getTime()]
  activeTimePreset.value = key
  result.value = null
}

function toTimestamp(value: string) {
  return new Date(value.replace(' ', 'T')).getTime()
}

function toLocalDateTime(timestamp: number) {
  const date = new Date(timestamp)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

async function loadOptions() {
  loadingOptions.value = true
  try {
    options.value = await getReportSearchOptions()
    range.value = [toTimestamp(options.value.default_start_time), toTimestamp(options.value.default_end_time)]
    activeTimePreset.value = 'yesterday'
  } catch (error) {
    message.error(error instanceof Error ? error.message : '搜索配置加载失败')
  } finally {
    loadingOptions.value = false
  }
}

async function loadCategories() {
  const response = await getReportSearchClassifications(source.value, 'category')
  categories.value = response.items
}

async function loadTypes() {
  const response = await getReportSearchClassifications(source.value, 'type')
  types.value = response.items
}

async function loadDetails() {
  const response = await getReportSearchClassifications(source.value, 'detail')
  details.value = response.items
}

async function loadAllClassifications() {
  loadingClassifications.value = true
  try {
    await Promise.all([loadCategories(), loadTypes(), loadDetails()])
  } finally {
    loadingClassifications.value = false
  }
}

async function runQuery() {
  if (!range.value) {
    message.warning('请选择时间范围')
    return
  }
  querying.value = true
  try {
    result.value = await executeReportSearch({
      source: source.value,
      start_time: toLocalDateTime(range.value[0]),
      end_time: toLocalDateTime(range.value[1]),
      category_codes: categoryCodes.value,
      type_codes: typeCodes.value,
      detail_codes: detailCodes.value,
      dimensions: [],
      measures: ['event_count'],
      limit: 100,
    })
  } catch (error) {
    message.error(error instanceof Error ? error.message : '查询失败')
  } finally {
    querying.value = false
  }
}

function escapeHtml(value: unknown) {
  return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function insertResult() {
  if (!result.value?.rows.length) return
  const headers = result.value.columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join('')
  const rows = result.value.rows.map((row) => `<tr>${result.value!.columns.map((column) => `<td>${escapeHtml(row[column.key])}</td>`).join('')}</tr>`).join('')
  const [start, end] = range.value || []
  const timeLabel = start && end ? `${toLocalDateTime(start).replace('T', ' ')} 至 ${toLocalDateTime(end).replace('T', ' ')}` : ''
  emit('insertHtml', `<h3>${escapeHtml(result.value.source.name)}统计结果</h3><p>统计时间：${escapeHtml(timeLabel)}；统计部门：${escapeHtml(result.value.department.name)}</p><table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table><p></p>`)
  message.success('查询结果已插入报告')
}

function resetSearch() {
  categoryCodes.value = []
  typeCodes.value = []
  detailCodes.value = []
  result.value = null
  range.value = options.value
    ? [toTimestamp(options.value.default_start_time), toTimestamp(options.value.default_end_time)]
    : defaultTimeRange()
  activeTimePreset.value = 'yesterday'
}

async function reloadClassificationOptions() {
  categoryCodes.value = []
  typeCodes.value = []
  detailCodes.value = []
  result.value = null
  await loadAllClassifications().catch(() => message.error('分类字典加载失败'))
}

watch(source, async () => {
  categoryCodes.value = []
  typeCodes.value = []
  detailCodes.value = []
  result.value = null
  await loadAllClassifications().catch(() => message.error('查询配置加载失败'))
})
watch([categoryCodes, typeCodes, detailCodes], () => { result.value = null })
onMounted(async () => {
  if (!userStore.user && userStore.token) {
    await userStore.loadCurrentUser().catch(() => undefined)
  }
  if (!departmentStore.departmentTree.length) {
    await departmentStore.loadDepartmentTree().catch(() => undefined)
  }
  await loadOptions()
  await loadAllClassifications().catch(() => message.error('分类字典加载失败'))
  window.addEventListener('statistics-dictionary-updated', reloadClassificationOptions)
})
onBeforeUnmount(() => window.removeEventListener('statistics-dictionary-updated', reloadClassificationOptions))
</script>

<template>
  <aside class="assistant-panel">
    <n-tabs v-model:value="activeTab" type="line" animated class="main-tabs">
      <n-tab-pane name="search">
        <template #tab><span class="tab-label"><n-icon :component="Search" />搜索</span></template>
        <n-spin :show="loadingOptions">
          <div class="panel-content">
            <section class="section-card">
              <div class="section-title">
                <span>全局参数</span>
                <n-button quaternary circle size="tiny" title="重置" @click="resetSearch">
                  <template #icon><n-icon :component="RefreshCw" /></template>
                </n-button>
              </div>
              <div class="field">
                <div class="field-label">时间范围</div>
                <n-date-picker v-model:value="range" type="datetimerange" clearable style="width: 100%" @update:value="activeTimePreset = ''" />
                <div class="time-presets">
                  <n-button
                    v-for="preset in timePresets"
                    :key="preset.key"
                    size="tiny"
                    :type="activeTimePreset === preset.key ? 'primary' : 'default'"
                    :secondary="activeTimePreset === preset.key"
                    @click="applyTimePreset(preset.key)"
                  >
                    {{ preset.label }}
                  </n-button>
                </div>
                <div class="field-hint">时间范围按起始时刻包含、结束时刻不包含统计</div>
              </div>
              <div class="field">
                <div class="field-label">当前账号部门</div>
                <div class="readonly-value">{{ currentDepartmentName }}</div>
                <div v-if="currentUnitCode" class="field-hint">{{ currentUnitCode }}</div>
              </div>
              <div class="field">
                <div class="field-label">数据源</div>
                <n-select v-model:value="source" :options="sourceOptions" />
                <div class="source-hint"><n-icon :component="Database" />仅查询当前数据库中的受控业务表</div>
              </div>
            </section>

            <section class="section-card">
              <div class="section-title"><span>分类筛选</span><n-tag size="small" :bordered="false">各层级独立</n-tag></div>
              <n-spin :show="loadingClassifications" size="small">
                <div class="classification-grid">
                  <div class="field">
                    <div class="field-label">类别</div>
                    <n-select v-model:value="categoryCodes" :options="categoryOptions" multiple clearable filterable max-tag-count="responsive" placeholder="全部类别" />
                  </div>
                  <div class="field">
                    <div class="field-label">类型</div>
                    <n-select v-model:value="typeCodes" :options="typeOptions" multiple clearable filterable virtual-scroll max-tag-count="responsive" placeholder="全部类型" />
                  </div>
                  <div class="field">
                    <div class="field-label">细类</div>
                    <n-select v-model:value="detailCodes" :options="detailOptions" multiple clearable filterable virtual-scroll max-tag-count="responsive" placeholder="全部细类" />
                  </div>
                </div>
              </n-spin>
              <n-button type="primary" block :loading="querying" @click="runQuery">
                <template #icon><n-icon :component="Search" /></template>
                执行查询
              </n-button>
            </section>

            <section class="result-card">
              <div class="section-title">
                <span>查询结果</span>
                <span v-if="result" class="result-meta">{{ result.row_count }} 行 · {{ result.elapsed_ms }} ms</span>
              </div>
              <n-alert v-if="result?.truncated" type="warning" :show-icon="false" class="result-alert">结果超过 100 行，仅展示前 100 行</n-alert>
              <div v-if="result?.rows.length" class="result-table">
                <n-data-table :columns="tableColumns" :data="result.rows" :pagination="false" size="small" :max-height="300" />
                <n-button secondary type="primary" block class="insert-button" @click="insertResult">
                  <template #icon><n-icon :component="FileInput" /></template>
                  插入报告
                </n-button>
              </div>
              <n-empty v-else description="设置参数并执行查询" size="small" class="result-empty" />
            </section>
          </div>
        </n-spin>
      </n-tab-pane>

      <n-tab-pane name="ai">
        <template #tab><span class="tab-label"><n-icon :component="Bot" />AI</span></template>
        <div class="panel-content">
          <section class="section-card ai-card">
            <h3>AI 报告助手</h3>
            <p>基于当前报告内容生成草稿。AI 结果仅作为草稿，需人工核验后使用。</p>
            <n-space vertical>
              <n-button type="primary" block @click="emit('generateDraft')">生成全文草稿</n-button>
              <n-button secondary block @click="emit('insertHtml', '<p>经综合研判，相关警情总体平稳，需持续关注重点区域和高发时段。</p>')">插入研判建议</n-button>
            </n-space>
          </section>
        </div>
      </n-tab-pane>
    </n-tabs>
  </aside>
</template>

<style scoped>
.assistant-panel { width: 360px; flex-shrink: 0; height: 100%; background: #f7f8fa; border-left: 1px solid #e5e7eb; display: flex; min-height: 0; }
.main-tabs { width: 100%; display: flex; flex-direction: column; min-height: 0; }
.main-tabs :deep(.n-tabs-nav) { flex-shrink: 0; padding: 0 16px; background: #fff; }
.main-tabs :deep(.n-tabs-tab) { width: 50%; justify-content: center; padding: 13px 0; font-weight: 600; }
.main-tabs :deep(.n-tabs-pane-wrapper), .main-tabs :deep(.n-tab-pane) { flex: 1; min-height: 0; }
.main-tabs :deep(.n-tab-pane) { height: 100%; overflow: auto; }
.tab-label { display: inline-flex; gap: 6px; align-items: center; }
.panel-content { padding: 12px; }
.section-card, .result-card { background: #fff; border: 1px solid #e8eaee; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.section-title { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; color: #262626; font-size: 14px; font-weight: 600; }
.field { margin-bottom: 13px; }
.field:last-child { margin-bottom: 0; }
.field-label { margin-bottom: 6px; font-size: 12px; color: #606266; font-weight: 500; }
.field-hint { margin-top: 4px; color: #a0a4aa; font-size: 11px; }
.time-presets { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 8px; }
.time-presets :deep(.n-button) { padding: 0 4px; }
.readonly-value { height: 34px; padding: 0 10px; display: flex; align-items: center; background: #f5f7fa; border: 1px solid #e4e7ed; border-radius: 4px; color: #303133; }
.source-hint { display: flex; align-items: center; gap: 4px; margin-top: 6px; color: #909399; font-size: 11px; }
.classification-grid { display: grid; grid-template-columns: 1fr; }
.classification-grid .field { margin-bottom: 10px; }
.section-divider { height: 1px; margin: 3px 0 12px; background: #eef0f3; }
.sub-title { margin-bottom: 10px; }
.metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px 6px; }
.result-meta { color: #909399; font-size: 11px; font-weight: 400; }
.result-alert { margin-bottom: 8px; font-size: 11px; }
.result-table { min-width: 0; }
.insert-button { margin-top: 10px; }
.result-empty { padding: 28px 0 34px; }
.ai-card h3 { margin: 0 0 8px; font-size: 15px; }
.ai-card p { margin: 0 0 14px; color: #7a7f87; font-size: 12px; line-height: 1.7; }
@media (max-width: 1200px) { .assistant-panel { width: 320px; } }
</style>
