<script setup lang="ts">
import {
  getWarningSummary,
  listRepeatGroupDetails,
  listWarningIncidentCategories,
  listWarnings,
  type RepeatWarningRow,
  type SuspectWarningRow,
  type SuspectWarningSummary,
  type WarningCategoryNode,
  type WarningListRow,
  type WarningRuleType
} from '@/api/warning'
import { useAuthStore } from '@/stores/auth'
import {
  buildDeptTreeOptions,
  collectDeptScopeIds,
  collectExpandedKeys,
  type DeptOption,
} from '@/utils/deptTree'
import { getPageRows, getPageTotal, getResponseData } from '@/utils/page'
import {
  Building2,
  CalendarDays,
  CalendarRange,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  Search,
  ShieldAlert,
  TrendingUp,
  Users
} from 'lucide-vue-next'
import {
  NButton,
  NDatePicker,
  NDrawer,
  NDrawerContent,
  NIcon,
  NInput,
  NSelect,
  NSpin,
  NTag,
  NTreeSelect,
  useMessage
} from 'naive-ui'
import type { TreeOption } from 'naive-ui'
import { computed, nextTick, onMounted, reactive, ref, type Component } from 'vue'

const message = useMessage()
const authStore = useAuthStore()
const loading = ref(false)
const detailLoading = ref(false)
const loadingDepts = ref(false)
const hasSearched = ref(false)
const ruleType = ref<WarningRuleType>('dayRise')
const rows = ref<WarningListRow[]>([])
const detailRows = ref<Array<SuspectWarningRow | RepeatWarningRow>>([])
const selectedId = ref('')
const selectedDetailId = ref('')
const pageNum = ref(1)
const pageSize = ref(20)
const pageTotal = ref(0)
const categoryTree = ref<WarningCategoryNode[]>([])
const deptRows = ref<DeptOption[]>([])
const selectedDeptKey = ref<string | null>(null)
const expandedDeptKeys = ref<string[]>([])
const summary = ref<SuspectWarningSummary>({
  total: 0,
  pending: 0,
  handled: 0,
  ignored: 0,
  labels: []
})

const filters = reactive({
  keyword: '',
  ryxm: '',
  rysfz: '',
  dhhm: '',
  sdpcs: '',
  orgCode: '',
  orgName: '',
  jjdbh: '',
  ajlb: '',
  bjlb: null as string | null,
  bjlx: null as string | null,
  beginRq: '',
  endRq: ''
})

const detailPanelRef = ref<HTMLElement | null>(null)
const detailHighlight = ref(false)
const detailOpen = ref(false)

const scopedDeptRows = computed(() => {
  const accountDeptId = Number(authStore.deptId || 0)
  if (!accountDeptId) return deptRows.value
  const scopeIds = collectDeptScopeIds(deptRows.value, accountDeptId)
  if (!scopeIds) return deptRows.value
  return deptRows.value.filter((dept) => scopeIds.has(Number(dept.deptId || 0)))
})

const deptTreeOptions = computed<TreeOption[]>(() => buildDeptTreeOptions(scopedDeptRows.value))

const categoryOptions = computed(() =>
  categoryTree.value.map((item) => ({
    label: item.name || item.code,
    value: item.code
  }))
)

const typeOptions = computed(() => {
  const categoryCode = filters.bjlb
  if (!categoryCode) {
    return categoryTree.value.flatMap((category) =>
      (category.children || []).map((item) => ({
        label: item.name || item.code,
        value: item.code
      }))
    )
  }
  const category = categoryTree.value.find((item) => item.code === categoryCode)
  return (category?.children || []).map((item) => ({
    label: item.name || item.code,
    value: item.code
  }))
})

const ruleTabs: Array<{ key: WarningRuleType; label: string; desc: string; icon: Component }> = [
  { key: 'dayRise', label: '连续三天上升', desc: '主类连续三天环比上升', icon: TrendingUp },
  { key: 'weekRise', label: '连续两周上升', desc: '主类连续两周环比上升', icon: CalendarRange },
  { key: 'pcsDayHb30', label: '派出所按天环比30%', desc: '派出所主类按天环比超30%', icon: Building2 },
  { key: 'pcsWeekHb30', label: '派出所按周环比30%', desc: '派出所主类按周环比超30%', icon: Building2 },
  { key: 'pcsMonthHb30', label: '派出所按月环比30%', desc: '派出所主类按月环比超30%', icon: CalendarDays },
  { key: 'pcsMonthTb30', label: '派出所按月同比30%', desc: '派出所主类按月同比超30%', icon: CalendarDays },
  { key: 'suspect', label: '涉警前科', desc: '前科比对命中摘要与明细', icon: ShieldAlert },
  { key: 'repeat', label: '重复涉警', desc: '近一年重复涉警人员', icon: Users }
]

const activeRuleTab = computed(() => ruleTabs.find((tab) => tab.key === ruleType.value) || ruleTabs[0])

const DETAIL_LINK_TEXT = '点击查看详情'

const isDayRise = computed(() => ruleType.value === 'dayRise')
const isWeekRise = computed(() => ruleType.value === 'weekRise')
const isPcsDayHb30 = computed(() => ruleType.value === 'pcsDayHb30')
const isPcsWeekHb30 = computed(() => ruleType.value === 'pcsWeekHb30')
const isPcsMonthHb30 = computed(() => ruleType.value === 'pcsMonthHb30')
const isPcsMonthTb30 = computed(() => ruleType.value === 'pcsMonthTb30')
const isSuspect = computed(() => ruleType.value === 'suspect')
const isRepeat = computed(() => ruleType.value === 'repeat')
const isMxPcsRule = computed(
  () => isPcsDayHb30.value || isPcsWeekHb30.value || isPcsMonthHb30.value || isPcsMonthTb30.value
)
const isRiseRule = computed(() => isDayRise.value || isWeekRise.value || isMxPcsRule.value)
const isPersonRule = computed(() => isSuspect.value || isRepeat.value)

const ruleHint = computed(() => {
  if (isDayRise.value) return '主类连续三天环比上升输出'
  if (isWeekRise.value) return '主类连续两周环比上升输出'
  if (isPcsDayHb30.value) return '派出所主类按天环比上升超过30%'
  if (isPcsWeekHb30.value) return '派出所主类按周环比上升超过30%'
  if (isPcsMonthHb30.value) return '派出所主类按月环比上升超过30%'
  if (isPcsMonthTb30.value) return '派出所主类按月同比上升超过30%'
  if (isRepeat.value) return '近一年重复涉警人员摘要与明细'
  return '前科比对命中摘要与警情明细'
})

const sidebarTitle = computed(() => {
  if (isDayRise.value) return '连续三天上升'
  if (isWeekRise.value) return '连续两周上升'
  if (isPcsDayHb30.value) return '派出所按天环比30%'
  if (isPcsWeekHb30.value) return '派出所按周环比30%'
  if (isPcsMonthHb30.value) return '派出所按月环比30%'
  if (isPcsMonthTb30.value) return '派出所按月同比30%'
  if (isRepeat.value) return '重复涉警预警'
  return '涉警前科预警'
})

const mainTitle = computed(() => (isRiseRule.value ? '预警明细' : '摘要与命中明细'))
const mainDesc = computed(() => {
  if (isDayRise.value) return '展示连续三天上升结构化字段与文案'
  if (isWeekRise.value) return '展示连续两周上升结构化字段与文案'
  if (isPcsDayHb30.value) return '展示派出所按天环比上升30%字段与文案'
  if (isPcsWeekHb30.value) return '展示派出所按周环比上升30%字段与文案'
  if (isPcsMonthHb30.value) return '展示派出所按月环比上升30%字段与文案'
  if (isPcsMonthTb30.value) return '展示派出所按月同比上升30%字段与文案'
  if (isRepeat.value) return '先看人员摘要，再下钻重复涉警明细'
  return '命中警情明细文案与字段'
})

const rightTitle = computed(() => (isRiseRule.value ? '趋势摘要' : isRepeat.value ? '涉警详情' : '警情详情'))
const rightDesc = computed(() => {
  if (isDayRise.value) return '三日数量与环比对照'
  if (isWeekRise.value) return '两周数量与环比对照'
  if (isPcsDayHb30.value) return '当日与昨日数量及环比'
  if (isPcsWeekHb30.value) return '本周与上周数量及环比'
  if (isPcsMonthHb30.value) return '本月与上月数量及环比'
  if (isPcsMonthTb30.value) return '本月与去年同期数量及同比'
  if (isRepeat.value) return '选中人员明细后在此查看字段'
  return '选中命中警情后在此查看完整字段'
})

const personWarningLead = computed(() => {
  const text = String(selectedRow.value?.warningText || '')
  return text.replace(/，?点击查看详情。?$/, '')
})

const rqRange = computed<[string, string] | null>({
  get() {
    if (!filters.beginRq || !filters.endRq) return null
    return [filters.beginRq, filters.endRq]
  },
  set(value) {
    filters.beginRq = value?.[0] || ''
    filters.endRq = value?.[1] || ''
  }
})

const pageCount = computed(() => Math.max(1, Math.ceil(pageTotal.value / pageSize.value)))
const pageStart = computed(() => (pageTotal.value ? (pageNum.value - 1) * pageSize.value + 1 : 0))
const pageEnd = computed(() => Math.min(pageNum.value * pageSize.value, pageTotal.value))
const selectedRow = computed(() => {
  const key = selectedId.value
  return rows.value.find((item) => rowKey(item) === key) || null
})
const selectedDetail = computed(
  () => detailRows.value.find((item) => String(item.xlbh) === selectedDetailId.value) || null
)

const riseDetailFields = computed(() => {
  const row = selectedRow.value
  if (!row || !isRiseRule.value) return []
  if (isDayRise.value) {
    return [
      { label: '派出所', value: row.sdpcs || '-' },
      { label: '案件类别', value: row.ajlb || '-' },
      { label: '截止日期', value: row.rq || '-' },
      { label: '前日数量', value: formatCount(row.qrPcsjjzs) },
      { label: '前日环比', value: row.qrJqhb || '-' },
      { label: '昨日数量', value: formatCount(row.zrPcsjjzs) },
      { label: '昨日环比', value: row.zrJqhb || '-' },
      { label: '当日数量', value: formatCount(row.jjzs) },
      { label: '当日环比', value: row.drjqhb || '-' },
      { label: '统计批次', value: row.tjsj || '-' }
    ]
  }
  if (isWeekRise.value) {
    return [
      { label: '派出所', value: row.sdpcs || '-' },
      { label: '案件类别', value: row.ajlb || '-' },
      { label: '本周区间', value: `${row.weekStart || '-'} ~ ${row.weekEnd || '-'}` },
      { label: '上周数量', value: formatCount(row.szPcsjjzs) },
      { label: '上周环比', value: row.szJqhb || '-' },
      { label: '本周数量', value: formatCount(row.jjzs) },
      { label: '本周环比', value: row.dzjqhb || '-' },
      { label: '统计批次', value: row.tjsj || '-' }
    ]
  }
  if (isPcsDayHb30.value) {
    return [
      { label: '派出所', value: row.sdpcs || '-' },
      { label: '案件类别', value: row.ajlb || '-' },
      { label: '日期', value: row.rq || '-' },
      { label: '昨日数量', value: formatCount(row.zrPcsjjzs) },
      { label: '当日数量', value: formatCount(row.jjzs) },
      { label: '当日环比', value: row.drjqhb || '-' },
      { label: '统计批次', value: row.tjsj || '-' }
    ]
  }
  if (isPcsWeekHb30.value) {
    return [
      { label: '派出所', value: row.sdpcs || '-' },
      { label: '案件类别', value: row.ajlb || '-' },
      { label: '本周区间', value: `${row.weekStart || '-'} ~ ${row.weekEnd || '-'}` },
      { label: '上周数量', value: formatCount(row.szPcsjjzs) },
      { label: '本周数量', value: formatCount(row.jjzs) },
      { label: '本周环比', value: row.dzjqhb || '-' },
      { label: '统计批次', value: row.tjsj || '-' }
    ]
  }
  if (isPcsMonthHb30.value) {
    return [
      { label: '派出所', value: row.sdpcs || '-' },
      { label: '案件类别', value: row.ajlb || '-' },
      { label: '月份区间', value: `${row.monthStart || '-'} ~ ${row.monthEnd || '-'}` },
      { label: '上月数量', value: formatCount(row.syPcsjjzs) },
      { label: '本月数量', value: formatCount(row.jjzs) },
      { label: '本月环比', value: row.dyjqhb || '-' },
      { label: '统计批次', value: row.tjsj || '-' }
    ]
  }
  if (isPcsMonthTb30.value) {
    return [
      { label: '派出所', value: row.sdpcs || '-' },
      { label: '案件类别', value: row.ajlb || '-' },
      { label: '月份区间', value: `${row.monthStart || '-'} ~ ${row.monthEnd || '-'}` },
      { label: '去年同期', value: formatCount(row.syJjzs) },
      { label: '本月数量', value: formatCount(row.jjzs) },
      { label: '本月同比', value: row.dyjqtb || '-' },
      { label: '统计批次', value: row.tjsj || '-' }
    ]
  }
  return []
})

const suspectSummaryFields = computed(() => {
  const row = selectedRow.value
  if (!row || !isSuspect.value) return []
  return [
    { label: '派出所', value: row.sdpcs || '-' },
    { label: '报警时间', value: row.bjsj || row.rq || '-' },
    { label: '事发地址', value: row.alarmAddress || '-' },
    { label: '报警类别', value: row.bjlbmc || '-' },
    { label: '报警类型', value: row.bjlxmc || '-' },
    { label: '比对标签', value: row.tjwdbq || '-' },
    { label: '接警单号', value: row.jjdbh || '-' }
  ]
})

const repeatSummaryFields = computed(() => {
  const row = selectedRow.value
  if (!row || !isRepeat.value) return []
  return [
    { label: '人员姓名', value: row.ryxm || '-' },
    { label: '身份证号', value: row.rysfz || '-' },
    { label: '联系电话', value: row.dhhm || '-' },
    { label: '重复次数', value: formatCount(row.bjcs) },
    { label: '派出所', value: row.sdpcs || row.pcsmc || '-' },
    { label: '统计批次', value: row.tjsj || '-' }
  ]
})

const detailFields = computed(() => {
  const row = selectedDetail.value
  if (!row) return []
  if (isRepeat.value) {
    const repeat = row as RepeatWarningRow
    return [
      { label: '接警单号', value: repeat.jjdbh || '-' },
      { label: '人员姓名', value: repeat.ryxm || '-' },
      { label: '身份证号', value: repeat.rysfz || '-' },
      { label: '联系电话', value: repeat.dhhm || '-' },
      { label: '报警时间', value: repeat.bjsj || '-' },
      { label: '重复次数', value: formatCount(repeat.bjcs) },
      { label: '派出所', value: repeat.sdpcs || repeat.pcsmc || '-' },
      { label: '派出所代码', value: repeat.sdpcsdm || repeat.pcsdm || '-' },
      { label: '统计批次', value: repeat.tjsj || '-' }
    ]
  }
  const suspect = row as SuspectWarningRow
  return [
    { label: '接警单号', value: suspect.jjdbh || '-' },
    { label: '报警人', value: suspect.alarmTitle || suspect.ryxm || '-' },
    { label: '身份证号', value: suspect.rysfz || '-' },
    { label: '报警电话', value: suspect.alarmPhone || '-' },
    { label: '报警时间', value: suspect.bjsj || '-' },
    { label: '报警类别', value: suspect.alarmCategory || '-' },
    { label: '事发地址', value: suspect.alarmAddress || '-' },
    { label: '属地派出所', value: suspect.sdpcs || '-' },
    { label: '比对标签', value: suspect.tjwdbq || '-' },
    { label: '接警碰撞', value: suspect.jjdMatched ? '已命中 jjd_jjd' : '未命中接警单' }
  ]
})

const trendBars = computed(() => {
  const row = selectedRow.value
  if (!row || !isRiseRule.value) return []
  if (isDayRise.value) {
    const values = [Number(row.qrPcsjjzs || 0), Number(row.zrPcsjjzs || 0), Number(row.jjzs || 0)]
    const max = Math.max(...values, 1)
    return [
      { label: '前日', count: values[0], ratio: row.qrJqhb || '-', width: `${(values[0] / max) * 100}%` },
      { label: '昨日', count: values[1], ratio: row.zrJqhb || '-', width: `${(values[1] / max) * 100}%` },
      { label: '当日', count: values[2], ratio: row.drjqhb || '-', width: `${(values[2] / max) * 100}%` }
    ]
  }
  if (isWeekRise.value || isPcsWeekHb30.value) {
    const values = [Number(row.szPcsjjzs || 0), Number(row.jjzs || 0)]
    const max = Math.max(...values, 1)
    return [
      { label: '上周', count: values[0], ratio: row.szJqhb || '-', width: `${(values[0] / max) * 100}%` },
      { label: '本周', count: values[1], ratio: row.dzjqhb || '-', width: `${(values[1] / max) * 100}%` }
    ]
  }
  if (isPcsDayHb30.value) {
    const values = [Number(row.zrPcsjjzs || 0), Number(row.jjzs || 0)]
    const max = Math.max(...values, 1)
    return [
      { label: '昨日', count: values[0], ratio: '-', width: `${(values[0] / max) * 100}%` },
      { label: '当日', count: values[1], ratio: row.drjqhb || '-', width: `${(values[1] / max) * 100}%` }
    ]
  }
  if (isPcsMonthHb30.value) {
    const values = [Number(row.syPcsjjzs || 0), Number(row.jjzs || 0)]
    const max = Math.max(...values, 1)
    return [
      { label: '上月', count: values[0], ratio: '-', width: `${(values[0] / max) * 100}%` },
      { label: '本月', count: values[1], ratio: row.dyjqhb || '-', width: `${(values[1] / max) * 100}%` }
    ]
  }
  if (isPcsMonthTb30.value) {
    const values = [Number(row.syJjzs || 0), Number(row.jjzs || 0)]
    const max = Math.max(...values, 1)
    return [
      { label: '去年同期', count: values[0], ratio: '-', width: `${(values[0] / max) * 100}%` },
      { label: '本月', count: values[1], ratio: row.dyjqtb || '-', width: `${(values[1] / max) * 100}%` }
    ]
  }
  return []
})

function rowKey(row: WarningListRow) {
  if (isPersonRule.value && row.groupKey) return row.groupKey
  return String(row.xlbh)
}

function formatCount(value?: number | null) {
  if (value === null || value === undefined) return '-'
  return String(value)
}

function rowCardStats(row: WarningListRow) {
  if (isDayRise.value) {
    return [
      { label: '前日', value: `${formatCount(row.qrPcsjjzs)} / ${row.qrJqhb || '-'}` },
      { label: '昨日', value: `${formatCount(row.zrPcsjjzs)} / ${row.zrJqhb || '-'}` },
      { label: '当日', value: `${formatCount(row.jjzs)} / ${row.drjqhb || '-'}` }
    ]
  }
  if (isWeekRise.value) {
    return [
      { label: '上周', value: `${formatCount(row.szPcsjjzs)} / ${row.szJqhb || '-'}` },
      { label: '本周', value: `${formatCount(row.jjzs)} / ${row.dzjqhb || '-'}` }
    ]
  }
  if (isPcsDayHb30.value) {
    return [
      { label: '昨日', value: formatCount(row.zrPcsjjzs) },
      { label: '当日', value: `${formatCount(row.jjzs)} / ${row.drjqhb || '-'}` }
    ]
  }
  if (isPcsWeekHb30.value) {
    return [
      { label: '上周', value: formatCount(row.szPcsjjzs) },
      { label: '本周', value: `${formatCount(row.jjzs)} / ${row.dzjqhb || '-'}` }
    ]
  }
  if (isPcsMonthHb30.value) {
    return [
      { label: '上月', value: formatCount(row.syPcsjjzs) },
      { label: '本月', value: `${formatCount(row.jjzs)} / ${row.dyjqhb || '-'}` }
    ]
  }
  if (isPcsMonthTb30.value) {
    return [
      { label: '去年同期', value: formatCount(row.syJjzs) },
      { label: '本月', value: `${formatCount(row.jjzs)} / ${row.dyjqtb || '-'}` }
    ]
  }
  if (isRepeat.value) {
    const stats = [{ label: '重复次数', value: formatCount(row.bjcs) }]
    if (row.alarmCount) stats.unshift({ label: '关联警情', value: `${row.alarmCount} 起` })
    return stats
  }
  return []
}


function splitTags(text?: string | null) {
  return String(text || '')
    .split(/[;；]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function findAccountDept() {
  const accountDeptId = String(authStore.deptId || '')
  const accountDeptCode = String(authStore.deptCode || '').trim()
  const accountDeptName = String(authStore.deptName || '').trim()
  if (accountDeptId) {
    const byId = scopedDeptRows.value.find((item) => String(item.deptId || '') === accountDeptId)
    if (byId) return byId
  }
  if (accountDeptCode) {
    const byCode = scopedDeptRows.value.find(
      (item) => String(item.deptCode || '').trim() === accountDeptCode
    )
    if (byCode) return byCode
  }
  if (accountDeptName) {
    return scopedDeptRows.value.find((item) => String(item.deptName || '').trim() === accountDeptName) || null
  }
  return null
}

function applyDeptSelection(dept: DeptOption | null | undefined) {
  if (!dept) {
    if (!authStore.isCityBureau) {
      const accountDept = findAccountDept()
      if (accountDept) {
        selectedDeptKey.value = String(accountDept.deptId || '')
        filters.orgCode = String(accountDept.deptCode || accountDept.deptId || '').trim()
        filters.orgName = String(accountDept.deptName || '').trim()
        return
      }
      filters.orgCode = String(authStore.deptCode || '').trim()
      filters.orgName = String(authStore.deptName || '').trim()
      return
    }
    selectedDeptKey.value = null
    filters.orgCode = ''
    filters.orgName = ''
    return
  }
  selectedDeptKey.value = String(dept.deptId || '')
  filters.orgCode = String(dept.deptCode || dept.deptId || '').trim()
  filters.orgName = String(dept.deptName || '').trim()
}

function applyAccountDeptDefault() {
  applyDeptSelection(findAccountDept())
}

function ensureAccountDeptScope() {
  if (authStore.isCityBureau) return
  applyAccountDeptDefault()
  if (!filters.orgCode && authStore.deptCode) {
    filters.orgCode = String(authStore.deptCode).trim()
  }
  if (!filters.orgName && authStore.deptName) {
    filters.orgName = String(authStore.deptName).trim()
  }
}

function updateDept(key: string | null) {
  if (!key) {
    applyDeptSelection(null)
    return
  }
  const dept = scopedDeptRows.value.find((item) => String(item.deptId || '') === String(key))
  applyDeptSelection(dept || null)
}

async function loadDepts() {
  loadingDepts.value = true
  try {
    if (!authStore.deptId && authStore.token) {
      await authStore.loadUserInfo()
    }
    deptRows.value = await authStore.listScopedDeptOptions()
    expandedDeptKeys.value = collectExpandedKeys(deptTreeOptions.value).slice(0, 12)
    const keyValid =
      Boolean(selectedDeptKey.value) &&
      scopedDeptRows.value.some((item) => String(item.deptId || '') === selectedDeptKey.value)
    if (!authStore.isCityBureau || !keyValid) {
      applyAccountDeptDefault()
    } else {
      updateDept(selectedDeptKey.value)
    }
  } catch (error) {
    deptRows.value = []
    message.error(error instanceof Error ? error.message : '部门列表加载失败')
  } finally {
    loadingDepts.value = false
  }
}

async function loadMeta() {
  try {
    const tasks: Promise<unknown>[] = [getWarningSummary(ruleType.value)]
    if (isSuspect.value && !categoryTree.value.length) {
      tasks.push(listWarningIncidentCategories())
    }
    const [summaryRes, categoriesRes] = await Promise.all(tasks)
    summary.value = getResponseData(summaryRes as Awaited<ReturnType<typeof getWarningSummary>>) || summary.value
    if (categoriesRes) {
      const tree =
        getResponseData(categoriesRes as Awaited<ReturnType<typeof listWarningIncidentCategories>>) || []
      categoryTree.value = Array.isArray(tree) ? tree : []
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '预警汇总加载失败')
  }
}

function onCategoryChange(value: string | null) {
  filters.bjlb = value
  if (!value) {
    filters.bjlx = null
    return
  }
  if (filters.bjlx && !typeOptions.value.some((item) => item.value === filters.bjlx)) {
    filters.bjlx = null
  }
}

async function loadSuspectDetails(row: WarningListRow) {
  detailLoading.value = false
  detailRows.value = [row as SuspectWarningRow]
  selectedDetailId.value = String(row.xlbh || '')
}

async function loadRepeatDetails(row: WarningListRow) {
  detailLoading.value = true
  try {
    const response = await listRepeatGroupDetails({
      rysfz: row.rysfz || undefined,
      ryxm: row.rysfz ? undefined : row.ryxm || undefined,
      dhhm: row.rysfz ? undefined : row.dhhm || undefined,
      pageNum: 1,
      pageSize: 200
    })
    detailRows.value = getPageRows(response)
    selectedDetailId.value = detailRows.value[0] ? String(detailRows.value[0].xlbh) : ''
  } catch (error) {
    detailRows.value = []
    selectedDetailId.value = ''
    message.error(error instanceof Error ? error.message : '明细加载失败')
  } finally {
    detailLoading.value = false
  }
}

async function loadPersonDetails(row: WarningListRow) {
  if (isSuspect.value) await loadSuspectDetails(row)
  else if (isRepeat.value) await loadRepeatDetails(row)
}

async function runSearch(resetPage = false) {
  ensureAccountDeptScope()
  if (resetPage) pageNum.value = 1
  loading.value = true
  hasSearched.value = true
  try {
    const response = await listWarnings({
      ruleType: ruleType.value,
      pageNum: pageNum.value,
      pageSize: pageSize.value,
      keyword: isSuspect.value ? undefined : filters.keyword.trim() || undefined,
      ryxm: isRepeat.value ? filters.ryxm.trim() || undefined : undefined,
      rysfz: isRepeat.value ? filters.rysfz.trim() || undefined : undefined,
      dhhm: isRepeat.value ? filters.dhhm.trim() || undefined : undefined,
      sdpcs: isSuspect.value ? undefined : filters.sdpcs.trim() || undefined,
      orgCode: filters.orgCode.trim() || undefined,
      orgName: filters.orgName.trim() || undefined,
      jjdbh: undefined,
      ajlb: isRiseRule.value ? filters.ajlb.trim() || undefined : undefined,
      bjlb: isSuspect.value ? filters.bjlb || undefined : undefined,
      bjlx: isSuspect.value ? filters.bjlx || undefined : undefined,
      beginRq: filters.beginRq || undefined,
      endRq: filters.endRq || undefined,
      viewMode: isSuspect.value ? 'detail' : isRepeat.value ? 'summary' : undefined
    })
    rows.value = getPageRows(response)
    pageTotal.value = getPageTotal(response)
    if (!rows.value.some((item) => rowKey(item) === selectedId.value)) {
      selectedId.value = rows.value[0] ? rowKey(rows.value[0]) : ''
    }
    const current =
      rows.value.find((item) => rowKey(item) === selectedId.value) || selectedRow.value
    if (isPersonRule.value && current) {
      await loadPersonDetails(current)
    } else {
      detailRows.value = []
      selectedDetailId.value = ''
    }
    await loadMeta()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '预警查询失败')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.ryxm = ''
  filters.rysfz = ''
  filters.dhhm = ''
  filters.sdpcs = ''
  filters.jjdbh = ''
  filters.ajlb = ''
  filters.bjlb = null
  filters.bjlx = null
  filters.beginRq = ''
  filters.endRq = ''
  applyAccountDeptDefault()
  runSearch(true)
}

function changePage(next: number) {
  if (next < 1 || next > pageCount.value || next === pageNum.value) return
  pageNum.value = next
  runSearch()
}

async function selectRow(row: WarningListRow) {
  selectedId.value = rowKey(row)
  if (isPersonRule.value) await loadPersonDetails(row)
  detailOpen.value = true
}

function selectDetail(row: SuspectWarningRow | RepeatWarningRow) {
  selectedDetailId.value = String(row.xlbh)
}

async function openPersonDetails() {
  const row = selectedRow.value
  if (!row || !isPersonRule.value) return
  if (!detailRows.value.length) {
    await loadPersonDetails(row)
  }
  await nextTick()
  detailPanelRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  detailHighlight.value = true
  window.setTimeout(() => {
    detailHighlight.value = false
  }, 1600)
  if (detailRows.value[0] && !selectedDetailId.value) {
    selectDetail(detailRows.value[0])
  }
}

async function switchRule(next: WarningRuleType) {
  if (ruleType.value === next) return
  ruleType.value = next
  selectedId.value = ''
  selectedDetailId.value = ''
  detailRows.value = []
  rows.value = []
  detailOpen.value = false
  applyAccountDeptDefault()
  await runSearch(true)
}

onMounted(async () => {
  await loadDepts()
  await loadMeta()
  await runSearch(true)
})
</script>

<template>
  <section class="flex h-full min-h-0 flex-col gap-3 overflow-hidden p-3 text-sm leading-6">
    <div class="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-hidden xl:grid-cols-[240px_minmax(0,1fr)]">
      <aside class="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-white/80 bg-white/80 shadow-xl shadow-amber-200/20 backdrop-blur-2xl ring-1 ring-white/80">
        <div class="border-b border-slate-100 px-4 py-3">
          <h2 class="text-sm font-semibold text-slate-900">预警规则</h2>
          <p class="mt-0.5 text-xs text-slate-500">选择规则查看对应预警</p>
        </div>
        <div class="min-h-0 flex-1 space-y-2 overflow-auto p-2">
          <button
            v-for="tab in ruleTabs"
            :key="tab.key"
            type="button"
            class="group flex w-full items-start gap-3 rounded-xl border px-3 py-3 text-left transition"
            :class="
              ruleType === tab.key
                ? 'border-amber-300 bg-amber-50/90 shadow-sm ring-1 ring-amber-200/60'
                : 'border-slate-100 bg-white hover:border-amber-200 hover:bg-amber-50/40'
            "
            @click="switchRule(tab.key)"
          >
            <span
              class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition"
              :class="
                ruleType === tab.key
                  ? 'bg-amber-500 text-white'
                  : 'bg-slate-100 text-slate-500 group-hover:bg-amber-100 group-hover:text-amber-700'
              "
            >
              <component :is="tab.icon" :size="16" />
            </span>
            <span class="min-w-0 flex-1">
              <span
                class="block text-[13px] font-semibold leading-5"
                :class="ruleType === tab.key ? 'text-amber-950' : 'text-slate-800'"
              >
                {{ tab.label }}
              </span>
              <span class="mt-0.5 block text-[11px] leading-4 text-slate-500">{{ tab.desc }}</span>
            </span>
          </button>
        </div>
      </aside>

      <div class="flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-hidden">
        <div class="shrink-0 rounded-2xl border border-white/80 bg-white/80 px-4 py-3 shadow-xl shadow-amber-200/20 backdrop-blur-2xl ring-1 ring-white/80">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex min-w-0 items-center gap-2">
              <component :is="activeRuleTab.icon" :size="16" class="shrink-0 text-amber-600" />
              <div class="min-w-0">
                <h2 class="text-sm font-semibold text-slate-900">{{ sidebarTitle }}</h2>
                <p class="text-xs text-slate-500">{{ ruleHint }}</p>
              </div>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <div class="rounded-lg bg-amber-50 px-2.5 py-1.5">
                <span class="text-[11px] text-amber-700">{{ isRepeat ? '人员数' : '预警条数' }}</span>
                <span class="ml-1.5 text-sm font-semibold tabular-nums text-amber-800">{{ summary.total }}</span>
              </div>
              <div class="rounded-lg bg-slate-50 px-2.5 py-1.5">
                <span class="text-[11px] text-slate-500">
                  {{ isRiseRule ? '类别数' : isRepeat ? '明细行' : '标签数' }}
                </span>
                <span class="ml-1.5 text-sm font-semibold tabular-nums text-slate-800">
                  {{ isRepeat ? summary.labels[0]?.count || 0 : summary.labels.length }}
                </span>
              </div>
              <div
                v-if="!isRepeat && summary.labels.length"
                class="hidden max-w-xs truncate rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600 lg:block"
                :title="summary.labels.slice(0, 5).map((item) => `${item.label} ${item.count}`).join(' · ')"
              >
                {{ summary.labels.slice(0, 3).map((item) => `${item.label} ${item.count}`).join(' · ') }}
              </div>
            </div>
          </div>

          <div class="mt-3 flex flex-nowrap items-center gap-2 overflow-x-auto pb-0.5">
            <div class="w-[180px] shrink-0">
              <NTreeSelect
                class="w-full"
              :value="selectedDeptKey"
              :options="deptTreeOptions"
              :loading="loadingDepts"
              :default-expanded-keys="expandedDeptKeys"
              :clearable="authStore.isCityBureau"
              filterable
              size="small"
              :placeholder="authStore.isCityBureau ? '部门（市局可查全部）' : '部门（仅本部门）'"
              key-field="key"
              label-field="label"
                @update:value="updateDept"
              />
            </div>
            <template v-if="isSuspect">
              <NSelect
                class="w-[130px] shrink-0"
                size="small"
                :value="filters.bjlb"
                clearable
                filterable
                :options="categoryOptions"
                placeholder="报警类别"
                @update:value="onCategoryChange"
              />
              <NSelect
                v-model:value="filters.bjlx"
                class="w-[130px] shrink-0"
                size="small"
                clearable
                filterable
                :options="typeOptions"
                placeholder="报警类型"
              />
              <NDatePicker
                v-model:formatted-value="rqRange"
                class="w-[220px] shrink-0"
                size="small"
                type="daterange"
                clearable
                value-format="yyyy-MM-dd"
                start-placeholder="时间起"
                end-placeholder="时间止"
              />
            </template>
            <template v-else>
              <div class="w-[160px] shrink-0">
                <NInput
                  v-model:value="filters.keyword"
                  class="w-full"
                  size="small"
                  clearable
                  placeholder="综合关键词"
                  @keyup.enter="runSearch(true)"
                />
              </div>
              <div class="w-[140px] shrink-0">
                <NInput
                  v-model:value="filters.sdpcs"
                  class="w-full"
                  size="small"
                  clearable
                  placeholder="派出所名称"
                  @keyup.enter="runSearch(true)"
                />
              </div>
              <div v-if="isRiseRule" class="w-[120px] shrink-0">
                <NInput
                  v-model:value="filters.ajlb"
                  class="w-full"
                  size="small"
                  clearable
                  placeholder="案件类别"
                  @keyup.enter="runSearch(true)"
                />
              </div>
              <template v-if="isRepeat">
                <div class="w-[100px] shrink-0">
                  <NInput
                    v-model:value="filters.ryxm"
                    class="w-full"
                    size="small"
                    clearable
                    placeholder="人员姓名"
                    @keyup.enter="runSearch(true)"
                  />
                </div>
                <div class="w-[160px] shrink-0">
                  <NInput
                    v-model:value="filters.rysfz"
                    class="w-full"
                    size="small"
                    clearable
                    placeholder="身份证号"
                    @keyup.enter="runSearch(true)"
                  />
                </div>
                <div class="w-[120px] shrink-0">
                  <NInput
                    v-model:value="filters.dhhm"
                    class="w-full"
                    size="small"
                    clearable
                    placeholder="联系电话"
                    @keyup.enter="runSearch(true)"
                  />
                </div>
              </template>
              <NDatePicker
                v-model:formatted-value="rqRange"
                class="w-[220px] shrink-0"
                size="small"
                type="daterange"
                clearable
                value-format="yyyy-MM-dd"
                start-placeholder="日期起"
                end-placeholder="日期止"
              />
            </template>
            <NButton type="primary" size="small" class="shrink-0" :loading="loading" @click="() => runSearch(true)">
              <template #icon><NIcon :component="Search" :size="14" /></template>
              查询
            </NButton>
            <NButton secondary size="small" class="shrink-0" :disabled="loading" @click="resetFilters">
              <template #icon><NIcon :component="RotateCcw" :size="14" /></template>
              重置
            </NButton>
          </div>
        </div>

        <div class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-white/80 bg-white/80 shadow-xl shadow-amber-200/20 backdrop-blur-2xl ring-1 ring-white/80">
          <div class="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
            <div>
              <h2 class="text-sm font-semibold text-slate-900">预警列表</h2>
              <p class="text-xs text-slate-500">点击卡片查看预警明细</p>
            </div>
            <div class="flex items-center gap-2 text-xs text-slate-500">
              <span>{{ pageStart }}-{{ pageEnd }} / {{ pageTotal }}</span>
              <NButton size="tiny" quaternary circle :disabled="pageNum <= 1" @click="changePage(pageNum - 1)">
                <template #icon><NIcon :component="ChevronLeft" :size="14" /></template>
              </NButton>
              <span class="min-w-12 text-center tabular-nums">{{ pageNum }} / {{ pageCount }}</span>
              <NButton
                size="tiny"
                quaternary
                circle
                :disabled="pageNum >= pageCount"
                @click="changePage(pageNum + 1)"
              >
                <template #icon><NIcon :component="ChevronRight" :size="14" /></template>
              </NButton>
            </div>
          </div>

          <div class="min-h-0 flex-1 overflow-auto p-3">
            <NSpin :show="loading">
              <div v-if="!hasSearched" class="px-3 py-16 text-center text-slate-400">请设置条件后查询</div>
              <div v-else-if="!rows.length" class="px-3 py-16 text-center text-slate-400">暂无预警数据</div>
              <div v-else class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                <button
                  v-for="row in rows"
                  :key="rowKey(row)"
                  type="button"
                  class="rounded-xl border px-3.5 py-3 text-left transition"
                  :class="
                    selectedId === rowKey(row)
                      ? 'border-amber-300 bg-amber-50/80 shadow-sm ring-1 ring-amber-200/50'
                      : 'border-slate-100 bg-white hover:border-amber-200 hover:bg-amber-50/40'
                  "
                  @click="selectRow(row)"
                >
                  <div class="line-clamp-3 text-[13px] font-medium leading-5 text-slate-900">
                    {{
                      row.warningText ||
                      `${row.sdpcs || row.ryxm || '-'} ${row.ajlb || row.tjwdbq || row.bjcs || ''}`
                    }}
                  </div>
                  <div
                    v-if="rowCardStats(row).length"
                    class="mt-2.5 grid gap-1.5"
                    :class="isDayRise ? 'grid-cols-3' : 'grid-cols-2'"
                  >
                    <div
                      v-for="stat in rowCardStats(row)"
                      :key="stat.label"
                      class="rounded-lg bg-slate-50 px-2 py-1.5 ring-1 ring-slate-100"
                    >
                      <div class="text-[10px] leading-none text-slate-400">{{ stat.label }}</div>
                      <div class="mt-1 truncate text-xs font-semibold tabular-nums text-slate-800">
                        {{ stat.value }}
                      </div>
                    </div>
                  </div>
                  <div class="mt-2 flex flex-wrap items-center gap-1">
                    <NTag v-if="row.ajlb" size="tiny" type="warning" :bordered="false">{{ row.ajlb }}</NTag>
                    <NTag v-if="row.tjwdbq && !isRiseRule" size="tiny" type="error" :bordered="false">
                      {{ row.tjwdbq }}
                    </NTag>
                    <NTag v-if="isRepeat && row.dhhm" size="tiny" :bordered="false">{{ row.dhhm }}</NTag>
                    <span class="text-[11px] text-slate-400">
                      {{ row.monthEnd || row.weekEnd || row.rq || row.bjsj || row.rysfz || '-' }}
                    </span>
                  </div>
                </button>
              </div>
            </NSpin>
          </div>
        </div>
      </div>
    </div>

    <NDrawer v-model:show="detailOpen" :width="560" placement="right">
      <NDrawerContent :title="mainTitle" closable :native-scrollbar="false">
        <p class="mb-3 text-xs text-slate-500">{{ mainDesc }}</p>
        <div v-if="!selectedRow" class="py-10 text-center text-slate-400">请选择预警记录</div>
        <div v-else class="space-y-4">
          <div class="rounded-xl border border-amber-100 bg-amber-50/60 px-3 py-3 text-sm text-amber-950">
            <template v-if="isPersonRule">
              <span>{{ personWarningLead }}，</span>
              <button
                type="button"
                class="inline font-semibold text-amber-700 underline decoration-amber-400 underline-offset-2 transition hover:text-amber-900"
                @click="openPersonDetails"
              >
                {{ DETAIL_LINK_TEXT }}
              </button>
              <span>。</span>
            </template>
            <template v-else>{{ selectedRow.warningText }}</template>
          </div>

          <div v-if="isRiseRule" class="grid gap-3 sm:grid-cols-2">
            <div
              v-for="field in riseDetailFields"
              :key="field.label"
              class="rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2"
            >
              <div class="text-[11px] text-slate-500">{{ field.label }}</div>
              <div class="mt-0.5 break-all text-slate-800">{{ field.value }}</div>
            </div>
          </div>

          <div v-if="isRiseRule && trendBars.length" class="space-y-3">
            <div class="text-xs font-medium text-slate-700">趋势摘要</div>
            <div
              v-for="bar in trendBars"
              :key="bar.label"
              class="rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-3"
            >
              <div class="mb-2 flex items-center justify-between text-xs">
                <span class="font-medium text-slate-700">{{ bar.label }}</span>
                <span class="tabular-nums text-slate-500">{{ bar.count }} 起 · {{ bar.ratio }}</span>
              </div>
              <div class="h-2 overflow-hidden rounded-full bg-slate-200">
                <div class="h-full rounded-full bg-amber-500 transition-all" :style="{ width: bar.width }" />
              </div>
            </div>
          </div>

          <template v-if="isPersonRule">
            <div class="grid gap-3 sm:grid-cols-2">
              <div
                v-for="field in isRepeat ? repeatSummaryFields : suspectSummaryFields"
                :key="field.label"
                class="rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2"
              >
                <div class="text-[11px] text-slate-500">{{ field.label }}</div>
                <div class="mt-0.5 break-all text-slate-800">{{ field.value }}</div>
              </div>
            </div>

            <NSpin :show="detailLoading">
              <div
                ref="detailPanelRef"
                class="rounded-xl border bg-white px-3 py-3 transition"
                :class="detailHighlight ? 'border-amber-400 ring-2 ring-amber-200' : 'border-slate-100'"
              >
                <div class="mb-2 flex items-center justify-between gap-2">
                  <div class="text-xs font-medium text-slate-700">
                    {{ isRepeat ? '涉警明细' : '命中警情' }}
                  </div>
                  <div class="text-[11px] text-slate-400">
                    {{ isRepeat ? '按人员聚合后下钻全部明细行' : '按 jjdbh 碰撞 jjd_jjd，已去重' }}
                  </div>
                </div>
                <div v-if="!detailRows.length" class="py-6 text-center text-slate-400">暂无明细</div>
                <button
                  v-for="item in detailRows"
                  :key="item.xlbh"
                  type="button"
                  class="mb-2 w-full rounded-lg border px-3 py-2 text-left transition"
                  :class="
                    selectedDetailId === String(item.xlbh)
                      ? 'border-amber-300 bg-amber-50/70'
                      : 'border-slate-100 hover:border-amber-200'
                  "
                  @click="selectDetail(item)"
                >
                  <div class="flex items-start justify-between gap-2">
                    <div class="min-w-0">
                      <div class="truncate font-medium text-slate-900">
                        {{
                          isRepeat
                            ? item.ryxm || '未登记姓名'
                            : (item as SuspectWarningRow).alarmTitle || item.ryxm || '未登记姓名'
                        }}
                        <span class="ml-1 text-xs font-normal text-slate-500">{{ item.jjdbh || '-' }}</span>
                      </div>
                      <div class="mt-1 truncate text-xs text-slate-500">
                        {{ item.bjsj || '-' }}
                        <span v-if="!isRepeat && (item as SuspectWarningRow).alarmCategory">
                          · {{ (item as SuspectWarningRow).alarmCategory }}
                        </span>
                        <span v-if="isRepeat && (item as RepeatWarningRow).bjcs">
                          · {{ (item as RepeatWarningRow).bjcs }} 次
                        </span>
                      </div>
                    </div>
                    <NTag v-if="isRepeat" size="tiny" type="error" :bordered="false">
                      {{ (item as RepeatWarningRow).bjcs ?? '-' }} 次
                    </NTag>
                    <NTag
                      v-else
                      size="tiny"
                      :type="(item as SuspectWarningRow).jjdMatched ? 'success' : 'warning'"
                      :bordered="false"
                    >
                      {{ (item as SuspectWarningRow).jjdMatched ? '已碰撞' : '未碰撞' }}
                    </NTag>
                  </div>
                </button>
              </div>
            </NSpin>

            <div v-if="selectedDetail" class="space-y-3">
              <div class="text-xs font-medium text-slate-700">
                {{ isRepeat ? '涉警详情' : '警情详情' }}
              </div>
              <div class="grid gap-2 sm:grid-cols-2">
                <div
                  v-for="field in detailFields"
                  :key="field.label"
                  class="rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2"
                  :class="field.label === '事发地址' || field.label === '报警内容' ? 'sm:col-span-2' : ''"
                >
                  <div class="text-[11px] text-slate-500">{{ field.label }}</div>
                  <div class="mt-0.5 break-all text-slate-800">{{ field.value }}</div>
                </div>
              </div>
              <div
                v-if="!isRepeat && (selectedDetail as SuspectWarningRow).alarmContent"
                class="rounded-xl border border-slate-100 bg-white px-3 py-3"
              >
                <div class="text-xs font-medium text-slate-700">报警内容</div>
                <div class="mt-2 whitespace-pre-wrap text-slate-700">
                  {{ (selectedDetail as SuspectWarningRow).alarmContent }}
                </div>
              </div>
              <div v-if="isSuspect" class="rounded-xl border border-slate-100 bg-white px-3 py-3">
                <div class="text-xs font-medium text-slate-700">特殊人员 / 案由标签</div>
                <div
                  v-if="splitTags((selectedDetail as SuspectWarningRow).tsrybq).length"
                  class="mt-2 flex flex-wrap gap-1.5"
                >
                  <NTag
                    v-for="(tag, index) in splitTags((selectedDetail as SuspectWarningRow).tsrybq)"
                    :key="`${tag}-${index}`"
                    size="small"
                    :bordered="false"
                    type="error"
                    class="!max-w-full whitespace-normal !h-auto !py-1"
                  >
                    {{ tag }}
                  </NTag>
                </div>
                <div v-else class="mt-2 text-slate-400">暂无</div>
              </div>
            </div>
          </template>
        </div>
      </NDrawerContent>
    </NDrawer>
  </section>
</template>
