<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NDatePicker,
  NEmpty,
  NIcon,
  NModal,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSpace,
  NSpin,
  NStatistic,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
} from 'naive-ui'
import { Bot, Code2, Database, FileInput, RefreshCw, Search } from 'lucide-vue-next'
import ReportPiAssistant from '@/components/editor/ReportPiAssistant.vue'
import { useDepartmentStore } from '@/stores/department'
import { useUserStore } from '@/stores/user'
import type { DepartmentItem } from '@/api/department'
import {
  executeReportSearch,
  getReportSearchClassifications,
  getReportSearchOptions,
  type ReportQueryBlock,
  type ReportQueryBlockMode,
  type JurisdictionMetric,
  type SearchClassificationItem,
  type SummaryDirection,
  type SearchOptions,
  type SearchQuery,
  type SearchResult,
} from '@/api/reportSearch'

const props = defineProps<{ reportHtml?: string }>()

const emit = defineEmits<{
  generateDraft: []
  insertHtml: [html: string]
  insertQueryBlock: [block: ReportQueryBlock]
  globalParametersChanged: [value: { start_time: string; end_time: string }]
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
const selectedMeasures = ref<string[]>(['event_count'])
const analysisType = ref<'standard' | 'jurisdiction'>('standard')
const jurisdictionMetric = ref<JurisdictionMetric>('year_on_year')
const summaryDirection = ref<SummaryDirection>('auto')
const insertionMode = ref<ReportQueryBlockMode>('snapshot')
const categories = ref<SearchClassificationItem[]>([])
const types = ref<SearchClassificationItem[]>([])
const details = ref<SearchClassificationItem[]>([])
const loadingClassifications = ref(false)
const result = ref<SearchResult | null>(null)
const showSql = ref(false)
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

const jurisdictionScopeLabel = computed(() => currentUnitCode.value === '330782000000' ? '派出所' : '管辖社区')
const sourceOptions = computed(() =>
  (options.value?.data_sources || [{ key: 'jjd_jjd', name: '接警单', enabled: true }]).map((item) => ({ label: item.name, value: item.key, disabled: !item.enabled })),
)
const categoryOptions = computed(() => categories.value.map((item) => ({ label: item.name, value: item.code })))
const typeOptions = computed(() => types.value.map((item) => ({ label: item.name, value: item.code })))
const detailOptions = computed(() => details.value.map((item) => ({ label: item.name, value: item.code })))
const hasClassificationSelection = computed(() => Boolean(categoryCodes.value.length || typeCodes.value.length || detailCodes.value.length))
const metricOptions = [
  { value: 'event_count', label: '警情数量' },
  { value: 'year_on_year_rate', label: '同比' },
  { value: 'period_on_period_rate', label: '环比' },
  { value: 'proportion', label: '占比' },
  { value: 'year_on_year_change', label: '同比数' },
  { value: 'period_on_period_change', label: '环比数' },
]
const totalMetrics = computed(() => {
  if (result.value?.rows.length !== 1 || 'classification_level' in result.value.rows[0]) return []
  return result.value.columns.map((column) => ({ key: column.key, label: column.label, value: result.value!.rows[0][column.key] }))
})
const classificationCounts = computed(() =>
  (result.value?.rows || []).filter((row) => 'classification_level' in row).map((row) => ({
    level: String(row.classification_level || ''),
    name: String(row.classification_name || row.classification_code || ''),
    code: String(row.classification_code || ''),
    metrics: result.value!.columns
      .filter((column) => !['classification_level', 'classification_name', 'classification_code'].includes(column.key))
      .map((column) => ({ key: column.key, label: column.label, value: row[column.key] })),
  })),
)

function formatMetric(key: string, value: unknown) {
  if (value === null || value === undefined) return '—'
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'
  if (['year_on_year_rate', 'period_on_period_rate', 'proportion'].includes(key)) return `${number > 0 && key !== 'proportion' ? '+' : ''}${number.toFixed(2)}%`
  return `${number > 0 && ['year_on_year_change', 'period_on_period_change'].includes(key) ? '+' : ''}${number.toLocaleString('zh-CN')}`
}

function metricClass(key: string, value: unknown) {
  if (!['year_on_year_rate', 'period_on_period_rate', 'year_on_year_change', 'period_on_period_change'].includes(key)) return ''
  const number = Number(value)
  return number > 0 ? 'metric-up' : number < 0 ? 'metric-down' : ''
}

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

async function runQuery() {
  if (!range.value) {
    message.warning('请选择时间范围')
    return
  }
  if (!selectedMeasures.value.length) {
    message.warning('请至少选择一个统计指标')
    return
  }
  querying.value = true
  try {
    result.value = await executeReportSearch({
      source: analysisType.value === 'jurisdiction' ? 'fkd_fkd' : source.value,
      analysis_type: analysisType.value,
      jurisdiction_metric: jurisdictionMetric.value,
      summary_direction: summaryDirection.value,
      start_time: toLocalDateTime(range.value[0]),
      end_time: toLocalDateTime(range.value[1]),
      category_codes: categoryCodes.value,
      type_codes: typeCodes.value,
      detail_codes: detailCodes.value,
      dimensions: [],
      measures: analysisType.value === 'jurisdiction'
        ? ['event_count']
        : selectedMeasures.value,
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

function currentBlockQuery(): ReportQueryBlock['query'] {
  return {
    source: analysisType.value === 'jurisdiction' ? 'fkd_fkd' : source.value,
    analysis_type: analysisType.value,
    jurisdiction_metric: jurisdictionMetric.value,
    summary_direction: summaryDirection.value,
    category_codes: [...categoryCodes.value],
    type_codes: [...typeCodes.value],
    detail_codes: [...detailCodes.value],
    dimensions: [],
    measures: analysisType.value === 'jurisdiction'
      ? ['event_count']
      : [...selectedMeasures.value],
    limit: 100,
  }
}

function createQueryBlock(): ReportQueryBlock | null {
  if (!result.value?.rows.length) return null
  return {
    id: crypto.randomUUID(),
    mode: insertionMode.value,
    query: currentBlockQuery(),
    title: result.value.analysis_type === 'jurisdiction'
      ? `${result.value.scope_label || '辖区'}${jurisdictionMetric.value === 'year_on_year' ? '同比' : jurisdictionMetric.value === 'period_on_period' ? '环比' : '占比'}综述`
      : `${result.value.source.name}统计结果`,
    result: result.value,
    last_updated_at: new Date().toISOString(),
  }
}

function insertResult() {
  const block = createQueryBlock()
  if (!block) return
  emit('insertQueryBlock', block)
  message.success(block.mode === 'dynamic' ? '动态数据块已插入报告' : '查询结果已插入报告')
}

function handleResultDragStart(event: DragEvent) {
  const block = createQueryBlock()
  if (!block || !event.dataTransfer) return
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/vnd.yw-report-query-block+json', JSON.stringify(block))
  event.dataTransfer.setData('text/plain', block.title)
}

function resetSearch() {
  localStorage.removeItem(globalParametersCacheKey())
  source.value = 'jjd_jjd'
  analysisType.value = 'standard'
  jurisdictionMetric.value = 'year_on_year'
  summaryDirection.value = 'auto'
  categoryCodes.value = []
  selectedMeasures.value = ['event_count']
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
  if (!settingsReady.value) return
  categoryCodes.value = []
  typeCodes.value = []
  detailCodes.value = []
  result.value = null
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
watch([categoryCodes, typeCodes, detailCodes], () => {
  if (!hasClassificationSelection.value) {
    selectedMeasures.value = selectedMeasures.value.filter((key) => key !== 'proportion')
  }
  result.value = null
})
watch(selectedMeasures, () => { result.value = null })
watch(analysisType, (value) => {
  result.value = null
  if (value === 'jurisdiction') source.value = 'fkd_fkd'
})
watch(jurisdictionMetric, () => { result.value = null })
watch(summaryDirection, () => { result.value = null })
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
              <div class="field">
                <div class="field-label">统计方式</div>
                <n-radio-group v-model:value="analysisType" size="small">
                  <n-radio-button value="standard">普通统计</n-radio-button>
                  <n-radio-button value="jurisdiction">辖区分析</n-radio-button>
                </n-radio-group>
                <div v-if="analysisType === 'jurisdiction'" class="jurisdiction-options">
                  <div class="field-label">分析指标</div>
                  <n-radio-group v-model:value="jurisdictionMetric" size="small">
                    <n-radio-button value="year_on_year">同比</n-radio-button>
                    <n-radio-button value="period_on_period">环比</n-radio-button>
                    <n-radio-button value="proportion">占比</n-radio-button>
                  </n-radio-group>
                  <div v-if="jurisdictionMetric !== 'proportion'" class="direction-field">
                    <div class="field-label">综述方向</div>
                    <n-select
                      v-model:value="summaryDirection"
                      :options="[
                        { label: '自动', value: 'auto' },
                        { label: '升幅', value: 'increase' },
                        { label: '降幅', value: 'decrease' },
                      ]"
                    />
                  </div>
                  <div class="field-hint">根据当前账号自动按{{ jurisdictionScopeLabel }}统计并生成综述</div>
                </div>
              </div>
              <div class="section-divider"></div>
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
              <div class="section-divider"></div>
              <div v-if="analysisType === 'standard'" class="field">
                <div class="field-label">统计指标</div>
                <n-checkbox-group v-model:value="selectedMeasures">
                  <div class="metric-options">
                    <n-checkbox
                      v-for="item in metricOptions"
                      :key="item.value"
                      :value="item.value"
                      :label="item.label"
                      :disabled="item.value === 'proportion' && !hasClassificationSelection"
                    />
                  </div>
                </n-checkbox-group>
              </div>
              <n-alert v-else type="info" :show-icon="false" class="summary-mode-alert">
                数据源固定为反馈单，自动计算所选指标，统计层级为{{ jurisdictionScopeLabel }}。
              </n-alert>
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
              <div
                v-if="result?.rows.length"
                class="result-output"
                draggable="true"
                title="可将查询结果拖入编辑器"
                @dragstart="handleResultDragStart"
              >
                <div v-if="result?.analysis_type === 'jurisdiction' || result?.analysis_type === 'jurisdiction_yoy_summary'" class="jurisdiction-summary-result">
                  <p>{{ result.summary }}</p>
                  <div class="jurisdiction-summary-list">
                    <div v-for="row in result.rows" :key="String(row.scope_code)" class="jurisdiction-summary-row">
                      <span :title="String(row.scope_name)">{{ row.scope_name }}</span>
                      <strong :class="metricClass(
                        result.jurisdiction_metric === 'period_on_period' ? 'period_on_period_rate' : 'year_on_year_rate',
                        result.jurisdiction_metric === 'proportion' ? row.proportion : result.jurisdiction_metric === 'period_on_period' ? row.period_on_period_rate : row.year_on_year_rate,
                      )">
                        {{ formatMetric(
                          result.jurisdiction_metric === 'proportion' ? 'proportion' : result.jurisdiction_metric === 'period_on_period' ? 'period_on_period_rate' : 'year_on_year_rate',
                          result.jurisdiction_metric === 'proportion' ? row.proportion : result.jurisdiction_metric === 'period_on_period' ? row.period_on_period_rate : row.year_on_year_rate,
                        ) }}
                      </strong>
                    </div>
                  </div>
                  <n-button size="tiny" secondary class="sql-button" @click="showSql = true">
                    <template #icon><n-icon :component="Code2" /></template>
                    SQL
                  </n-button>
                </div>
                <div v-else-if="totalMetrics.length" class="total-statistic-wrap">
                  <div class="total-metrics">
                    <n-statistic
                      v-for="metric in totalMetrics"
                      :key="metric.key"
                      :label="metric.label"
                      :value="formatMetric(metric.key, metric.value)"
                      :class="['total-statistic', metricClass(metric.key, metric.value)]"
                    />
                  </div>
                  <n-button size="tiny" secondary class="sql-button" @click="showSql = true">
                    <template #icon><n-icon :component="Code2" /></template>
                    SQL
                  </n-button>
                </div>
                <div v-else class="count-list">
                  <div v-for="item in classificationCounts" :key="`${item.level}-${item.code}`" class="count-item classification-result">
                    <div class="count-header">
                      <div class="count-info">
                        <span class="count-level">{{ item.level }}</span>
                        <span class="count-name" :title="item.name">{{ item.name }}</span>
                      </div>
                      <n-button size="tiny" secondary class="sql-button" @click="showSql = true">
                        <template #icon><n-icon :component="Code2" /></template>
                        SQL
                      </n-button>
                    </div>
                    <div class="classification-metrics">
                      <div v-for="metric in item.metrics" :key="metric.key" class="metric-cell">
                        <span>{{ metric.label }}</span>
                        <strong :class="metricClass(metric.key, metric.value)">{{ formatMetric(metric.key, metric.value) }}</strong>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="insert-controls">
                  <n-radio-group v-model:value="insertionMode" size="small">
                    <n-radio-button value="snapshot">正常内容</n-radio-button>
                    <n-radio-button value="dynamic">模板占位</n-radio-button>
                  </n-radio-group>
                  <div class="field-hint">可拖动整个结果区域到编辑器指定位置</div>
                </div>
                <n-button secondary type="primary" block class="insert-button" @click="insertResult">
                  <template #icon><n-icon :component="FileInput" /></template>
                  {{ insertionMode === 'dynamic' ? '插入动态数据块' : '插入查询结果' }}
                </n-button>
              </div>
              <n-empty v-else :description="result ? '当前条件统计数量为 0' : '设置参数并执行查询'" size="small" class="result-empty" />
            </section>
          </div>
        </n-spin>
      </n-tab-pane>

      <n-tab-pane name="ai" class="ai-pane">
        <template #tab><span class="tab-label"><n-icon :component="Bot" />AI</span></template>
        <ReportPiAssistant :report-html="props.reportHtml" @generate-draft="emit('generateDraft')" @insert-html="emit('insertHtml', $event)" />
      </n-tab-pane>
    </n-tabs>
    <n-modal
      v-model:show="showSql"
      preset="card"
      title="本次查询 SQL"
      :bordered="false"
      style="width: 680px; max-width: calc(100vw - 32px)"
    >
      <pre class="sql-code"><code>{{ result?.executed_sql }}</code></pre>
    </n-modal>
  </aside>
</template>

<style scoped>
.assistant-panel { width: 360px; flex-shrink: 0; height: 100%; background: #f7f8fa; border-left: 1px solid #e5e7eb; display: flex; min-height: 0; }
.main-tabs { width: 100%; display: flex; flex-direction: column; min-height: 0; }
.main-tabs :deep(.n-tabs-nav) { flex-shrink: 0; padding: 8px 12px 0; background: #fff; }
.main-tabs :deep(.n-tabs-nav-scroll-wrapper),
.main-tabs :deep(.n-tabs-nav-scroll-content) { width: 100%; }
.main-tabs :deep(.n-tabs-nav-scroll-content) { display: flex; }
.main-tabs :deep(.n-tabs-tab) { flex: 1 1 50%; justify-content: center; padding: 9px 16px; font-weight: 600; }
.main-tabs :deep(.n-tabs-pane-wrapper), .main-tabs :deep(.n-tab-pane) { flex: 1; min-height: 0; }
.main-tabs :deep(.n-tab-pane) { height: 100%; overflow: auto; }
.main-tabs :deep(.ai-pane) { overflow: hidden; }
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
.metric-options { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px 4px; }
.metric-options :deep(.n-checkbox__label) { padding-left: 5px; font-size: 12px; }
.result-meta { color: #909399; font-size: 11px; font-weight: 400; }
.result-alert { margin-bottom: 8px; font-size: 11px; }
.summary-mode-alert { margin-bottom: 12px; font-size: 11px; }
.jurisdiction-options { margin-top: 12px; padding: 10px; border-radius: 6px; background: #f5faff; }
.direction-field { margin-top: 12px; }
.result-output { min-width: 0; cursor: grab; }
.result-output:active { cursor: grabbing; }
.insert-controls { margin-top: 10px; display: flex; flex-direction: column; align-items: center; gap: 2px; }
.jurisdiction-summary-result { position: relative; padding: 12px; border: 1px solid #d9e9fb; border-radius: 8px; background: #f5faff; }
.jurisdiction-summary-result > p { margin: 0 46px 10px 0; color: #303133; font-size: 12px; line-height: 1.75; }
.jurisdiction-summary-result > .sql-button { position: absolute; right: 9px; top: 9px; }
.jurisdiction-summary-list { max-height: 240px; overflow: auto; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 5px 10px; }
.jurisdiction-summary-row { min-width: 0; display: flex; justify-content: space-between; gap: 6px; padding: 5px 6px; background: rgba(255,255,255,.8); border-radius: 4px; font-size: 11px; }
.jurisdiction-summary-row span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.jurisdiction-summary-row strong { flex-shrink: 0; font-variant-numeric: tabular-nums; }
.total-statistic-wrap { position: relative; padding: 14px 54px 14px 12px; border: 1px solid #d9e9fb; border-radius: 8px; background: #f5faff; }
.total-metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 8px; }
.total-statistic { min-width: 0; text-align: center; }
.total-statistic :deep(.n-statistic-value) { color: #1890ff; font-size: 24px; font-weight: 700; }
.total-statistic-wrap > .sql-button { position: absolute; right: 9px; top: 9px; }
.count-list { max-height: 360px; overflow: auto; display: flex; flex-direction: column; gap: 7px; }
.count-item { min-width: 0; padding: 9px 10px; border: 1px solid #e8eaee; border-radius: 6px; background: #fafbfc; }
.count-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.count-info { min-width: 0; display: flex; align-items: center; gap: 7px; }
.count-level { flex-shrink: 0; padding: 2px 5px; color: #1677d2; background: #eaf4ff; border-radius: 4px; font-size: 10px; }
.count-name { overflow: hidden; color: #303133; font-size: 12px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.classification-metrics { margin-top: 9px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; }
.metric-cell { min-width: 0; padding: 6px 7px; display: flex; align-items: center; justify-content: space-between; gap: 5px; background: #fff; border-radius: 4px; font-size: 11px; }
.metric-cell span { overflow: hidden; color: #909399; text-overflow: ellipsis; white-space: nowrap; }
.metric-cell strong { flex-shrink: 0; color: #1890ff; font-size: 14px; font-variant-numeric: tabular-nums; }
.metric-up, .metric-up :deep(.n-statistic-value) { color: #d03050 !important; }
.metric-down, .metric-down :deep(.n-statistic-value) { color: #18a058 !important; }
.sql-button { font-family: Consolas, monospace; }
.sql-code { max-height: 60vh; margin: 0; padding: 14px; overflow: auto; color: #d4d4d4; background: #1e1e1e; border-radius: 6px; font-family: Consolas, 'Courier New', monospace; font-size: 12px; line-height: 1.65; white-space: pre-wrap; overflow-wrap: anywhere; }
.insert-button { margin-top: 10px; }
.result-empty { padding: 28px 0 34px; }
@media (max-width: 1200px) { .assistant-panel { width: 320px; } }
</style>
