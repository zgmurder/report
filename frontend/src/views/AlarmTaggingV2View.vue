<script setup lang="ts">
import {
  enrichStatusLabel,
  getTagV2AlarmDetail,
  groupTagsByDomain,
  listTagV2Catalog,
  personDisplayName,
  personExtractTags,
  personRoleLabel,
  personTagLeaf,
  personZjTags,
  searchTagV2Alarms,
  statsTagV2Alarms,
  verifyTagV2Alarm,
  type TagV2AlarmRow,
  type TagV2DictItem,
  type TagV2PersonItem,
  type TagV2StatsItem,
  type TagV2StatsLevel
} from '@/api/tagV2'
import { getFeedbackCategoryTree, type FeedbackCategoryNode } from '@/api/feedbackCategory'
import { isCityBureauDept, useAuthStore } from '@/stores/auth'
import {
  buildDeptTreeOptions,
  collectDeptScopeIds,
  collectExpandedKeys,
  type DeptOption,
} from '@/utils/deptTree'
import { maskCjqkText, maskIdNo, maskPersonName, maskPhone } from '@/utils/privacyMask'
import {
  formatDateTime,
  persistDateRangeShortcut,
  readReportDateRange,
  syncTimeToReportCache,
  type DateRangeShortcutKey
} from '@/utils/reportDateRange'
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  LayoutGrid,
  RotateCcw,
  Search,
  Tags
} from 'lucide-vue-next'
import {
  NButton,
  NDataTable,
  NDatePicker,
  NIcon,
  NInput,
  NModal,
  NSelect,
  NSpin,
  NTag,
  NTooltip,
  NTreeSelect,
  useMessage,
  type DataTableColumns,
  type SelectOption
} from 'naive-ui'
import type { TreeOption } from 'naive-ui'
import { computed, h, onMounted, reactive, ref, watch } from 'vue'

const message = useMessage()
const authStore = useAuthStore()

const loading = ref(false)
const loadingStats = ref(false)
const loadingCatalog = ref(false)
const loadingDepts = ref(false)
const loadingFeedbackTree = ref(false)
const savingVerify = ref(false)
const hasSearched = ref(false)
const verifyingRowId = ref('')
const searchExpanded = ref(true)
const detailVisible = ref(false)

const rows = ref<TagV2AlarmRow[]>([])
const selectedId = ref('')
const pageNum = ref(1)
const pageSize = ref(20)
const pageTotal = ref(0)

const catalogTags = ref<TagV2DictItem[]>([])
const domains = ref<string[]>([])
const deptRows = ref<DeptOption[]>([])
const selectedDeptKey = ref<string | null>(null)
const expandedDeptKeys = ref<string[]>([])
const selectedDateRangeShortcut = ref<DateRangeShortcutKey | ''>('')
const draftTagPaths = ref<string[]>([])
const feedbackCategoryOptions = ref<SelectOption[]>([])
const feedbackTypeOptions = ref<SelectOption[]>([])
const feedbackSubtypeOptions = ref<SelectOption[]>([])
const selectedAjlbCodes = ref<string[]>([])
const selectedAjlxCodes = ref<string[]>([])
const selectedAjxlCodes = ref<string[]>([])

const statsLevel = ref<TagV2StatsLevel>('1')
const statsItems = ref<TagV2StatsItem[]>([])
/** 组合标签全路径统计，供左侧「全局搜索」使用（与当前级数无关） */
const globalStatsItems = ref<TagV2StatsItem[]>([])
const statsTotalAlarms = ref(0)
const activeStatPrefix = ref('')
const statsKeyword = ref('')

const filters = reactive({
  fkdbh: '',
  cjdbh: '',
  fkdwmc: '',
  fkdwdm: '',
  fkrxm: '',
  keyword: '',
  beginTime: '',
  endTime: '',
  domain: null as string | null,
  includeTags: [] as string[],
  verifyStatus: 'all' as 'all' | 'manual' | 'auto'
})

const statsLevelOptions: Array<{ label: string; value: TagV2StatsLevel }> = [
  { label: '一级', value: '1' },
  { label: '二级', value: '2' },
  { label: '三级', value: '3' },
  { label: '四级', value: '4' }
]

function setTimeRange(
  start: string,
  end: string,
  shortcut: DateRangeShortcutKey | '' = '',
  persist = true
) {
  filters.beginTime = start
  filters.endTime = end
  selectedDateRangeShortcut.value = shortcut
  if (persist) {
    persistDateRangeShortcut(shortcut)
    syncTimeToReportCache(start, end)
  }
}

function applyTimeFromReportCache() {
  const range = readReportDateRange()
  if (range.beginTime && range.endTime) {
    setTimeRange(range.beginTime, range.endTime, range.shortcut)
  }
}

function parseDateMs(value?: string | null) {
  if (!value) return null
  const ms = Date.parse(String(value).replace(' ', 'T'))
  return Number.isNaN(ms) ? null : ms
}

function rangesOverlap(beginA: string, endA: string, beginB?: string | null, endB?: string | null) {
  const a0 = parseDateMs(beginA)
  const a1 = parseDateMs(endA)
  const b0 = parseDateMs(beginB)
  const b1 = parseDateMs(endB)
  if (a0 == null || a1 == null || b0 == null || b1 == null) return false
  return a0 < b1 && b0 < a1
}

function coverTaggedDayRange(minTime?: string | null, maxTime?: string | null): [string, string] | null {
  const minMs = parseDateMs(minTime)
  const maxMs = parseDateMs(maxTime)
  if (minMs == null || maxMs == null) return null
  const start = new Date(minMs)
  start.setHours(0, 0, 0, 0)
  const end = new Date(maxMs)
  end.setHours(0, 0, 0, 0)
  end.setDate(end.getDate() + 1)
  return [formatDateTime(start.getTime()), formatDateTime(end.getTime())]
}

const alarmTimeRange = computed<[string, string] | null>({
  get() {
    if (!filters.beginTime || !filters.endTime) return null
    return [filters.beginTime, filters.endTime]
  },
  set(value) {
    setTimeRange(value?.[0] || '', value?.[1] || '', '')
  }
})

applyTimeFromReportCache()

const scopedDeptRows = computed(() => {
  const accountDeptId = Number(authStore.deptId || 0)
  if (!accountDeptId) return deptRows.value
  const scopeIds = collectDeptScopeIds(deptRows.value, accountDeptId)
  if (!scopeIds) return deptRows.value
  return deptRows.value.filter((dept) => scopeIds.has(Number(dept.deptId || 0)))
})

const deptTreeOptions = computed<TreeOption[]>(() => buildDeptTreeOptions(scopedDeptRows.value))
const pageCount = computed(() => Math.max(1, Math.ceil(pageTotal.value / pageSize.value)))
const pageStart = computed(() => (pageTotal.value ? (pageNum.value - 1) * pageSize.value + 1 : 0))
const pageEnd = computed(() => Math.min(pageNum.value * pageSize.value, pageTotal.value))

const selectedRow = computed(() => rows.value.find((item) => rowKey(item) === selectedId.value) || null)

const domainOptions = computed(() => domains.value.map((item) => ({ label: item, value: item })))

const verifyStatusOptions = [
  { label: '全部', value: 'all' },
  { label: '含人工标签', value: 'manual' },
  { label: '仅自动标签', value: 'auto' }
]

const tagOptions = computed(() => {
  const domain = String(filters.domain || '').trim()
  return catalogTags.value
    .filter((tag) => !domain || tag.domain === domain)
    .map((tag) => ({
      label: tag.tagPath,
      value: tag.tagPath
    }))
})

const draftTagOptions = computed(() => {
  const selected = new Set(draftTagPaths.value)
  const merged = [...tagOptions.value]
  catalogTags.value.forEach((tag) => {
    if (!selected.has(tag.tagPath)) return
    if (merged.some((item) => item.value === tag.tagPath)) return
    merged.push({ label: tag.tagPath, value: tag.tagPath })
  })
  return merged
})

const displayTags = computed(() => groupTagsByDomain(selectedRow.value?.tags || []))

const displayPersons = computed(() => selectedRow.value?.persons || [])

const maskedDetailCjqk = computed(() => {
  const row = selectedRow.value
  if (!row) return '暂无处警情况'
  const masked = maskCjqkText(htmlToPlainText(row.cjqk), {
    personNames: (row.persons || []).map((person) => person.personName)
  })
  return masked || '暂无处警情况'
})

const detailPersonNames = computed(() =>
  displayPersons.value.map((person) => person.personName).filter(Boolean)
)

function maskedPersonDisplayName(person: TagV2PersonItem) {
  return maskPersonName(personDisplayName(person))
}

const verifyingRow = computed(
  () => rows.value.find((item) => rowKey(item) === verifyingRowId.value) || null
)

const expandedVerifyKeys = computed(() => (verifyingRowId.value ? [verifyingRowId.value] : []))

const contentFields = computed(() => {
  const row = selectedRow.value
  if (!row) return []
  return [
    { label: '反馈单号', value: row.fkdbh || '-' },
    { label: '处警单号', value: row.cjdbh || '-' },
    { label: '报警时间', value: row.bjsj || '-' },
    { label: '责任人', value: row.zrmj || '-' },
    { label: '反馈单位', value: row.fkdwmc || '-' },
    { label: '反馈人', value: row.fkrxm || '-' }
  ]
})

function matchStatsKeyword(text: string, keyword: string) {
  const value = String(text || '').toLowerCase()
  if (!value || !keyword) return false
  if (value.includes(keyword)) return true
  return value.split('/').filter(Boolean).some((seg) => seg.includes(keyword))
}

function resolveStatsCount(
  path: string,
  countMap: Map<string, { alarmCount: number; hitCount: number }>
) {
  const exact = countMap.get(path)
  if (exact) return exact
  let alarmCount = 0
  let hitCount = 0
  countMap.forEach((value, key) => {
    if (path === key || path.startsWith(`${key}/`) || key.startsWith(`${path}/`)) {
      alarmCount = Math.max(alarmCount, value.alarmCount)
      hitCount = Math.max(hitCount, value.hitCount)
    }
  })
  return { alarmCount, hitCount }
}

/** 路径各级前缀：地址类/娱乐场所/KTV → [地址类, 地址类/娱乐场所, 地址类/娱乐场所/KTV] */
function pathPrefixes(path: string): string[] {
  const parts = String(path || '')
    .split('/')
    .map((item) => item.trim())
    .filter(Boolean)
  const prefixes: string[] = []
  parts.forEach((_, index) => {
    prefixes.push(parts.slice(0, index + 1).join('/'))
  })
  return prefixes
}

const filteredStatsItems = computed(() => {
  const keyword = statsKeyword.value.trim().toLowerCase()
  // 无关键词：跟当前级数 Tab
  if (!keyword) return statsItems.value

  // 有关键词：以标签字典为搜索全集；命中叶子时同步放出匹配的中间级（如「娱乐」→「娱乐场所」）
  const countMap = new Map<string, { alarmCount: number; hitCount: number }>()
  const remember = (item: TagV2StatsItem) => {
    const key = String(item.pathPrefix || item.label || '').trim()
    if (!key || countMap.has(key)) return
    countMap.set(key, {
      alarmCount: Number(item.alarmCount || 0),
      hitCount: Number(item.hitCount || item.alarmCount || 0)
    })
  }
  globalStatsItems.value.forEach(remember)
  statsItems.value.forEach(remember)

  const rows: TagV2StatsItem[] = []
  const seen = new Set<string>()

  const pushPath = (path: string, label?: string) => {
    const key = String(path || '').trim()
    if (!key || seen.has(key)) return
    if (!matchStatsKeyword(key, keyword) && !matchStatsKeyword(leafLabel(key), keyword)) return
    seen.add(key)
    const counts = resolveStatsCount(key, countMap)
    rows.push({
      label: label || key,
      pathPrefix: key,
      alarmCount: counts.alarmCount,
      hitCount: counts.hitCount
    })
  }

  catalogTags.value.forEach((tag) => {
    const path = String(tag.tagPath || '').trim()
    if (!path) return
    const leafHit =
      matchStatsKeyword(path, keyword) ||
      matchStatsKeyword(tag.name, keyword) ||
      matchStatsKeyword(tag.level1 || '', keyword) ||
      matchStatsKeyword(tag.level2 || '', keyword) ||
      matchStatsKeyword(tag.level3 || '', keyword) ||
      matchStatsKeyword(tag.level4 || '', keyword)
    if (!leafHit) return
    // 叶子 + 所有命中关键词的中间前缀（娱乐场所）都进结果
    pathPrefixes(path).forEach((prefix) => pushPath(prefix))
  })

  // 字典未覆盖、但 combo/当前级统计里已有的路径也纳入
  ;[...globalStatsItems.value, ...statsItems.value].forEach((item) => {
    const path = String(item.pathPrefix || item.label || '').trim()
    if (!path) return
    if (!matchStatsKeyword(path, keyword) && !matchStatsKeyword(leafLabel(item.label), keyword)) return
    pathPrefixes(path).forEach((prefix) => pushPath(prefix, prefix === path ? item.label || path : prefix))
  })

  return rows.sort((a, b) => Number(b.alarmCount || 0) - Number(a.alarmCount || 0))
})

/** 层层下钻：有上级筛选时，只展示该前缀下的标签（切到二级/三级/四级仍带着一级条件） */
function matchesDrillDown(path: string, prefix: string) {
  const target = String(path || '').trim()
  const root = String(prefix || '').trim()
  if (!root) return true
  if (!target) return false
  return target === root || target.startsWith(`${root}/`) || root.startsWith(`${target}/`)
}

const displayStatsItems = computed(() => {
  const items = filteredStatsItems.value
  const prefix = activeStatPrefix.value.trim()
  // 全局关键词搜索时不过滤前缀，便于跨级查找
  if (!prefix || statsKeyword.value.trim()) return items
  return items.filter((item) =>
    matchesDrillDown(String(item.pathPrefix || item.label || ''), prefix)
  )
})

const isStatsGlobalSearch = computed(() => Boolean(statsKeyword.value.trim()))

const maxStatCount = computed(() =>
  Math.max(1, ...displayStatsItems.value.map((item) => item.alarmCount || 0))
)

const tableColumns = computed<DataTableColumns<TagV2AlarmRow>>(() => [
  {
    type: 'expand',
    width: 40,
    renderExpand: (row) => {
      if (verifyingRowId.value !== rowKey(row)) return null
      return h('div', { class: 'mx-1 mb-1 rounded-xl border border-blue-100 bg-blue-50/50 px-3 py-3' }, [
        h('p', { class: 'mb-1.5 text-xs font-medium text-slate-500' }, '处警情况'),
        h(
          'div',
          {
            class:
              'mb-3 max-h-40 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-100 bg-white px-3 py-2 text-sm leading-relaxed text-slate-700'
          },
          maskCjqkText(htmlToPlainText(row.cjqk), {
            personNames: (row.persons || []).map((person) => person.personName)
          }) || '暂无处警情况'
        ),
        h('p', { class: 'mb-2 mt-3 text-xs font-medium text-slate-500' }, '涉警人员'),
        h('div', { class: 'mb-3' }, [renderPersonsPanel(row.persons, true, true)]),
        h('p', { class: 'mb-2 text-xs font-medium text-blue-700' }, '编辑警情标签'),
        h(NSelect, {
          value: draftTagPaths.value,
          'onUpdate:value': (value: string[]) => {
            draftTagPaths.value = value || []
          },
          multiple: true,
          filterable: true,
          clearable: true,
          tag: true,
          options: draftTagOptions.value,
          loading: loadingCatalog.value,
          placeholder: '从 tag_dict_v2 选择标签路径',
          maxTagCount: 6,
          class: 'w-full'
        }),
        h('div', { class: 'mt-3 flex items-center gap-2' }, [
          h(
            NButton,
            { size: 'small', disabled: savingVerify.value, onClick: () => cancelVerify() },
            { default: () => '取消' }
          ),
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              loading: savingVerify.value,
              onClick: () => void saveVerify()
            },
            { default: () => '保存核对' }
          )
        ])
      ])
    }
  },
  {
    title: '#',
    key: 'index',
    width: 52,
    render: (_row, index) => pageStart.value + index
  },
  {
    title: '反馈单号',
    key: 'fkdbh',
    minWidth: 220,
    ellipsis: { tooltip: true },
    render: (row) =>
      h(
        'button',
        {
          type: 'button',
          class: 'font-mono text-blue-600 hover:underline',
          onClick: () => openDetail(row)
        },
        row.fkdbh || '-'
      )
  },
  {
    title: '反馈单位',
    key: 'fkdwmc',
    minWidth: 120,
    ellipsis: { tooltip: true },
    render: (row) => row.fkdwmc || '-'
  },
  {
    title: '是否核对',
    key: 'manualVerified',
    width: 88,
    align: 'center',
    render: (row) =>
      h(
        NTag,
        {
          size: 'small',
          round: true,
          bordered: false,
          type: row.manualVerified ? 'success' : 'default'
        },
        { default: () => (row.manualVerified ? '已核对' : '未核对') }
      )
  },
  {
    title: '报警时间',
    key: 'bjsj',
    width: 168,
    render: (row) => row.bjsj || '-'
  },
  {
    title: '责任人',
    key: 'zrmj',
    width: 88,
    ellipsis: { tooltip: true },
    render: (row) => row.zrmj || '-'
  },
  {
    title: '反馈人',
    key: 'fkrxm',
    width: 88,
    ellipsis: { tooltip: true },
    render: (row) => row.fkrxm || '-'
  },
  {
    title: '处警情况',
    key: 'cjqk',
    width: 400,
    render: (row) => {
      const text = htmlToPlainText(row.cjqk) || '-'
      return h(
        NTooltip,
        {
          placement: 'top',
          contentStyle: {
            width: '520px',
            maxWidth: '520px',
            padding: '8px 14px 8px 10px',
            boxSizing: 'border-box',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            lineHeight: '1.5'
          }
        },
        {
          trigger: () =>
            h(
              'span',
              {
                class: 'block w-full overflow-hidden text-ellipsis whitespace-nowrap'
              },
              text
            ),
          default: () =>
            h(
              'div',
              {
                style: {
                  maxWidth: '492px',
                  paddingRight: '4px',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  lineHeight: '1.5'
                }
              },
              text
            )
        }
      )
    }
  },
  {
    title: '警情标签',
    key: 'tags',
    minWidth: 340,
    render: (row) => {
      const tags = (row.tags || []).slice(0, 3)
      if (!tags.length) return h('span', { class: 'text-slate-400' }, '-')
      return h(
        'div',
        { class: 'flex flex-wrap gap-1' },
        tags.map((tag) =>
          h(
            NTag,
            { size: 'small', round: true, bordered: false, type: sourceType(tag.source) },
            { default: () => tag.name || tag.tagPath.split('/').pop() || tag.tagPath }
          )
        ).concat(
          (row.tags || []).length > 3
            ? [h('span', { class: 'text-xs text-slate-400' }, `+${(row.tags || []).length - 3}`)]
            : []
        )
      )
    }
  },
  {
    title: '涉警人员',
    key: 'persons',
    minWidth: 220,
    render: (row) => renderPersonSummary(row)
  },
  {
    title: '操作',
    key: 'actions',
    width: 128,
    fixed: 'right',
    render: (row) => {
      const key = rowKey(row)
      const isVerifying = verifyingRowId.value === key
      return h('div', { class: 'flex items-center gap-0' }, [
        h(
          NButton,
          { size: 'tiny', quaternary: true, type: 'primary', onClick: () => openDetail(row) },
          { default: () => '详情' }
        ),
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            type: isVerifying ? 'warning' : 'default',
            onClick: (event: MouseEvent) => {
              event.stopPropagation()
              startVerifyRow(row)
            }
          },
          {
            default: () => (isVerifying ? '收起' : '核对')
          }
        )
      ])
    }
  }
])

watch(pageNum, () => {
  if (verifyingRowId.value) cancelVerify()
})

watch(statsLevel, () => {
  // 全局搜索进行中时列表不跟随级数，无需重复拉当前级统计
  if (hasSearched.value && !statsKeyword.value.trim()) {
    void loadStats({ includeGlobal: false })
  }
})

let statsKeywordTimer: ReturnType<typeof setTimeout> | undefined
watch(statsKeyword, (value, oldValue) => {
  const next = String(value || '').trim()
  const prev = String(oldValue || '').trim()
  if (statsKeywordTimer) clearTimeout(statsKeywordTimer)

  // 退出全局搜索后，按当前级数刷新列表
  if (prev && !next && hasSearched.value) {
    void loadStats({ includeGlobal: false })
    return
  }

  // 进入全局搜索时补拉 combo（市局未选派出所时初始查询会跳过 combo）
  if (next && hasSearched.value && !globalStatsItems.value.length) {
    statsKeywordTimer = setTimeout(() => {
      void loadStats({ includeGlobal: true })
    }, 280)
  }
})

function rowKey(row: TagV2AlarmRow | null | undefined) {
  return String(row?.fkdbh || row?.id || '').trim()
}

function htmlToPlainText(html?: string | null) {
  if (!html) return ''
  return String(html)
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+\n/g, '\n')
    .trim()
}

function sourceLabel(source?: string | null) {
  const map: Record<string, string> = {
    llm: 'AI',
    rule: '规则',
    map: '映射',
    manual: '人工'
  }
  return map[String(source || '')] || source || '-'
}

function sourceType(source?: string | null): 'default' | 'info' | 'success' | 'warning' {
  if (source === 'manual') return 'success'
  if (source === 'rule' || source === 'map') return 'warning'
  return 'info'
}

function personSourceType(source?: string | null): 'default' | 'info' | 'success' | 'warning' {
  if (source === 'manual') return 'success'
  if (source === 'third_party' || source === 'zj-api') return 'warning'
  return 'info'
}

function renderPersonsPanel(
  persons: TagV2PersonItem[] | undefined | null,
  compact = false,
  masked = false
) {
  const list = persons || []
  if (!list.length) {
    return h('div', { class: 'text-xs text-slate-400' }, '暂无涉警人员')
  }
  return h(
    'div',
    { class: compact ? 'space-y-2' : 'space-y-3' },
    list.map((person) => {
      const roleLabel = person.personRoleLabel || personRoleLabel(person.personRole)
      const rawName = personDisplayName(person)
      const name = masked ? maskPersonName(rawName) : rawName
      const extractTags = personExtractTags(person)
      const zjTags = personZjTags(person)
      return h(
        'div',
        {
          key: `${person.personRole}-${person.idNo || ''}-${person.personName || ''}`,
          class: 'rounded-lg border border-slate-100 bg-white px-3 py-2.5'
        },
        [
          h('div', { class: 'flex flex-wrap items-center gap-x-2 gap-y-1' }, [
            h(NTag, { size: 'small', round: true, bordered: false, type: 'default' }, { default: () => roleLabel }),
            h('span', { class: 'text-sm font-medium text-slate-800' }, name),
            person.idNo
              ? h('span', { class: 'text-xs text-slate-500' }, maskIdNo(person.idNo))
              : null,
            person.phone
              ? h('span', { class: 'text-xs text-slate-500' }, masked ? maskPhone(person.phone) : person.phone)
              : null,
            h(
              'span',
              { class: 'text-[11px] text-slate-400' },
              enrichStatusLabel(person.enrichStatus)
            )
          ]),
          extractTags.length
            ? h(
                'div',
                { class: 'mt-2 flex flex-wrap gap-1' },
                extractTags.map((tag) =>
                  h(
                    NTag,
                    {
                      key: `extract-${tag.tagPath}-${tag.source}`,
                      size: 'small',
                      round: true,
                      bordered: false,
                      type: personSourceType(tag.source)
                    },
                    { default: () => personTagLeaf(tag) }
                  )
                )
              )
            : null,
          h('div', { class: 'mt-2 flex flex-wrap items-center gap-1' }, [
            h('span', { class: 'mr-1 text-[11px] text-amber-700' }, '治安标签'),
            ...(zjTags.length
              ? zjTags.map((tag) =>
                  h(
                    NTag,
                    {
                      key: `zj-${tag.tagPath}-${tag.tagCode || ''}`,
                      size: 'small',
                      round: true,
                      bordered: false,
                      type: 'warning'
                    },
                    { default: () => personTagLeaf(tag) }
                  )
                )
              : [
                  h(
                    'span',
                    { class: 'text-[11px] text-slate-400' },
                    person.enrichStatus === '2' ? '无命中' : person.enrichStatus === '1' ? '已补全(无明细)' : '待补全'
                  )
                ])
          ])
        ]
      )
    })
  )
}

function renderPersonSummary(row: TagV2AlarmRow) {
  const persons = row.persons || []
  if (!persons.length) return h('span', { class: 'text-slate-400' }, '-')
  const chips = persons.slice(0, 2).map((person) => {
    const roleLabel = person.personRoleLabel || personRoleLabel(person.personRole)
    const zjTags = personZjTags(person)
    const firstZj = zjTags[0]
    const firstExtract = personExtractTags(person)[0]
    const tagText = firstZj
      ? personTagLeaf(firstZj)
      : firstExtract
        ? personTagLeaf(firstExtract)
        : enrichStatusLabel(person.enrichStatus)
    return h(
      'span',
      { key: `${person.personRole}-${person.idNo || person.personName}`, class: 'text-xs text-slate-700' },
      `${personDisplayName(person)}(${roleLabel})·${tagText}`
    )
  })
  const extra = persons.length > 2 ? h('span', { class: 'text-xs text-slate-400' }, `+${persons.length - 2}`) : null
  return h('div', { class: 'space-y-1' }, [...chips, extra].filter(Boolean))
}

function leafLabel(path: string) {
  const parts = String(path || '').split('/').filter(Boolean)
  return parts[parts.length - 1] || path
}

function findAccountDept() {
  const accountDeptId = Number(authStore.deptId || 0)
  const accountDeptCode = String(authStore.deptCode || '').trim()
  const accountDeptName = String(authStore.deptName || '').trim()
  if (accountDeptId) {
    const byId = scopedDeptRows.value.find((item) => Number(item.deptId || 0) === accountDeptId)
    if (byId) return byId
  }
  if (accountDeptCode) {
    const byCode = scopedDeptRows.value.find((item) => String(item.deptCode || '').trim() === accountDeptCode)
    if (byCode) return byCode
  }
  if (accountDeptName) {
    return scopedDeptRows.value.find((item) => String(item.deptName || '').trim() === accountDeptName) || null
  }
  return null
}

function resolveFkdwdmFromDept(dept: DeptOption | null | undefined) {
  const code = String(dept?.deptCode || '').trim()
  const name = String(dept?.deptName || '').trim()
  if (!code) return ''
  if (isCityBureauDept(code, name)) return ''
  return code
}

function applyAccountDeptDefault() {
  if (authStore.isCityBureau) {
    selectedDeptKey.value = null
    filters.fkdwmc = ''
    filters.fkdwdm = ''
    return
  }
  const dept = findAccountDept()
  if (!dept) {
    selectedDeptKey.value = authStore.deptId || null
    filters.fkdwmc = String(authStore.deptName || '').trim()
    filters.fkdwdm = String(authStore.deptCode || '').trim()
    return
  }
  selectedDeptKey.value = String(dept.deptId || '')
  filters.fkdwmc = String(dept.deptName || '').trim()
  filters.fkdwdm = resolveFkdwdmFromDept(dept)
}

function updateDept(key: string | null) {
  if (!key) {
    if (!authStore.isCityBureau) {
      applyAccountDeptDefault()
      return
    }
    selectedDeptKey.value = null
    filters.fkdwmc = ''
    filters.fkdwdm = ''
    return
  }
  const dept = scopedDeptRows.value.find((item) => String(item.deptId || '') === String(key))
  const code = String(dept?.deptCode || '').trim()
  const name = String(dept?.deptName || '').trim()
  // 选中市局节点 = 不按部门过滤（只带 fkdwmc 无 fkdwdm 会误触发后端 join 反馈单大表，极慢）
  if (isCityBureauDept(code, name)) {
    selectedDeptKey.value = null
    filters.fkdwmc = ''
    filters.fkdwdm = ''
    return
  }
  selectedDeptKey.value = key
  filters.fkdwmc = name
  filters.fkdwdm = resolveFkdwdmFromDept(dept)
}

function hasSearchScope() {
  return (
    Boolean(filters.beginTime.trim() && filters.endTime.trim()) ||
    Boolean(filters.fkdbh.trim()) ||
    Boolean(filters.cjdbh.trim()) ||
    Boolean(filters.fkdwmc.trim()) ||
    Boolean(filters.fkdwdm.trim()) ||
    Boolean(filters.fkrxm.trim()) ||
    Boolean(filters.keyword.trim()) ||
    Boolean(filters.domain) ||
    filters.includeTags.length > 0 ||
    selectedAjlbCodes.value.length > 0 ||
    selectedAjlxCodes.value.length > 0 ||
    selectedAjxlCodes.value.length > 0
  )
}

function pushUniqueOption(target: SelectOption[], code: string, name: string) {
  const value = String(code || '').trim()
  if (!value) return
  if (target.some((item) => String(item.value) === value)) return
  target.push({ label: String(name || value).trim() || value, value })
}

function flattenFeedbackOptions(tree: FeedbackCategoryNode[]) {
  const categories: SelectOption[] = []
  const types: SelectOption[] = []
  const subtypes: SelectOption[] = []
  tree.forEach((category) => {
    pushUniqueOption(categories, category.code, category.name)
    ;(category.children || []).forEach((type) => {
      pushUniqueOption(types, type.code, type.name)
      ;(type.children || []).forEach((subtype) => {
        pushUniqueOption(subtypes, subtype.code, subtype.name)
      })
    })
  })
  feedbackCategoryOptions.value = categories
  feedbackTypeOptions.value = types
  feedbackSubtypeOptions.value = subtypes
}

function buildSearchPayload(page = pageNum.value) {
  return {
    includeTags: filters.includeTags,
    domain: filters.domain || undefined,
    fkdbh: filters.fkdbh.trim() || undefined,
    cjdbh: filters.cjdbh.trim() || undefined,
    fkdwmc: filters.fkdwmc.trim() || undefined,
    fkdwdm: filters.fkdwdm.trim() || undefined,
    fkrxm: filters.fkrxm.trim() || undefined,
    keyword: filters.keyword.trim() || undefined,
    beginTime: filters.beginTime.trim() || undefined,
    endTime: filters.endTime.trim() || undefined,
    ajlbCodes: selectedAjlbCodes.value,
    ajlxCodes: selectedAjlxCodes.value,
    ajxlCodes: selectedAjxlCodes.value,
    hasManual:
      filters.verifyStatus === 'manual' ? true : filters.verifyStatus === 'auto' ? false : undefined,
    pageNum: page,
    pageSize: pageSize.value
  }
}

async function loadFeedbackCategoryTree() {
  loadingFeedbackTree.value = true
  try {
    const response = await getFeedbackCategoryTree()
    const tree = (response.data || []) as FeedbackCategoryNode[]
    flattenFeedbackOptions(tree)
  } catch (error) {
    feedbackCategoryOptions.value = []
    feedbackTypeOptions.value = []
    feedbackSubtypeOptions.value = []
    message.error(error instanceof Error ? error.message : '反馈类别树加载失败')
  } finally {
    loadingFeedbackTree.value = false
  }
}

async function loadCatalog() {
  loadingCatalog.value = true
  try {
    const response = await listTagV2Catalog()
    catalogTags.value = response.data?.tags || []
    domains.value = response.data?.domains || []
    const dataRange = response.data?.dataRange
    const cover = coverTaggedDayRange(dataRange?.beginTime, dataRange?.endTime)
    if (cover) {
      const hasCache = Boolean(filters.beginTime && filters.endTime)
      const overlap =
        hasCache &&
        rangesOverlap(filters.beginTime, filters.endTime, dataRange?.beginTime, dataRange?.endTime)
      if (!hasCache || !overlap) {
        setTimeRange(cover[0], cover[1], '', false)
        if (hasCache && !overlap && (dataRange?.alarmCount || 0) > 0) {
          message.info(`当前报告时间范围内无打标数据，已切换到有数据区间（约 ${dataRange?.alarmCount} 条）`)
        }
      }
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '标签字典加载失败')
  } finally {
    loadingCatalog.value = false
  }
}

async function loadDepts() {
  loadingDepts.value = true
  try {
    if (!authStore.deptId && authStore.token) {
      await authStore.loadUserInfo()
    }
    deptRows.value = await authStore.listScopedDeptOptions()
    expandedDeptKeys.value = collectExpandedKeys(deptTreeOptions.value).slice(0, 12)
    applyAccountDeptDefault()
  } catch (error) {
    deptRows.value = []
    message.error(error instanceof Error ? error.message : '部门加载失败')
  } finally {
    loadingDepts.value = false
  }
}

async function loadStats(options?: { includeGlobal?: boolean }) {
  if (!hasSearchScope()) {
    statsItems.value = []
    globalStatsItems.value = []
    statsTotalAlarms.value = 0
    return
  }
  const includeGlobal = options?.includeGlobal !== false
  loadingStats.value = true
  try {
    const payload = buildSearchPayload(1)
    // 左侧统计不受「点击卡片」过滤影响，便于在同级卡片间切换
    if (
      activeStatPrefix.value &&
      payload.includeTags?.length === 1 &&
      payload.includeTags[0] === activeStatPrefix.value
    ) {
      payload.includeTags = []
    }
    const levelPromise = statsTagV2Alarms({
      ...payload,
      level: statsLevel.value,
      limit: 500
    })
    // 市局未选派出所时，combo 全路径统计很重；仅在统计关键词搜索或已选派出所时再拉
    const needCombo =
      includeGlobal &&
      (Boolean(statsKeyword.value.trim()) || Boolean(filters.fkdwdm.trim()))
    if (!needCombo) {
      const levelRes = await levelPromise
      statsItems.value = levelRes.data?.items || []
      if (includeGlobal) globalStatsItems.value = []
      statsTotalAlarms.value = Number(levelRes.data?.totalAlarms || 0)
      return
    }
    const [levelRes, comboRes] = await Promise.all([
      levelPromise,
      statsTagV2Alarms({
        ...payload,
        level: 'combo',
        limit: 2000
      })
    ])
    statsItems.value = levelRes.data?.items || []
    globalStatsItems.value = comboRes.data?.items || []
    statsTotalAlarms.value = Number(levelRes.data?.totalAlarms || comboRes.data?.totalAlarms || 0)
  } catch (error) {
    statsItems.value = []
    if (includeGlobal) globalStatsItems.value = []
    statsTotalAlarms.value = 0
    message.error(error instanceof Error ? error.message : '标签统计加载失败')
  } finally {
    loadingStats.value = false
  }
}

async function runSearch(resetPage = true) {
  if (!hasSearchScope()) {
    message.warning('请先选择时间范围或其它筛选条件，再查询')
    return
  }
  if (resetPage) pageNum.value = 1
  loading.value = true
  try {
    const [listRes] = await Promise.all([
      searchTagV2Alarms(buildSearchPayload(pageNum.value)),
      loadStats()
    ])
    rows.value = listRes.data?.rows || []
    pageTotal.value = Number(listRes.data?.total || 0)
    hasSearched.value = true
    if (!rows.value.some((item) => rowKey(item) === selectedId.value)) {
      selectedId.value = ''
    }
    if (searchExpanded.value && pageTotal.value > 0) {
      searchExpanded.value = false
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '警情列表加载失败')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.fkdbh = ''
  filters.cjdbh = ''
  filters.fkrxm = ''
  filters.keyword = ''
  filters.domain = null
  filters.includeTags = []
  filters.verifyStatus = 'all'
  selectedAjlbCodes.value = []
  selectedAjlxCodes.value = []
  selectedAjxlCodes.value = []
  activeStatPrefix.value = ''
  if (authStore.isCityBureau) {
    selectedDeptKey.value = null
    filters.fkdwmc = ''
    filters.fkdwdm = ''
  } else {
    applyAccountDeptDefault()
  }
  applyTimeFromReportCache()
  runSearch(true)
}

async function changePage(nextPage: number) {
  if (nextPage < 1 || nextPage > pageCount.value || nextPage === pageNum.value) return
  pageNum.value = nextPage
  await runSearch(false)
}

function selectStatCard(item: TagV2StatsItem) {
  const prefix = String(item.pathPrefix || item.label || '').trim()
  if (!prefix) return
  if (activeStatPrefix.value === prefix) {
    activeStatPrefix.value = ''
    filters.includeTags = []
  } else {
    activeStatPrefix.value = prefix
    filters.includeTags = [prefix]
    const depth = Number(statsLevel.value)
    const next = String(Math.min(4, depth + 1)) as TagV2StatsLevel
    if (next !== statsLevel.value) {
      statsLevel.value = next
    }
  }
  runSearch(true)
}

function clearStatFilter() {
  activeStatPrefix.value = ''
  filters.includeTags = []
  runSearch(true)
}

function onIncludeTagsChange(value: string[] | null) {
  const tags = value || []
  filters.includeTags = tags
  activeStatPrefix.value = tags.length === 1 ? tags[0] : ''
}

function openDetail(row: TagV2AlarmRow) {
  selectedId.value = rowKey(row)
  detailVisible.value = true
}

function closeDetail() {
  detailVisible.value = false
}

function startVerifyRow(row: TagV2AlarmRow) {
  const key = rowKey(row)
  if (!key) return
  if (verifyingRowId.value === key) {
    cancelVerify()
    return
  }
  verifyingRowId.value = key
  draftTagPaths.value = (row.tags || []).map((item) => item.tagPath)
}

function cancelVerify() {
  verifyingRowId.value = ''
  draftTagPaths.value = []
}

function onExpandedVerifyKeysChange(keys: Array<string | number>) {
  if (!keys.length) {
    cancelVerify()
  }
}

async function saveVerify() {
  const row = verifyingRow.value
  if (!row) return
  savingVerify.value = true
  try {
    const response = await verifyTagV2Alarm({
      fkdbh: rowKey(row),
      tagPaths: draftTagPaths.value
    })
    const saved = response.data
    if (saved) {
      const index = rows.value.findIndex((item) => rowKey(item) === rowKey(row))
      if (index >= 0) rows.value[index] = { ...rows.value[index], ...saved }
      else rows.value.unshift(saved)
    } else {
      const detail = await getTagV2AlarmDetail(rowKey(row))
      const index = rows.value.findIndex((item) => rowKey(item) === rowKey(row))
      if (index >= 0 && detail.data) rows.value[index] = { ...rows.value[index], ...detail.data }
    }
    cancelVerify()
    message.success('核对保存成功')
    loadStats()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '核对保存失败')
  } finally {
    savingVerify.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadCatalog(), loadDepts(), loadFeedbackCategoryTree()])
  if (filters.beginTime && filters.endTime) {
    await runSearch(true)
  }
})
</script>

<template>
  <section class="grid h-full min-h-0 grid-cols-1 gap-3 overflow-hidden p-3 text-sm leading-6 xl:grid-cols-[minmax(280px,320px)_minmax(0,1fr)]">
    <!-- 左侧：分层统计卡片 -->
    <aside class="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-white/80 bg-white/80 shadow-xl shadow-blue-200/20 backdrop-blur-2xl ring-1 ring-white/80">
      <div class="border-b border-slate-100 px-4 py-3">
        <div class="flex items-center gap-2">
          <LayoutGrid :size="16" class="shrink-0 text-blue-600" />
          <div class="min-w-0 flex-1">
            <h2 class="text-sm font-semibold text-slate-900">标签统计</h2>
            <p class="truncate text-xs text-slate-500">
              共 {{ statsTotalAlarms }} 条已打标警情
            </p>
          </div>
        </div>
        <div class="mt-3">
          <NInput
            v-model:value="statsKeyword"
            clearable
            size="small"
            placeholder="全局搜索标签名称 / 路径"
          >
            <template #prefix>
              <NIcon :component="Search" :size="14" class="text-slate-400" />
            </template>
          </NInput>
        </div>
        <div class="mt-3 flex flex-wrap gap-1.5" :class="isStatsGlobalSearch ? 'pointer-events-none opacity-45' : ''">
          <button
            v-for="opt in statsLevelOptions"
            :key="opt.value"
            type="button"
            class="rounded-full px-2.5 py-1 text-xs transition"
            :class="
              !isStatsGlobalSearch && statsLevel === opt.value
                ? 'bg-blue-600 text-white shadow-sm shadow-blue-200'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200/80'
            "
            @click="statsLevel = opt.value"
          >
            {{ opt.label }}
          </button>
        </div>
        <div v-if="activeStatPrefix" class="mt-2 flex items-center gap-2 rounded-lg bg-blue-50 px-2.5 py-1.5 text-xs text-blue-700">
          <span class="min-w-0 flex-1 truncate">筛选：{{ activeStatPrefix }}</span>
          <button type="button" class="shrink-0 hover:underline" @click="clearStatFilter">清除</button>
        </div>
      </div>

      <div class="min-h-0 flex-1 overflow-auto p-3">
        <NSpin :show="loadingStats" class="min-h-40">
          <div v-if="!loadingStats && !displayStatsItems.length" class="px-2 py-10 text-center text-slate-400">
            {{
              !hasSearched
                ? '请先查询后再看统计'
                : statsKeyword.trim()
                  ? '未匹配到相关标签'
                  : activeStatPrefix
                    ? '当前筛选下暂无下级标签'
                    : '当前条件下暂无统计'
            }}
          </div>
          <div class="space-y-2">
            <button
              v-for="item in displayStatsItems"
              :key="item.pathPrefix || item.label"
              type="button"
              class="w-full rounded-xl border px-3 py-2.5 text-left transition"
              :class="
                activeStatPrefix === item.pathPrefix
                  ? 'border-blue-300 bg-blue-50/90 shadow-sm shadow-blue-100'
                  : 'border-slate-100 bg-white/70 hover:border-blue-200 hover:bg-blue-50/40'
              "
              @click="selectStatCard(item)"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <p class="truncate font-medium text-slate-800" :title="item.label">
                    {{ leafLabel(item.label) }}
                  </p>
                  <p v-if="item.label.includes('/')" class="mt-0.5 truncate text-[11px] text-slate-400" :title="item.label">
                    {{ item.label }}
                  </p>
                </div>
                <div class="shrink-0 text-right">
                  <p class="text-base font-semibold tabular-nums text-blue-700">{{ item.alarmCount }}</p>
                  <p class="text-[11px] text-slate-400">警情</p>
                </div>
              </div>
              <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
                <div
                  class="h-full rounded-full bg-gradient-to-r from-blue-500 to-sky-400 transition-all"
                  :style="{ width: `${Math.max(8, (item.alarmCount / maxStatCount) * 100)}%` }"
                />
              </div>
            </button>
          </div>
        </NSpin>
      </div>
    </aside>

    <!-- 右侧：搜索 + 表格 -->
    <main class="flex min-h-0 flex-col gap-3 overflow-hidden">
      <section class="shrink-0 overflow-hidden rounded-2xl border border-white/80 bg-white/80 shadow-xl shadow-blue-200/20 backdrop-blur-2xl ring-1 ring-white/80">
        <div class="flex flex-wrap items-center gap-2 px-4 py-3">
          <div class="flex min-w-0 shrink-0 items-center gap-2">
            <Tags :size="16" class="shrink-0 text-blue-600" />
            <h2 class="text-sm font-semibold text-slate-900">警情打标</h2>
          </div>
          <div class="ml-auto flex flex-wrap items-center justify-end gap-2">
            <div class="w-[340px] shrink-0">
              <NDatePicker
                v-model:formatted-value="alarmTimeRange"
                class="w-full"
                size="small"
                type="datetimerange"
                clearable
                value-format="yyyy-MM-dd HH:mm:ss"
                format="yyyy-MM-dd HH:mm:ss"
                time-picker-format="HH:mm:ss"
                start-placeholder="报警时间起"
                end-placeholder="报警时间止"
              />
            </div>
            <div class="w-[148px] shrink-0">
              <NSelect
                v-model:value="selectedAjlbCodes"
                multiple
                clearable
                filterable
                size="small"
                :options="feedbackCategoryOptions"
                :loading="loadingFeedbackTree"
                :max-tag-count="1"
                placeholder="反馈类别"
              />
            </div>
            <div class="w-[148px] shrink-0">
              <NSelect
                v-model:value="selectedAjlxCodes"
                multiple
                clearable
                filterable
                size="small"
                :options="feedbackTypeOptions"
                :loading="loadingFeedbackTree"
                :max-tag-count="1"
                placeholder="反馈类型"
              />
            </div>
            <div class="w-[148px] shrink-0">
              <NSelect
                v-model:value="selectedAjxlCodes"
                multiple
                clearable
                filterable
                size="small"
                :options="feedbackSubtypeOptions"
                :loading="loadingFeedbackTree"
                :max-tag-count="1"
                placeholder="反馈细类"
              />
            </div>
            <div class="w-[180px] shrink-0">
              <NTreeSelect
                :value="selectedDeptKey"
                :options="deptTreeOptions"
                :loading="loadingDepts"
                :default-expanded-keys="expandedDeptKeys"
                :clearable="authStore.isCityBureau"
                filterable
                size="small"
                :placeholder="authStore.isCityBureau ? '部门（不选=全市）' : '部门（仅本部门）'"
                key-field="key"
                label-field="label"
                @update:value="updateDept"
              />
            </div>
            <NButton type="primary" size="small" :loading="loading" @click="() => runSearch(true)">
              <template #icon><NIcon :component="Search" :size="14" /></template>
              查询
            </NButton>
            <NButton size="small" secondary :disabled="loading" @click="searchExpanded = !searchExpanded">
              <template #icon>
                <NIcon :component="searchExpanded ? ChevronUp : ChevronDown" :size="14" />
              </template>
              {{ searchExpanded ? '收起' : '展开' }}
            </NButton>
          </div>
        </div>

        <div v-show="searchExpanded" class="border-t border-slate-100 px-4 py-3">
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
            <NInput v-model:value="filters.fkdbh" clearable placeholder="反馈单号" @keyup.enter="runSearch(true)" />
            <NInput v-model:value="filters.cjdbh" clearable placeholder="处警单号" @keyup.enter="runSearch(true)" />
            <NInput v-model:value="filters.fkrxm" clearable placeholder="反馈人" @keyup.enter="runSearch(true)" />
            <NInput v-model:value="filters.keyword" clearable placeholder="处警情况关键词" @keyup.enter="runSearch(true)" />
            <NSelect
              v-model:value="filters.verifyStatus"
              :options="verifyStatusOptions"
              placeholder="标签来源"
            />
            <NSelect
              v-model:value="filters.domain"
              :options="domainOptions"
              :loading="loadingCatalog"
              clearable
              filterable
              placeholder="标签域"
            />
            <NSelect
              v-model:value="filters.includeTags"
              multiple
              filterable
              clearable
              :options="tagOptions"
              :loading="loadingCatalog"
              placeholder="包含标签路径"
              class="sm:col-span-2 xl:col-span-3"
              :max-tag-count="3"
              @update:value="onIncludeTagsChange"
            />
          </div>
          <div class="mt-3 flex gap-2">
            <NButton type="primary" :loading="loading" @click="() => runSearch(true)">
              <template #icon><NIcon :component="Search" :size="16" /></template>
              查询
            </NButton>
            <NButton secondary :disabled="loading" @click="resetFilters">
              <template #icon><NIcon :component="RotateCcw" :size="16" /></template>
              重置
            </NButton>
          </div>
        </div>
      </section>

      <section class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-white/80 bg-white/80 shadow-xl shadow-blue-200/20 backdrop-blur-2xl ring-1 ring-white/80">
        <div class="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-2.5 text-xs text-slate-500">
          <span>{{ pageTotal ? `${pageStart}-${pageEnd} / ${pageTotal}` : '0 条' }}</span>
          <div class="flex items-center gap-1">
            <NButton size="tiny" quaternary :disabled="pageNum <= 1 || loading" @click="changePage(pageNum - 1)">
              <template #icon><NIcon :component="ChevronLeft" :size="14" /></template>
            </NButton>
            <span>{{ pageNum }} / {{ pageCount }}</span>
            <NButton size="tiny" quaternary :disabled="pageNum >= pageCount || loading" @click="changePage(pageNum + 1)">
              <template #icon><NIcon :component="ChevronRight" :size="14" /></template>
            </NButton>
          </div>
        </div>

        <div class="min-h-0 flex-1 overflow-auto p-2">
          <NDataTable
            :columns="tableColumns"
            :data="rows"
            :loading="loading"
            :row-key="(row: TagV2AlarmRow) => rowKey(row)"
            :expanded-row-keys="expandedVerifyKeys"
            @update:expanded-row-keys="onExpandedVerifyKeysChange"
            :bordered="false"
            :single-line="false"
            size="small"
            flex-height
            class="h-full"
            :row-props="(row: TagV2AlarmRow) => ({
              style: 'cursor: pointer',
              onDblclick: () => openDetail(row)
            })"
          />
          <div v-if="!loading && hasSearched && !rows.length" class="py-10 text-center text-slate-400">
            未检索到已打标警情
          </div>
          <div v-if="!loading && !hasSearched" class="py-10 text-center text-slate-400">
            请设置筛选条件后查询
          </div>
        </div>
      </section>
    </main>

    <NModal
      v-model:show="detailVisible"
      preset="card"
      :title="selectedRow?.fkdbh || '警情详情'"
      class="!w-[920px] max-w-[calc(100vw-32px)]"
      :bordered="false"
      @after-leave="closeDetail"
    >
      <div v-if="selectedRow" class="max-h-[70vh] space-y-4 overflow-auto pr-1">
        <section class="grid grid-cols-1 gap-2 rounded-xl bg-slate-50/80 p-3 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="field in contentFields" :key="field.label" class="min-w-0">
            <p class="text-xs text-slate-500">{{ field.label }}</p>
            <p class="truncate font-medium text-slate-800">{{ field.value }}</p>
          </div>
        </section>

        <section>
          <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">处警情况</h3>
          <div class="whitespace-pre-wrap rounded-xl border border-slate-100 bg-white px-3 py-3 text-slate-700">
            {{ maskedDetailCjqk }}
          </div>
        </section>

        <section class="space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500">警情打标结果</h3>
            <span class="text-xs text-slate-400">{{ selectedRow.tagCount || 0 }} 个标签</span>
          </div>

          <div v-if="!displayTags.length" class="rounded-xl border border-dashed border-slate-200 px-4 py-8 text-center text-slate-400">
            暂无标签
          </div>

          <div
            v-for="group in displayTags"
            :key="group.domain"
            class="overflow-hidden rounded-xl border border-slate-100"
          >
            <div class="border-b border-slate-100 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700">
              {{ group.domain }}
              <span class="ml-1 font-normal text-slate-400">({{ group.items.length }})</span>
            </div>
            <div class="divide-y divide-slate-50">
              <div
                v-for="tag in group.items"
                :key="`${tag.tagPath}-${tag.source}`"
                class="flex items-start justify-between gap-3 px-3 py-2.5"
              >
                <div class="min-w-0 flex-1">
                  <p class="break-all font-medium text-slate-800">{{ tag.tagPath }}</p>
                  <p v-if="tag.evidence" class="mt-0.5 line-clamp-2 text-xs text-slate-500">
                    依据：{{ maskCjqkText(tag.evidence, { personNames: detailPersonNames }) }}
                  </p>
                </div>
                <div class="flex shrink-0 flex-col items-end gap-1">
                  <NTag size="small" round :bordered="false" :type="sourceType(tag.source)">
                    {{ sourceLabel(tag.source) }}
                  </NTag>
                  <span v-if="tag.confidence != null" class="text-[11px] text-slate-400">
                    {{ Number(tag.confidence).toFixed(2) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500">涉警人员</h3>
            <span class="text-xs text-slate-400">{{ selectedRow.personCount || displayPersons.length || 0 }} 人</span>
          </div>
          <div v-if="!displayPersons.length" class="rounded-xl border border-dashed border-slate-200 px-4 py-8 text-center text-slate-400">
            暂无涉警人员
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="person in displayPersons"
              :key="`${person.personRole}-${person.idNo || person.personName}`"
              class="rounded-xl border border-slate-100 bg-slate-50/50 px-3 py-3"
            >
              <div class="flex flex-wrap items-center gap-2">
                <NTag size="small" round :bordered="false">{{ person.personRoleLabel || personRoleLabel(person.personRole) }}</NTag>
                <span class="font-medium text-slate-800">{{ maskedPersonDisplayName(person) }}</span>
                <span v-if="person.idNo" class="text-xs text-slate-500">{{ maskIdNo(person.idNo) }}</span>
                <span v-if="person.phone" class="text-xs text-slate-500">{{ maskPhone(person.phone) }}</span>
                <span class="text-[11px] text-slate-400">{{ enrichStatusLabel(person.enrichStatus) }}</span>
              </div>
              <div v-if="personExtractTags(person).length" class="mt-2 flex flex-wrap gap-1">
                <NTag
                  v-for="tag in personExtractTags(person)"
                  :key="`extract-${tag.tagPath}-${tag.source}`"
                  size="small"
                  round
                  :bordered="false"
                  :type="personSourceType(tag.source)"
                >
                  {{ personTagLeaf(tag) }}
                </NTag>
              </div>
              <div class="mt-2 flex flex-wrap items-center gap-1">
                <span class="mr-1 text-[11px] text-amber-700">治安标签</span>
                <template v-if="personZjTags(person).length">
                  <NTag
                    v-for="tag in personZjTags(person)"
                    :key="`zj-${tag.tagPath}-${tag.tagCode || ''}`"
                    size="small"
                    round
                    :bordered="false"
                    type="warning"
                  >
                    {{ personTagLeaf(tag) }}
                  </NTag>
                </template>
                <span v-else class="text-[11px] text-slate-400">
                  {{
                    person.enrichStatus === '2'
                      ? '无命中'
                      : person.enrichStatus === '1'
                        ? '已补全(无明细)'
                        : '待补全'
                  }}
                </span>
              </div>
              <p v-if="personExtractTags(person).some((tag) => tag.evidence)" class="mt-2 space-y-1 text-xs text-slate-500">
                <span
                  v-for="tag in personExtractTags(person).filter((item) => item.evidence)"
                  :key="`${tag.tagPath}-evidence`"
                  class="block"
                >
                  {{ personTagLeaf(tag) }}：{{ maskCjqkText(tag.evidence, { personNames: detailPersonNames }) }}
                </span>
              </p>
            </div>
          </div>
        </section>
      </div>
    </NModal>
  </section>
</template>
