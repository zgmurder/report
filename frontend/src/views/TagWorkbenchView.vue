<script setup lang="ts">
import {
  deleteTagPackage,
  exportTags,
  extractPeopleFromAlarmRow,
  extractTagsFromAlarmRow,
  listTagCatalog,
  listTagPackages,
  saveTagPackage,
  searchTags,
  updateTagPackage,
  type JudgmentPackage,
  type SelectedSmartTag,
  type SmartTag,
  type TagAlarmRow
} from '@/api/tag'
import AlarmDetailModal from '@/components/tag/AlarmDetailModal.vue'
import {
  persistDateRangeShortcut,
  readReportDateRange,
  syncTimeToReportCache,
  type DateRangeShortcutKey
} from '@/utils/reportDateRange'
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  FilePenLine,
  Filter,
  MinusCircle,
  PackagePlus,
  Play,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  X
} from 'lucide-vue-next'
import {
  NButton,
  NCheckbox,
  NDatePicker,
  NDropdown,
  NIcon,
  NInput,
  NModal,
  NSelect,
  NSpin,
  NSwitch,
  NTag,
  useDialog,
  useMessage
} from 'naive-ui'
import type { DropdownOption } from 'naive-ui'
import { computed, h, reactive, ref, watch } from 'vue'

type SortKey = 'policeStation' | 'incidentCount' | 'bjsj'

const message = useMessage()
const dialog = useDialog()
const smartTags = ref<SmartTag[]>([])
const smartTagCategories = ref<string[]>(['全部'])
const matchedRows = ref<TagAlarmRow[]>([])
const resultSummary = reactive({ people: 0, incidents: 0, stations: 0 })
const selectedTags = ref<SelectedSmartTag[]>([])
const packages = ref<JudgmentPackage[]>([])
const selectedPackageId = ref('')
const packageKeyword = ref('')
const tagKeyword = ref('')
const activeCategory = ref('全部')
const excludeMode = ref(false)
const hasSearched = ref(false)
const loadingCatalog = ref(false)
const loadingPackages = ref(false)
const searching = ref(false)
const exporting = ref(false)
const selectedRowIds = ref<string[]>([])
const sortKey = ref<SortKey>('bjsj')
const sortAsc = ref(false)
const pageNum = ref(1)
const pageSize = ref(10)
const pageTotal = ref(0)
const beginTime = ref('')
const endTime = ref('')
const selectedDateRangeShortcut = ref<DateRangeShortcutKey | ''>('')
const saveModalVisible = ref(false)
const editingPackageId = ref('')
const packageForm = reactive({ name: '', remark: '' })
const detailModalVisible = ref(false)
const detailRow = ref<TagAlarmRow | null>(null)

function setTimeRange(start: string, end: string, shortcut: DateRangeShortcutKey | '' = '') {
  beginTime.value = start
  endTime.value = end
  selectedDateRangeShortcut.value = shortcut
  persistDateRangeShortcut(shortcut)
  syncTimeToReportCache(start, end)
}

function applyTimeFromReportCache() {
  const range = readReportDateRange()
  if (range.beginTime && range.endTime) {
    setTimeRange(range.beginTime, range.endTime, range.shortcut)
  }
}

const alarmTimeRange = computed<[string, string] | null>({
  get() {
    if (!beginTime.value || !endTime.value) return null
    return [beginTime.value, endTime.value]
  },
  set(value) {
    setTimeRange(value?.[0] || '', value?.[1] || '', '')
  }
})

applyTimeFromReportCache()

const sortOptions = [
  { label: '报警时间', value: 'bjsj' },
  { label: '反馈单位', value: 'policeStation' },
  { label: '标签数量', value: 'incidentCount' }
]

const pageCount = computed(() => Math.max(1, Math.ceil(pageTotal.value / pageSize.value)))
const pageStart = computed(() => (pageTotal.value ? (pageNum.value - 1) * pageSize.value + 1 : 0))
const pageEnd = computed(() => Math.min(pageNum.value * pageSize.value, pageTotal.value))


const packageList = computed(() => {
  const keyword = packageKeyword.value.trim()
  if (!keyword) return packages.value
  return packages.value.filter((item) => item.name.includes(keyword) || item.remark.includes(keyword))
})

const filteredTags = computed(() => {
  const keyword = tagKeyword.value.trim()
  return smartTags.value.filter((tag) => {
    const keywordMatched =
      !keyword ||
      tag.name.includes(keyword) ||
      (tag.description || '').includes(keyword) ||
      tag.source.includes(keyword) ||
      tag.category.includes(keyword)
    return keywordMatched
  })
})

const includeTags = computed(() => selectedTags.value.filter((tag) => tag.mode === 'include'))
const excludeTags = computed(() => selectedTags.value.filter((tag) => tag.mode === 'exclude'))
const selectedPackage = computed(() => packages.value.find((item) => item.id === selectedPackageId.value))

loadCatalog()
loadPackages()

async function selectCategory(category: string) {
  if (activeCategory.value === category && smartTags.value.length) return
  activeCategory.value = category
  await loadCatalog(category)
}

function selectTag(tag: SmartTag) {
  const mode = excludeMode.value ? 'exclude' : 'include'
  const existedIndex = selectedTags.value.findIndex((item) => item.id === tag.id)
  if (existedIndex >= 0) {
    selectedTags.value[existedIndex] = { ...tag, mode }
    return
  }
  selectedTags.value.push({ ...tag, mode })
}

function removeSelectedTag(index: number) {
  selectedTags.value.splice(index, 1)
}

function clearSelectedTags() {
  selectedTags.value = []
  selectedPackageId.value = ''
  selectedRowIds.value = []
}

function resetSearch() {
  clearSelectedTags()
  excludeMode.value = false
  tagKeyword.value = ''
  activeCategory.value = '全部'
  packageKeyword.value = ''
  sortKey.value = 'bjsj'
  sortAsc.value = false
  pageNum.value = 1
  pageSize.value = 10
  pageTotal.value = 0
  applyTimeFromReportCache()
  hasSearched.value = false
  matchedRows.value = []
  resultSummary.people = 0
  resultSummary.incidents = 0
  resultSummary.stations = 0
}

async function loadCatalog(sheet?: string) {
  loadingCatalog.value = true
  try {
    const target = sheet || activeCategory.value || '全部'
    const response = await listTagCatalog(target)
    smartTags.value = response.data?.tags || []
    const categories = response.data?.categories || ['全部']
    smartTagCategories.value = categories.length ? categories : ['全部']
    if (!smartTagCategories.value.includes(activeCategory.value)) {
      activeCategory.value = '全部'
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '标签目录加载失败')
  } finally {
    loadingCatalog.value = false
  }
}

async function loadPackages() {
  loadingPackages.value = true
  try {
    const response = await listTagPackages(packageKeyword.value.trim() || undefined)
    packages.value = response.data || []
  } catch (error) {
    message.error(error instanceof Error ? error.message : '标签加载失败')
  } finally {
    loadingPackages.value = false
  }
}

async function runSearch(resetPage = true) {
  if (!selectedTags.value.length) {
    message.warning('请先选择至少一个标签')
    return
  }
  if (resetPage) pageNum.value = 1
  searching.value = true
  try {
    const response = await searchTags({
      tags: selectedTags.value,
      sortKey: sortKey.value,
      sortAsc: sortAsc.value,
      pageNum: pageNum.value,
      pageSize: pageSize.value,
      beginTime: beginTime.value.trim() || undefined,
      endTime: endTime.value.trim() || undefined
    })
    const data = response.data
    matchedRows.value = data?.rows || []
    pageTotal.value = Number(data?.total || 0)
    resultSummary.people = Number(data?.peopleTotal || 0)
    resultSummary.incidents = Number(data?.incidentTotal || data?.total || 0)
    resultSummary.stations = Number(data?.stationTotal || 0)
    selectedRowIds.value = []
    hasSearched.value = true
    message.success(`已筛选出 ${pageTotal.value} 条警情结果`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '标签检索失败')
  } finally {
    searching.value = false
  }
}

async function changePage(nextPage: number) {
  if (nextPage < 1 || nextPage > pageCount.value || nextPage === pageNum.value) return
  pageNum.value = nextPage
  await runSearch(false)
}

watch([sortKey, sortAsc], () => {
  if (hasSearched.value) runSearch(true)
})

function loadPackage(item: JudgmentPackage) {
  selectedPackageId.value = item.id
  selectedTags.value = item.tags.map((tag) => ({ ...tag }))
  selectedRowIds.value = []
  message.success(`已加载“${item.name}”`)
}

function openSavePackage() {
  if (!selectedTags.value.length) {
    message.warning('请先选择标签组合')
    return
  }
  editingPackageId.value = ''
  packageForm.name = selectedPackage.value?.name || ''
  packageForm.remark = selectedPackage.value?.remark || ''
  saveModalVisible.value = true
}

function openEditPackage(item: JudgmentPackage) {
  editingPackageId.value = item.id
  selectedPackageId.value = item.id
  selectedTags.value = item.tags.map((tag) => ({ ...tag }))
  packageForm.name = item.name
  packageForm.remark = item.remark
  saveModalVisible.value = true
}

async function savePackage() {
  const name = packageForm.name.trim()
  if (!name) {
    message.warning('请输入标签名称')
    return
  }
  if (!selectedTags.value.length) {
    message.warning('至少需要选择一个标签')
    return
  }
  try {
    if (editingPackageId.value) {
      await updateTagPackage(editingPackageId.value, {
        name,
        remark: packageForm.remark.trim(),
        tags: selectedTags.value.map((tag) => ({ ...tag }))
      })
      selectedPackageId.value = editingPackageId.value
      message.success('标签已更新')
    } else {
      const response = await saveTagPackage({
        name,
        remark: packageForm.remark.trim(),
        tags: selectedTags.value.map((tag) => ({ ...tag }))
      })
      selectedPackageId.value = response.data?.id || ''
      message.success('标签已保存')
    }
    saveModalVisible.value = false
    await loadPackages()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '标签保存失败')
  }
}

function confirmDeletePackage(item: JudgmentPackage) {
  dialog.warning({
    title: '删除标签',
    content: `确定删除“${item.name}”吗？删除后不可恢复。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteTagPackage(item.id)
        if (selectedPackageId.value === item.id) selectedPackageId.value = ''
        message.success('标签已删除')
        await loadPackages()
      } catch (error) {
        message.error(error instanceof Error ? error.message : '标签删除失败')
      }
    }
  })
}

function toggleRow(row: TagAlarmRow, checked: boolean) {
  if (checked) {
    if (!selectedRowIds.value.includes(row.id)) selectedRowIds.value.push(row.id)
    return
  }
  selectedRowIds.value = selectedRowIds.value.filter((id) => id !== row.id)
}

function openDetail(row: TagAlarmRow) {
  detailRow.value = row
  detailModalVisible.value = true
}

function rowPeopleLabel(row: TagAlarmRow) {
  const names = extractPeopleFromAlarmRow(row)
    .map((item) => String(item['姓名'] || '').trim())
    .filter(Boolean)
  return names.join('、') || '-'
}

function rowTags(row: TagAlarmRow) {
  return extractTagsFromAlarmRow(row).slice(0, 8)
}

async function exportRows(scope: 'all' | 'selected', exportType: 'alarms' | 'people' = 'alarms') {
  const selectedIds = scope === 'selected' ? [...selectedRowIds.value] : undefined
  if (scope === 'selected' && !selectedIds?.length) {
    message.warning('请先勾选要导出的结果')
    return
  }
  if (!matchedRows.value.length && scope === 'all' && !pageTotal.value) {
    message.warning('暂无可导出的结果')
    return
  }
  exporting.value = true
  try {
    const blob = await exportTags({
      tags: selectedTags.value,
      sortKey: sortKey.value,
      sortAsc: sortAsc.value,
      selectedIds,
      pageNum: 1,
      pageSize: 10000,
      exportType,
      beginTime: beginTime.value.trim() || undefined,
      endTime: endTime.value.trim() || undefined
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const typeLabel = exportType === 'people' ? '涉及人员' : '命中警情'
    const scopeLabel = scope === 'selected' ? '选中' : '全部'
    link.download = `标签${typeLabel}-${scopeLabel}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    message.success('导出文件已生成')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

const exportMenuOptions = computed<DropdownOption[]>(() => [
  {
    label: '导出涉及人员',
    key: 'people',
    icon: () => h(NIcon, null, { default: () => h(Download) })
  },
  {
    label: '导出命中警情',
    key: 'alarms',
    icon: () => h(NIcon, null, { default: () => h(Download) })
  }
])

function handleExportMenuSelect(key: string | number) {
  if (key === 'people') {
    void exportRows('all', 'people')
    return
  }
  if (key === 'alarms') {
    void exportRows('all', 'alarms')
  }
}
</script>

<template>
  <section class="grid h-full min-h-0 grid-cols-1 gap-3 overflow-hidden p-3 lg:grid-cols-[minmax(220px,1fr)_minmax(360px,3fr)_minmax(220px,1fr)]">
    <aside class="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-white/80 bg-white/80 shadow-xl shadow-blue-200/20 backdrop-blur-2xl ring-1 ring-white/80">
      <div class="border-b border-slate-100 px-4 py-4">
        <h2 class="text-lg font-bold text-slate-950">标签</h2>
        <NInput v-model:value="packageKeyword" clearable placeholder="按名称搜索" class="mt-3" @keyup.enter="loadPackages" @clear="loadPackages">
          <template #prefix><NIcon :component="Search" class="text-slate-400" /></template>
        </NInput>
      </div>

      <div class="min-h-0 flex-1 space-y-2 overflow-auto p-3" :class="loadingPackages ? 'opacity-60' : ''">
        <button
          v-for="item in packageList"
          :key="item.id"
          type="button"
          class="w-full rounded-xl border p-3 text-left transition"
          :class="selectedPackageId === item.id ? 'border-blue-300 bg-blue-50 shadow-sm' : 'border-slate-100 bg-white hover:border-blue-200 hover:bg-blue-50/50'"
          @click="loadPackage(item)"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold text-slate-800">{{ item.name }}</p>
              <p class="mt-1 text-xs text-slate-400">{{ item.createdAt }}</p>
            </div>
            <NTag size="small" round :bordered="false" :type="item.preset ? 'info' : 'success'">{{ item.tags.length }} 标签</NTag>
          </div>
          <p class="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">{{ item.remark || '暂无备注' }}</p>
          <div class="mt-3 flex items-center justify-between">
            <span class="text-xs text-slate-400">{{ item.preset ? '系统预设' : '自定义' }}</span>
            <span class="flex gap-1">
              <NButton quaternary circle size="tiny" title="修改" @click.stop="openEditPackage(item)">
                <template #icon><NIcon :component="FilePenLine" /></template>
              </NButton>
              <NButton quaternary circle size="tiny" type="error" title="删除" @click.stop="confirmDeletePackage(item)">
                <template #icon><NIcon :component="Trash2" /></template>
              </NButton>
            </span>
          </div>
        </button>
      </div>
    </aside>

    <main class="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-white/80 bg-white/85 shadow-xl shadow-blue-200/20 backdrop-blur-2xl ring-1 ring-white/80">
      <div class="shrink-0 border-b border-slate-100 px-4 py-3 sm:px-5 sm:py-4">
        <div class="flex flex-col gap-3">
          <div class="min-w-0">
            <h1 class="text-lg font-bold tracking-tight text-slate-950 sm:text-xl">标签组合查询</h1>
            <p class="mt-1 text-sm text-slate-500">组合包含标签与剔除标签，快速定位复杂条件下的人员与警情线索。</p>
          </div>
          <div class="flex flex-col gap-2 min-[640px]:flex-row min-[640px]:flex-wrap min-[640px]:items-center">
            <NDatePicker
              v-model:formatted-value="alarmTimeRange"
              class="tag-workbench-datepicker w-full min-w-0 min-[640px]:max-w-[380px] min-[640px]:flex-1"
              type="datetimerange"
              clearable
              value-format="yyyy-MM-dd HH:mm:ss"
              format="yyyy-MM-dd HH:mm:ss"
              time-picker-format="HH:mm:ss"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
            />
            <div class="flex flex-wrap gap-2">
              <NButton secondary @click="clearSelectedTags">
                <template #icon><NIcon :component="X" /></template>
                清空标签
              </NButton>
              <NButton secondary @click="resetSearch">
                <template #icon><NIcon :component="RotateCcw" /></template>
                重置条件
              </NButton>
              <NButton type="primary" :loading="searching" @click="() => runSearch(true)">
                <template #icon><NIcon :component="Play" /></template>
                检索
              </NButton>
            </div>
          </div>
        </div>
      </div>

      <div class="shrink-0 border-b border-slate-100 bg-slate-50/70 px-4 py-3 sm:px-5 sm:py-4">
        <div class="mb-3 flex items-center justify-between gap-3">
          <div class="text-sm font-semibold text-slate-700">已选择标签</div>
          <NButton secondary type="primary" size="small" @click="openSavePackage">
            <template #icon><NIcon :component="PackagePlus" /></template>
            保存标签
          </NButton>
        </div>
        <div v-if="selectedTags.length" class="flex max-h-24 flex-wrap gap-2 overflow-y-auto">
          <button
            v-for="(tag, index) in selectedTags"
            :key="`${tag.id}-${index}`"
            type="button"
            class="inline-flex max-w-full items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium ring-1 transition hover:shadow-sm"
            :class="tag.mode === 'exclude' ? 'bg-rose-50 text-rose-700 ring-rose-200' : 'bg-blue-50 text-blue-700 ring-blue-200'"
            @click="removeSelectedTag(index)"
          >
            <MinusCircle v-if="tag.mode === 'exclude'" :size="14" class="shrink-0" />
            <Check v-else :size="14" class="shrink-0" />
            <span class="truncate">{{ tag.mode === 'exclude' ? '排除' : '包含' }} {{ tag.name }}</span>
            <X :size="13" class="shrink-0 opacity-60" />
          </button>
        </div>
        <div v-else class="rounded-xl border border-dashed border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-400">
          从右侧标签库点击标签，按添加顺序生成组合条件。
        </div>
      </div>

      <div class="grid shrink-0 grid-cols-3 gap-2 border-b border-slate-100 px-4 py-3 sm:px-5">
        <div class="rounded-xl border border-blue-100 bg-blue-50/70 px-4 py-3">
          <p class="text-xs text-slate-500">命中警情</p>
          <p class="mt-1 text-2xl font-bold text-slate-950">{{ hasSearched ? resultSummary.incidents : '--' }}</p>
        </div>
        <div class="rounded-xl border border-emerald-100 bg-emerald-50/70 px-4 py-3">
          <p class="text-xs text-slate-500">涉及人员</p>
          <p class="mt-1 text-2xl font-bold text-slate-950">{{ hasSearched ? resultSummary.people : '--' }}</p>
        </div>
        <div class="rounded-xl border border-amber-100 bg-amber-50/70 px-4 py-3">
          <p class="text-xs text-slate-500">反馈单位</p>
          <p class="mt-1 text-2xl font-bold text-slate-950">{{ hasSearched ? resultSummary.stations : '--' }}</p>
        </div>
      </div>

      <div class="flex shrink-0 flex-col gap-3 border-b border-slate-100 px-4 py-3 sm:px-5 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm text-slate-500">排序</span>
          <NSelect v-model:value="sortKey" :options="sortOptions" :disabled="searching" class="!w-36" />
          <NButton secondary size="small" :disabled="searching" :loading="searching" @click="sortAsc = !sortAsc">{{ sortAsc ? '升序' : '降序' }}</NButton>
        </div>
        <div class="flex flex-wrap gap-2">
          <NButton secondary :loading="exporting" @click="exportRows('selected', 'alarms')">
            <template #icon><NIcon :component="Download" /></template>
            导出选中结果
          </NButton>
          <NDropdown
            trigger="hover"
            placement="bottom-end"
            :options="exportMenuOptions"
            :disabled="exporting"
            @select="handleExportMenuSelect"
          >
            <NButton secondary type="primary" :loading="exporting">
              <template #icon><NIcon :component="Download" /></template>
              导出
            </NButton>
          </NDropdown>
        </div>
      </div>

      <div class="relative min-h-0 flex-1 overflow-auto">
        <NSpin :show="searching" class="min-h-72" content-class="min-h-72">
          <table class="w-full min-w-[1100px] table-fixed border-collapse text-left">
            <colgroup>
              <col class="w-14" />
              <col class="w-14" />
              <col class="w-[150px]" />
              <col class="w-[150px]" />
              <col class="w-[120px]" />
              <col class="w-[90px]" />
              <col class="w-[120px]" />
              <col class="w-[180px]" />
              <col />
            </colgroup>
            <thead class="sticky top-0 z-10 bg-white/95 text-xs font-semibold text-slate-500 backdrop-blur">
              <tr class="border-b border-slate-200">
                <th class="px-3 py-3 sm:px-5">选择</th>
                <th class="px-3 py-3 sm:px-4">序号</th>
                <th class="px-3 py-3 sm:px-4">处警单号</th>
                <th class="px-3 py-3 sm:px-4">报警时间</th>
                <th class="px-3 py-3 sm:px-4">反馈单位</th>
                <th class="px-3 py-3 sm:px-4">反馈人</th>
                <th class="px-3 py-3 sm:px-4">涉及人员</th>
                <th class="px-3 py-3 sm:px-4">关联标签</th>
                <th class="px-3 py-3 sm:px-5">处警情况</th>
              </tr>
            </thead>
            <tbody v-if="hasSearched && !searching" class="divide-y divide-slate-100">
              <tr
                v-for="(row, index) in matchedRows"
                :key="row.id"
                class="cursor-pointer transition hover:bg-blue-50/35"
                @click="openDetail(row)"
              >
                <td class="overflow-hidden px-3 py-3 sm:px-5 sm:py-4" @click.stop>
                  <NCheckbox :checked="selectedRowIds.includes(row.id)" @update:checked="toggleRow(row, Boolean($event))" />
                </td>
                <td class="overflow-hidden px-3 py-3 text-sm text-slate-500 sm:px-4 sm:py-4">{{ pageStart + index }}</td>
                <td class="overflow-hidden px-3 py-3 font-mono text-xs text-slate-600 sm:px-4 sm:py-4">
                  <p class="truncate" :title="row.cjdbh || ''">{{ row.cjdbh || '-' }}</p>
                </td>
                <td class="overflow-hidden px-3 py-3 text-sm text-slate-700 sm:px-4 sm:py-4">
                  <p class="truncate" :title="row.bjsj || ''">{{ row.bjsj || '-' }}</p>
                </td>
                <td class="overflow-hidden px-3 py-3 text-sm text-slate-700 sm:px-4 sm:py-4">
                  <p class="truncate" :title="row.fkdwmc || ''">{{ row.fkdwmc || '-' }}</p>
                </td>
                <td class="overflow-hidden px-3 py-3 text-sm text-slate-700 sm:px-4 sm:py-4">
                  <p class="truncate" :title="row.fkrxm || ''">{{ row.fkrxm || '-' }}</p>
                </td>
                <td class="overflow-hidden px-3 py-3 text-sm text-slate-700 sm:px-4 sm:py-4">
                  <p class="truncate" :title="rowPeopleLabel(row)">{{ rowPeopleLabel(row) }}</p>
                </td>
                <td class="overflow-hidden px-3 py-3 sm:px-4 sm:py-4">
                  <div class="flex flex-nowrap gap-1.5 overflow-hidden">
                    <NTag v-for="tag in rowTags(row)" :key="tag" size="small" round :bordered="false" class="max-w-[100px] shrink-0">
                      <span class="truncate">{{ tag }}</span>
                    </NTag>
                  </div>
                </td>
                <td class="overflow-hidden px-3 py-3 sm:px-5 sm:py-4">
                  <p class="truncate text-xs leading-5 text-slate-500" :title="row.cjqk || ''">{{ row.cjqk || '-' }}</p>
                </td>
              </tr>
            </tbody>
          </table>

          <div v-if="!hasSearched && !searching" class="flex min-h-72 flex-col items-center justify-center px-6 text-center">
            <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-500">
              <Search :size="26" />
            </div>
            <p class="mt-4 font-semibold text-slate-700">等待检索</p>
            <p class="mt-1 text-sm text-slate-400">选择标签组合后点击检索，下方会展示命中的警情列表。</p>
          </div>
          <div v-else-if="hasSearched && !searching && !matchedRows.length" class="flex min-h-72 flex-col items-center justify-center px-6 text-center">
            <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
              <Filter :size="26" />
            </div>
            <p class="mt-4 font-semibold text-slate-700">没有命中结果</p>
            <p class="mt-1 text-sm text-slate-400">可以减少包含标签，或调整剔除标签后重新检索。</p>
          </div>
        </NSpin>
      </div>

      <div v-if="hasSearched && pageTotal > 0" class="flex shrink-0 items-center justify-between gap-3 border-t border-slate-100 px-5 py-3">
        <p class="text-xs text-slate-500">
          共 {{ pageTotal }} 条，当前 {{ pageStart }}-{{ pageEnd }}
        </p>
        <div class="flex items-center gap-2">
          <NButton size="small" secondary circle :disabled="pageNum <= 1 || searching" @click="changePage(pageNum - 1)">
            <template #icon><NIcon :component="ChevronLeft" /></template>
          </NButton>
          <span class="min-w-16 text-center text-sm tabular-nums text-slate-600">第 {{ pageNum }} / {{ pageCount }} 页</span>
          <NButton
            size="small"
            secondary
            circle
            :disabled="pageNum >= pageCount || searching"
            @click="changePage(pageNum + 1)"
          >
            <template #icon><NIcon :component="ChevronRight" /></template>
          </NButton>
        </div>
      </div>
    </main>

    <aside class="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-white/80 bg-white/80 shadow-xl shadow-blue-200/20 backdrop-blur-2xl ring-1 ring-white/80">
      <div class="border-b border-slate-100 px-4 py-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-bold text-slate-950">标签操作区</h2>
            <p class="mt-1 text-xs text-slate-500">点击标签加入当前组合</p>
          </div>
          <div class="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5">
            <span class="text-xs font-medium" :class="excludeMode ? 'text-rose-600' : 'text-blue-600'">{{ excludeMode ? '剔除' : '包含' }}</span>
            <NSwitch v-model:value="excludeMode" size="small" />
          </div>
        </div>
        <NInput v-model:value="tagKeyword" clearable placeholder="搜索标签" class="mt-3">
          <template #prefix><NIcon :component="Search" class="text-slate-400" /></template>
        </NInput>
        <div class="mt-3 flex flex-wrap gap-1.5">
          <button
            v-for="category in smartTagCategories"
            :key="category"
            type="button"
            class="rounded-full px-3 py-1 text-xs font-medium ring-1 transition"
            :class="activeCategory === category ? 'bg-slate-900 text-white ring-slate-900' : 'bg-white text-slate-500 ring-slate-200 hover:bg-slate-50'"
            @click="selectCategory(category)"
          >
            {{ category }}
          </button>
        </div>
      </div>

      <div class="min-h-0 flex-1 space-y-2 overflow-auto p-3" :class="loadingCatalog ? 'opacity-60' : ''">
        <button
          v-for="tag in filteredTags"
          :key="tag.id"
          type="button"
          class="w-full rounded-xl border border-slate-100 bg-white p-3 text-left transition hover:border-blue-200 hover:bg-blue-50/45"
          @click="selectTag(tag)"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="font-semibold text-slate-800">{{ tag.name }}</p>
              <p class="mt-1 text-xs text-slate-400">{{ tag.source }} / {{ tag.category }}</p>
            </div>
            <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full" :class="excludeMode ? 'bg-rose-50 text-rose-600' : 'bg-blue-50 text-blue-600'">
              <MinusCircle v-if="excludeMode" :size="16" />
              <Plus v-else :size="16" />
            </span>
          </div>
          <p v-if="tag.description" class="mt-2 text-xs leading-5 text-slate-500">{{ tag.description }}</p>
        </button>
      </div>
    </aside>

    <NModal
      v-model:show="saveModalVisible"
      preset="card"
      :title="editingPackageId ? '修改标签' : '保存标签'"
      class="!w-[min(520px,calc(100vw-24px))]"
      :bordered="false"
      :mask-closable="false"
    >
      <div class="space-y-4">
        <label class="block space-y-1.5">
          <span class="text-sm font-medium text-slate-700">标签名称</span>
          <NInput v-model:value="packageForm.name" placeholder="请输入标签名称" />
        </label>
        <label class="block space-y-1.5">
          <span class="text-sm font-medium text-slate-700">备注</span>
          <NInput v-model:value="packageForm.remark" type="textarea" :rows="3" placeholder="说明适用场景或筛选口径" />
        </label>
        <div class="rounded-xl border border-slate-100 bg-slate-50 p-3">
          <p class="mb-2 text-xs font-semibold text-slate-500">当前标签组合</p>
          <div class="flex flex-wrap gap-2">
            <NTag v-for="tag in selectedTags" :key="`${tag.id}-${tag.mode}`" size="small" round :bordered="false" :type="tag.mode === 'exclude' ? 'error' : 'info'">
              {{ tag.mode === 'exclude' ? '排除' : '包含' }} {{ tag.name }}
            </NTag>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <NButton @click="saveModalVisible = false">取消</NButton>
          <NButton type="primary" @click="savePackage">确认</NButton>
        </div>
      </template>
    </NModal>

    <AlarmDetailModal v-model:show="detailModalVisible" :row="detailRow" />
  </section>
</template>

<style scoped>
.tag-workbench-datepicker :deep(.n-input) {
  width: 100%;
}

.tag-workbench-datepicker :deep(.n-input__input-el) {
  min-width: 0;
}
</style>
