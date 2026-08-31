<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  NButton,
  NDatePicker,
  NIcon,
  NSelect,
  NSpin,
  NTabPane,
  NTabs,
  useMessage,
} from 'naive-ui'
import { Bot, Database, RefreshCw, Search } from 'lucide-vue-next'
import ReportPiAssistant from '@/components/editor/ReportPiAssistant.vue'
import AtomicMetricPanel from '@/components/editor/atomic/AtomicMetricPanel.vue'
import { useDepartmentStore } from '@/stores/department'
import { useUserStore } from '@/stores/user'
import type { DepartmentItem } from '@/api/department'
import {
  getReportSearchClassifications,
  getReportSearchOptions,
  type SearchClassificationItem,
  type SearchOptions,
} from '@/api/reportSearch'

const props = withDefaults(defineProps<{ reportHtml?: string; readOnly?: boolean }>(), { readOnly: false })

const emit = defineEmits<{
  generateDraft: []
  insertHtml: [html: string]
  globalParametersChanged: [value: { start_time: string; end_time: string }]
}>()

const message = useMessage()
const userStore = useUserStore()
const departmentStore = useDepartmentStore()
const activeTab = ref<'search' | 'ai'>('search')
const loadingOptions = ref(false)
const options = ref<SearchOptions | null>(null)
const source = ref<'jjd_jjd' | 'fkd_fkd'>('jjd_jjd')
const range = ref<[number, number] | null>(defaultTimeRange())
const activeTimePreset = ref('yesterday')
const categories = ref<SearchClassificationItem[]>([])
const types = ref<SearchClassificationItem[]>([])
const details = ref<SearchClassificationItem[]>([])
const loadingClassifications = ref(false)
const settingsReady = ref(false)

interface CachedGlobalParameters {
  source: 'jjd_jjd' | 'fkd_fkd'
  range: [number, number]
  activeTimePreset: string
}

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

function globalParametersCacheKey() {
  const identity = userStore.user?.id || userStore.user?.username || 'anonymous'
  return `report_search_global_parameters:${identity}`
}

function readCachedGlobalParameters(): CachedGlobalParameters | null {
  try {
    const parsed = JSON.parse(localStorage.getItem(globalParametersCacheKey()) || 'null') as Partial<CachedGlobalParameters> | null
    if (!parsed || !['jjd_jjd', 'fkd_fkd'].includes(String(parsed.source))) return null
    if (!Array.isArray(parsed.range) || parsed.range.length !== 2 || !parsed.range.every(Number.isFinite)) return null
    if (parsed.range[1]! <= parsed.range[0]!) return null
    return {
      source: parsed.source as CachedGlobalParameters['source'],
      range: [parsed.range[0]!, parsed.range[1]!],
      activeTimePreset: typeof parsed.activeTimePreset === 'string' ? parsed.activeTimePreset : '',
    }
  } catch {
    localStorage.removeItem(globalParametersCacheKey())
    return null
  }
}

function persistGlobalParameters() {
  if (!settingsReady.value || !range.value || !options.value) return
  const defaultRange: [number, number] = [
    toTimestamp(options.value.default_start_time),
    toTimestamp(options.value.default_end_time),
  ]
  const isDefault = source.value === 'jjd_jjd'
    && activeTimePreset.value === 'yesterday'
    && range.value[0] === defaultRange[0]
    && range.value[1] === defaultRange[1]
  if (isDefault) {
    localStorage.removeItem(globalParametersCacheKey())
    return
  }
  localStorage.setItem(globalParametersCacheKey(), JSON.stringify({
    source: source.value,
    range: range.value,
    activeTimePreset: activeTimePreset.value,
  } satisfies CachedGlobalParameters))
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
    const cached = readCachedGlobalParameters()
    const enabledSources = new Set(options.value.data_sources.filter((item) => item.enabled).map((item) => item.key))
    if (cached && enabledSources.has(cached.source)) {
      source.value = cached.source
      range.value = cached.range
      activeTimePreset.value = cached.activeTimePreset
    } else {
      source.value = 'jjd_jjd'
      range.value = [toTimestamp(options.value.default_start_time), toTimestamp(options.value.default_end_time)]
      activeTimePreset.value = 'yesterday'
    }
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

function resetSearch() {
  localStorage.removeItem(globalParametersCacheKey())
  source.value = 'jjd_jjd'
  range.value = options.value
    ? [toTimestamp(options.value.default_start_time), toTimestamp(options.value.default_end_time)]
    : defaultTimeRange()
  activeTimePreset.value = 'yesterday'
  persistGlobalParameters()
}

async function reloadClassificationOptions() {
  await loadAllClassifications().catch(() => message.error('分类字典加载失败'))
}

watch(source, async () => {
  if (!settingsReady.value) return
  persistGlobalParameters()
  await loadAllClassifications().catch(() => message.error('查询配置加载失败'))
})
watch([range, activeTimePreset], () => {
  persistGlobalParameters()
  if (!settingsReady.value || !range.value) return
  emit('globalParametersChanged', {
    start_time: toLocalDateTime(range.value[0]),
    end_time: toLocalDateTime(range.value[1]),
  })
}, { deep: true })
onMounted(async () => {
  if (!userStore.user && userStore.token) {
    await userStore.loadCurrentUser().catch(() => undefined)
  }
  if (!departmentStore.departmentTree.length) {
    await departmentStore.loadDepartmentTree().catch(() => undefined)
  }
  await loadOptions()
  settingsReady.value = true
  if (range.value) {
    emit('globalParametersChanged', {
      start_time: toLocalDateTime(range.value[0]),
      end_time: toLocalDateTime(range.value[1]),
    })
  }
  await loadAllClassifications().catch(() => message.error('分类字典加载失败'))
  window.addEventListener('statistics-dictionary-updated', reloadClassificationOptions)
})
onBeforeUnmount(() => window.removeEventListener('statistics-dictionary-updated', reloadClassificationOptions))
</script>

<template>
  <aside class="assistant-panel">
    <n-tabs v-model:value="activeTab" type="card" animated class="main-tabs">
      <n-tab-pane name="search">
        <template #tab><span class="tab-label"><n-icon :component="Search" />原子指标</span></template>
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
              <div class="field-row">
                <div class="field">
                  <div class="field-label">当前账号部门</div>
                  <div class="readonly-value">{{ currentDepartmentName }}</div>
                  <div v-if="currentUnitCode" class="field-hint">{{ currentUnitCode }}</div>
                </div>
                <div class="field">
                  <div class="field-label">数据源</div>
                  <n-select v-model:value="source" :options="sourceOptions" />
                  <div class="source-hint"><n-icon :component="Database" />仅查受控业务表</div>
                </div>
              </div>
            </section>

            <AtomicMetricPanel
              v-if="!props.readOnly"
              :category-options="categoryOptions"
              :type-options="typeOptions"
              :detail-options="detailOptions"
              :source="source"
              :range="range"
              :dept-code="currentUnitCode"
              :dept-name="currentDepartmentName"
              :loading-classifications="loadingClassifications"
            />
            <div v-else class="read-only-tip">归档报告为只读，指标查询、拖拽插入和动态刷新已停用。</div>
          </div>
        </n-spin>
      </n-tab-pane>

      <n-tab-pane name="ai" class="ai-pane">
        <template #tab><span class="tab-label"><n-icon :component="Bot" />AI</span></template>
        <ReportPiAssistant v-if="!props.readOnly" :report-html="props.reportHtml" @generate-draft="emit('generateDraft')" @insert-html="emit('insertHtml', $event)" />
        <div v-else class="read-only-tip">归档报告为只读，AI 生成与内容插入已停用。</div>
      </n-tab-pane>
    </n-tabs>
  </aside>
</template>

<style scoped>
.assistant-panel { width: 360px; flex-shrink: 0; height: 100%; background: #f7f8fa; border-left: 1px solid #e5e7eb; display: flex; min-height: 0; }
.main-tabs { width: 100%; display: flex; flex-direction: column; min-height: 0; }
.main-tabs :deep(.n-tabs-nav) { flex-shrink: 0; padding: 8px 12px 0; background: #fff; }
.main-tabs :deep(.n-tabs-nav-scroll-wrapper),
.main-tabs :deep(.n-tabs-nav-scroll-content) { width: 100%; }
.main-tabs :deep(.n-tabs-wrapper) { display: flex; width: 100%; }
.main-tabs :deep(.n-tabs-tab-pad) { width: 0; }
.main-tabs :deep(.n-tabs-tab-wrapper) { flex: 1 1 50%; min-width: 0; display: flex; }
.main-tabs :deep(.n-tabs-tab) { flex: 1; width: 100%; display: flex; justify-content: center; align-items: center; padding: 9px 16px; font-weight: 600; }
.main-tabs :deep(.n-tabs-tab__label) { display: flex; justify-content: center; width: 100%; }
.main-tabs :deep(.n-tabs-pane-wrapper), .main-tabs :deep(.n-tab-pane) { flex: 1; min-height: 0; }
.main-tabs :deep(.n-tab-pane) { height: 100%; overflow: auto; }
.main-tabs :deep(.ai-pane) { overflow: hidden; }
.tab-label { display: inline-flex; gap: 6px; align-items: center; justify-content: center; }
.panel-content { padding: 12px; }
.section-card, .result-card { background: #fff; border: 1px solid #e8eaee; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.section-title { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; color: #262626; font-size: 14px; font-weight: 600; }
.field { margin-bottom: 13px; }
.field:last-child { margin-bottom: 0; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 13px; }
.field-row > .field { margin-bottom: 0; min-width: 0; }
.field-label { margin-bottom: 6px; font-size: 12px; color: #606266; font-weight: 500; }
.field-hint { margin-top: 4px; color: #a0a4aa; font-size: 11px; }
.time-presets { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 8px; }
.time-presets :deep(.n-button) { padding: 0 4px; }
.readonly-value { height: 34px; padding: 0 10px; display: flex; align-items: center; background: #f5f7fa; border: 1px solid #e4e7ed; border-radius: 4px; color: #303133; }
.source-hint { display: flex; align-items: center; gap: 4px; margin-top: 6px; color: #909399; font-size: 11px; white-space: nowrap; }
.classification-grid { display: grid; grid-template-columns: 1fr; }
.classification-grid .field { margin-bottom: 10px; }
.classification-grid .field-row { margin-bottom: 0; }
.classification-grid .field-row > .field { margin-bottom: 0; }
.section-divider { height: 1px; margin: 3px 0 12px; background: #eef0f3; }
.metric-options { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px 4px; }
.metric-options :deep(.n-checkbox__label) { padding-left: 5px; font-size: 12px; }
.result-meta { color: #909399; font-size: 11px; font-weight: 400; }
.result-alert { margin-bottom: 8px; font-size: 11px; }
.summary-mode-alert { margin-bottom: 12px; font-size: 11px; }
.jurisdiction-options { margin-top: 12px; padding: 10px; border-radius: 6px; background: #f5faff; }
.direction-field { margin-top: 12px; }
.result-output { min-width: 0; }
.result-blocks { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.result-blocks--stack { grid-template-columns: 1fr; }
.result-block {
  position: relative;
  min-width: 0;
  border: 1px solid #d9e9fb;
  border-radius: 8px;
  background: #f5faff;
  cursor: grab;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.result-block:active { cursor: grabbing; }
.result-block:hover { border-color: #91caff; box-shadow: 0 1px 4px rgba(24, 144, 255, 0.12); }
.result-block--wide { grid-column: 1 / -1; }
.result-block--metric { padding: 14px 10px 10px; text-align: center; }
.result-drag-hint { margin-top: 10px; text-align: center; }
.sql-link { margin-top: 6px; }
.jurisdiction-summary-result { position: relative; padding: 12px; }
.jurisdiction-summary-result > p { margin: 0 46px 10px 0; color: #303133; font-size: 12px; line-height: 1.75; }
.jurisdiction-summary-result > .sql-button { position: absolute; right: 9px; top: 9px; }
.jurisdiction-summary-list { max-height: 240px; overflow: auto; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 5px 10px; }
.jurisdiction-summary-row { min-width: 0; display: flex; justify-content: space-between; gap: 6px; padding: 5px 6px; background: rgba(255,255,255,.8); border-radius: 4px; font-size: 11px; }
.jurisdiction-summary-row span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.jurisdiction-summary-row strong { flex-shrink: 0; font-variant-numeric: tabular-nums; cursor: grab; }
.jurisdiction-summary-row strong:active { cursor: grabbing; }
.total-statistic { min-width: 0; text-align: center; }
.total-statistic :deep(.n-statistic-value) { color: #1890ff; font-size: 22px; font-weight: 700; }
.count-item { min-width: 0; padding: 9px 10px; }
.count-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.count-info { min-width: 0; display: flex; align-items: center; gap: 7px; }
.count-level { flex-shrink: 0; padding: 2px 5px; color: #1677d2; background: #eaf4ff; border-radius: 4px; font-size: 10px; }
.count-name { overflow: hidden; color: #303133; font-size: 12px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.classification-metrics { margin-top: 9px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; }
.metric-cell { min-width: 0; padding: 6px 7px; display: flex; align-items: center; justify-content: space-between; gap: 5px; background: #fff; border-radius: 4px; font-size: 11px; cursor: grab; }
.metric-cell:active { cursor: grabbing; }
.metric-cell span { overflow: hidden; color: #909399; text-overflow: ellipsis; white-space: nowrap; }
.metric-cell strong { flex-shrink: 0; color: #1890ff; font-size: 14px; font-variant-numeric: tabular-nums; }
.metric-up, .metric-up :deep(.n-statistic-value) { color: #d03050 !important; }
.metric-down, .metric-down :deep(.n-statistic-value) { color: #18a058 !important; }
.sql-button { font-family: Consolas, monospace; }
.sql-code { max-height: 60vh; margin: 0; padding: 14px; overflow: auto; color: #d4d4d4; background: #1e1e1e; border-radius: 6px; font-family: Consolas, 'Courier New', monospace; font-size: 12px; line-height: 1.65; white-space: pre-wrap; overflow-wrap: anywhere; }
.result-empty { padding: 28px 0 34px; }
@media (max-width: 1200px) { .assistant-panel { width: 320px; } }
</style>
