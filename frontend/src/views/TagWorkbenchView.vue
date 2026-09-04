<script setup lang="ts">
import {
  deleteTagPackage,
  listTagPackages,
  saveTagPackage,
  updateTagPackage,
  type JudgmentPackage,
  type SelectedSmartTag,
  type SmartTag,
} from '@/api/tag'
import {
  groupTagsByDomain,
  listSecurityTagCatalog,
  listTagV2Catalog,
  personDisplayName,
  personRoleLabel,
  personTagLeaf,
  searchTagV2Alarms,
  type SecurityTagItem,
  type TagV2AlarmRow,
  type TagV2DictItem,
} from '@/api/tagV2'
import { readReportDateRange } from '@/utils/reportDateRange'
import { maskCjqkText, maskIdNo, maskPersonName, maskPhone } from '@/utils/privacyMask'
import { Bookmark, Database, Plus, RefreshCcw, Save, Search, Shield, X } from 'lucide-vue-next'
import {
  NButton,
  NCard,
  NDataTable,
  NDatePicker,
  NDivider,
  NDrawer,
  NDrawerContent,
  NEmpty,
  NIcon,
  NInput,
  NInputNumber,
  NModal,
  NPopconfirm,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  NTooltip,
  useMessage,
  type DataTableColumns,
  type SelectOption,
} from 'naive-ui'
import { computed, h, onMounted, reactive, ref, watch } from 'vue'

const message = useMessage()

const loadingPackages = ref(false)
const loadingCatalog = ref(false)
const searching = ref(false)
const packageModalVisible = ref(false)
const detailVisible = ref(false)
const activePool = ref<'alarm' | 'person' | 'security'>('alarm')

const packages = ref<JudgmentPackage[]>([])
const packageKeyword = ref('')
const selectedPackageId = ref('')
const selectedTags = ref<SelectedSmartTag[]>([])

const alarmTags = ref<TagV2DictItem[]>([])
const securityTags = ref<SecurityTagItem[]>([])
const domains = ref<string[]>([])
const tagKeyword = ref('')
const activeDomain = ref('全部')

const rows = ref<TagV2AlarmRow[]>([])
const selectedRow = ref<TagV2AlarmRow | null>(null)
const pageNum = ref(1)
const pageSize = ref(20)
const pageTotal = ref(0)
const resultSummary = reactive({ incidents: 0, people: 0 })

const filters = reactive({
  beginTime: null as string | null,
  endTime: null as string | null,
  fkdbh: '',
  jjdbh: '',
  unit: '',
  keyword: '',
})

const packageForm = reactive({ id: '', name: '', remark: '' })

const poolOptions = [
  { label: '本标签池', value: 'alarm' },
  { label: '人员标签池', value: 'person' },
  { label: '治安标签池', value: 'security' },
]

const domainOptions = computed<SelectOption[]>(() => [
  { label: '全部领域', value: '全部' },
  ...domains.value.map((item) => ({ label: item, value: item })),
])

const filteredPackages = computed(() => {
  const keyword = packageKeyword.value.trim()
  if (!keyword) return packages.value
  return packages.value.filter((item) => {
    const text = `${item.name} ${item.remark} ${(item.tags || []).map((tag) => tag.name).join(' ')}`
    return text.includes(keyword)
  })
})

const alarmPoolTags = computed(() => {
  const keyword = tagKeyword.value.trim()
  const domain = activeDomain.value
  return alarmTags.value.filter((tag) => {
    const inDomain = domain === '全部' || tag.domain === domain
    if (!inDomain) return false
    if (activePool.value === 'person') {
      const path = tag.tagPath || ''
      const domainText = tag.domain || ''
      if (!path.includes('人物') && !path.includes('人员') && !domainText.includes('人物') && !domainText.includes('人员')) {
        return false
      }
    }
    if (!keyword) return true
    return `${tag.tagPath} ${tag.tagCode} ${tag.domain} ${tag.tagRule || ''}`.includes(keyword)
  })
})

const securityPoolTags = computed(() => {
  const keyword = tagKeyword.value.trim()
  if (!keyword) return securityTags.value
  return securityTags.value.filter((tag) => `${tag.name} ${tag.tagCode || ''}`.includes(keyword))
})

const currentPoolTags = computed(() => (activePool.value === 'security' ? securityPoolTags.value : alarmPoolTags.value))
const includeTags = computed(() => selectedTags.value.filter((tag) => tag.mode !== 'exclude'))
const excludeTags = computed(() => selectedTags.value.filter((tag) => tag.mode === 'exclude'))
const pageCount = computed(() => Math.max(1, Math.ceil(pageTotal.value / pageSize.value)))

const tableColumns = computed<DataTableColumns<TagV2AlarmRow>>(() => [
  {
    title: '反馈单号',
    key: 'fkdbh',
    width: 180,
    fixed: 'left',
    render(row) {
      return h(NButton, { text: true, type: 'primary', onClick: () => openDetail(row) }, { default: () => row.fkdbh })
    },
  },
  { title: '接警单号', key: 'jjdbh', width: 170, render: (row) => row.jjdbh || '-' },
  { title: '报警时间', key: 'bjsj', width: 170, render: (row) => row.bjsj || '-' },
  { title: '反馈单位', key: 'fkdwmc', width: 180, ellipsis: { tooltip: true }, render: (row) => row.fkdwmc || '-' },
  { title: '责任民警', key: 'fkrxm', width: 110, render: (row) => maskPersonName(row.fkrxm || row.zrmj || '') || '-' },
  {
    title: '标签命中',
    key: 'tags',
    width: 320,
    render(row) {
      const tags = (row.tags || []).slice(0, 4)
      if (!tags.length) return '-'
      return h('div', { class: 'tag-cell' }, [
        ...tags.map((tag) => h(NTag, { size: 'small', bordered: false, type: 'info' }, { default: () => tag.name || tag.tagPath })),
        (row.tags || []).length > tags.length ? h(NTag, { size: 'small', bordered: false }, { default: () => `+${(row.tags || []).length - tags.length}` }) : null,
      ])
    },
  },
  { title: '人员数', key: 'personCount', width: 90, render: (row) => String(row.personCount || 0) },
  {
    title: '警情摘要',
    key: 'cjqk',
    minWidth: 260,
    ellipsis: { tooltip: true },
    render: (row) => maskCjqkText(row.cjqk || '') || '-',
  },
])

onMounted(async () => {
  applyDefaultTimeRange()
  await Promise.all([loadPackages(), loadCatalog(), loadSecurityCatalog()])
})

watch(selectedPackageId, (id) => {
  if (!id) return
  const pkg = packages.value.find((item) => item.id === id)
  if (!pkg) return
  selectedTags.value = (pkg.tags || []).map((tag) => ({ ...tag }))
  pageNum.value = 1
  runSearch(false)
})

function applyDefaultTimeRange() {
  const range = readReportDateRange()
  if (range.beginTime && range.endTime) {
    filters.beginTime = range.beginTime || null
    filters.endTime = range.endTime || null
  }
}

function toSmartTag(item: TagV2DictItem | SecurityTagItem): SmartTag {
  const isSecurity = 'tagName' in item || item.domain === '治安标签'
  const name = isSecurity ? `治安标签/${item.name}` : (item as TagV2DictItem).tagPath
  return {
    id: isSecurity ? `zj:${item.tagCode || item.name}` : (item as TagV2DictItem).tagCode,
    name,
    category: isSecurity ? '治安标签' : ((item as TagV2DictItem).domain || '本标签池'),
    source: isSecurity ? 'jq_person_zj_tags' : 'jq_tag_result',
    description: isSecurity ? `治安命中人员 ${(item as SecurityTagItem).personCount || 0} 人` : (item as TagV2DictItem).tagRule || '',
  }
}

function addTag(item: TagV2DictItem | SecurityTagItem, mode: 'include' | 'exclude' = 'include') {
  const tag = toSmartTag(item)
  const index = selectedTags.value.findIndex((selected) => selected.name === tag.name)
  const next = { ...tag, mode }
  if (index >= 0) selectedTags.value[index] = next
  else selectedTags.value.push(next)
}

function removeTag(index: number) {
  selectedTags.value.splice(index, 1)
}

function clearSelectedTags() {
  selectedTags.value = []
  selectedPackageId.value = ''
}

async function loadPackages() {
  loadingPackages.value = true
  try {
    const response = await listTagPackages()
    packages.value = response.data || []
  } catch (error) {
    message.error(error instanceof Error ? error.message : '组合列表加载失败')
  } finally {
    loadingPackages.value = false
  }
}

async function loadCatalog() {
  loadingCatalog.value = true
  try {
    const response = await listTagV2Catalog()
    alarmTags.value = response.data?.tags || []
    domains.value = response.data?.domains || []
  } catch (error) {
    message.error(error instanceof Error ? error.message : '本标签池加载失败')
  } finally {
    loadingCatalog.value = false
  }
}

async function loadSecurityCatalog() {
  try {
    const response = await listSecurityTagCatalog()
    securityTags.value = response.data?.tags || []
  } catch (error) {
    message.error(error instanceof Error ? error.message : '治安标签池加载失败')
  }
}

async function runSearch(resetPage = true) {
  if (!selectedTags.value.length && !filters.beginTime && !filters.endTime && !filters.fkdbh && !filters.jjdbh && !filters.unit && !filters.keyword) {
    message.warning('请先选择标签组合或输入检索条件')
    return
  }
  if (resetPage) pageNum.value = 1
  searching.value = true
  try {
    const response = await searchTagV2Alarms({
      includeTags: includeTags.value.map((tag) => tag.name),
      excludeTags: excludeTags.value.map((tag) => tag.name),
      fkdbh: filters.fkdbh.trim() || undefined,
      cjdbh: filters.jjdbh.trim() || undefined,
      fkdwmc: filters.unit.trim() || undefined,
      keyword: filters.keyword.trim() || undefined,
      beginTime: filters.beginTime || undefined,
      endTime: filters.endTime || undefined,
      pageNum: pageNum.value,
      pageSize: pageSize.value,
    })
    rows.value = response.data?.rows || []
    pageTotal.value = Number(response.data?.total || 0)
    resultSummary.incidents = pageTotal.value
    resultSummary.people = rows.value.reduce((sum, row) => sum + Number(row.personCount || 0), 0)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '组合检索失败')
  } finally {
    searching.value = false
  }
}

function resetAll() {
  filters.fkdbh = ''
  filters.jjdbh = ''
  filters.unit = ''
  filters.keyword = ''
  applyDefaultTimeRange()
  clearSelectedTags()
  rows.value = []
  pageTotal.value = 0
  resultSummary.incidents = 0
  resultSummary.people = 0
}

function openCreatePackage() {
  packageForm.id = ''
  packageForm.name = ''
  packageForm.remark = ''
  packageModalVisible.value = true
}

function openEditPackage(pkg: JudgmentPackage) {
  selectedPackageId.value = pkg.id
  selectedTags.value = (pkg.tags || []).map((tag) => ({ ...tag }))
  packageForm.id = pkg.id
  packageForm.name = pkg.name
  packageForm.remark = pkg.remark || ''
  packageModalVisible.value = true
}

async function submitPackage() {
  if (!packageForm.name.trim()) {
    message.warning('请输入组合名称')
    return
  }
  if (!selectedTags.value.length) {
    message.warning('请至少选择一个标签')
    return
  }
  try {
    const payload = { name: packageForm.name.trim(), remark: packageForm.remark.trim(), tags: selectedTags.value }
    if (packageForm.id) await updateTagPackage(packageForm.id, payload)
    else await saveTagPackage(payload)
    packageModalVisible.value = false
    message.success('组合已保存')
    await loadPackages()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '组合保存失败')
  }
}

async function removePackage(pkg: JudgmentPackage) {
  try {
    await deleteTagPackage(pkg.id)
    if (selectedPackageId.value === pkg.id) clearSelectedTags()
    message.success('组合已删除')
    await loadPackages()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '组合删除失败')
  }
}

function openDetail(row: TagV2AlarmRow) {
  selectedRow.value = row
  detailVisible.value = true
}

function onPageChange(page: number) {
  pageNum.value = page
  runSearch(false)
}

function onPageSizeChange(size: number | null) {
  pageSize.value = Number(size || 20)
  pageNum.value = 1
  runSearch(false)
}

</script>

<template>
  <div class="judgment-page">
    <aside class="left-panel">
      <div class="panel-header">
        <div>
          <h2>标签组合</h2>
          <p>本标签池 + 人员标签池 + 治安标签池</p>
        </div>
        <NButton circle type="primary" @click="openCreatePackage">
          <template #icon><NIcon :component="Plus" /></template>
        </NButton>
      </div>

      <NInput v-model:value="packageKeyword" clearable placeholder="搜索组合" />
      <NSpin :show="loadingPackages" class="package-spin">
        <div class="package-list">
          <div
            v-for="pkg in filteredPackages"
            :key="pkg.id"
            class="package-item"
            :class="{ active: selectedPackageId === pkg.id }"
            @click="selectedPackageId = pkg.id"
          >
            <div class="package-main">
              <NIcon :component="Bookmark" />
              <div>
                <div class="package-name">{{ pkg.name }}</div>
                <div class="package-remark">{{ pkg.remark || '无备注' }}</div>
              </div>
            </div>
            <div class="package-tags">
              <NTag v-for="tag in (pkg.tags || []).slice(0, 3)" :key="tag.name" size="small" :type="tag.mode === 'exclude' ? 'error' : 'info'" bordered>
                {{ tag.mode === 'exclude' ? '排除' : '包含' }} {{ tag.name }}
              </NTag>
              <NTag v-if="(pkg.tags || []).length > 3" size="small">+{{ (pkg.tags || []).length - 3 }}</NTag>
            </div>
            <div class="package-actions" @click.stop>
              <NButton size="tiny" quaternary @click="openEditPackage(pkg)">编辑</NButton>
              <NPopconfirm @positive-click="removePackage(pkg)">
                <template #trigger><NButton size="tiny" quaternary type="error">删除</NButton></template>
                确认删除该组合？
              </NPopconfirm>
            </div>
          </div>
          <NEmpty v-if="!filteredPackages.length" description="暂无组合" />
        </div>
      </NSpin>
    </aside>

    <main class="right-panel">
      <NCard class="search-card" :bordered="false">
        <template #header>
          <div class="card-title"><NIcon :component="Search" />组合检索</div>
        </template>
        <div class="filter-grid">
          <NDatePicker v-model:formatted-value="filters.beginTime" value-format="yyyy-MM-dd HH:mm:ss" type="datetime" clearable placeholder="开始时间" />
          <NDatePicker v-model:formatted-value="filters.endTime" value-format="yyyy-MM-dd HH:mm:ss" type="datetime" clearable placeholder="结束时间" />
          <NInput v-model:value="filters.fkdbh" clearable placeholder="反馈单号" />
          <NInput v-model:value="filters.jjdbh" clearable placeholder="接警单号" />
          <NInput v-model:value="filters.unit" clearable placeholder="反馈单位" />
          <NInput v-model:value="filters.keyword" clearable placeholder="警情关键词" />
        </div>

        <div class="selected-area">
          <div class="selected-title">当前组合</div>
          <div class="selected-tags">
            <NTag v-for="(tag, index) in selectedTags" :key="`${tag.name}-${index}`" closable :type="tag.mode === 'exclude' ? 'error' : tag.source === 'jq_person_zj_tags' ? 'warning' : 'info'" @close="removeTag(index)">
              {{ tag.mode === 'exclude' ? '排除' : '包含' }} {{ tag.name }}
            </NTag>
            <span v-if="!selectedTags.length" class="muted">请从下方标签池或左侧组合选择标签</span>
          </div>
          <NSpace>
            <NButton secondary @click="clearSelectedTags"><template #icon><NIcon :component="X" /></template>清空标签</NButton>
            <NButton secondary @click="openCreatePackage"><template #icon><NIcon :component="Save" /></template>保存为组合</NButton>
            <NButton @click="resetAll"><template #icon><NIcon :component="RefreshCcw" /></template>重置</NButton>
            <NButton type="primary" :loading="searching" @click="runSearch(true)"><template #icon><NIcon :component="Search" /></template>检索</NButton>
          </NSpace>
        </div>
      </NCard>

      <NCard class="pool-card" :bordered="false">
        <template #header>
          <div class="card-title"><NIcon :component="Database" />标签池</div>
        </template>
        <div class="pool-tools">
          <NSelect v-model:value="activePool" :options="poolOptions" class="pool-select" />
          <NSelect v-if="activePool !== 'security'" v-model:value="activeDomain" :options="domainOptions" class="domain-select" />
          <NInput v-model:value="tagKeyword" clearable placeholder="搜索标签名称/路径/编码" />
        </div>
        <NSpin :show="loadingCatalog">
          <div class="pool-list">
            <div v-for="item in currentPoolTags.slice(0, 240)" :key="item.id" class="pool-item">
              <div class="pool-name">
                <NIcon :component="activePool === 'security' ? Shield : Bookmark" />
                <NTooltip>
                  <template #trigger>
                    <span>{{ activePool === 'security' ? item.name : (item as TagV2DictItem).tagPath }}</span>
                  </template>
                  {{ activePool === 'security' ? item.name : (item as TagV2DictItem).tagRule || (item as TagV2DictItem).tagPath }}
                </NTooltip>
              </div>
              <div class="pool-meta">
                {{ activePool === 'security' ? `命中人员 ${(item as SecurityTagItem).personCount || 0}` : (item as TagV2DictItem).domain }}
              </div>
              <NSpace size="small">
                <NButton size="tiny" type="primary" secondary @click="addTag(item, 'include')">包含</NButton>
                <NButton size="tiny" type="error" secondary @click="addTag(item, 'exclude')">排除</NButton>
              </NSpace>
            </div>
            <NEmpty v-if="!currentPoolTags.length" description="暂无标签" />
          </div>
        </NSpin>
      </NCard>

      <NCard class="result-card" :bordered="false">
        <template #header>
          <div class="result-header">
            <div class="card-title">检索结果</div>
            <div class="summary">警情 {{ resultSummary.incidents }} 条，当前页人员 {{ resultSummary.people }} 人</div>
          </div>
        </template>
        <NDataTable :columns="tableColumns" :data="rows" :loading="searching" :row-key="(row) => row.fkdbh" :scroll-x="1280" size="small" />
        <div class="pager">
          <NButton :disabled="pageNum <= 1 || searching" @click="onPageChange(pageNum - 1)">上一页</NButton>
          <span>第 {{ pageNum }} / {{ pageCount }} 页，共 {{ pageTotal }} 条</span>
          <NButton :disabled="pageNum >= pageCount || searching" @click="onPageChange(pageNum + 1)">下一页</NButton>
          <span>每页</span>
          <NInputNumber :value="pageSize" :min="10" :max="200" size="small" @update:value="onPageSizeChange" />
        </div>
      </NCard>
    </main>

    <NModal v-model:show="packageModalVisible" preset="card" title="保存标签组合" class="package-modal">
      <NSpace vertical>
        <NInput v-model:value="packageForm.name" placeholder="组合名称，例如：治安重点人员涉纠纷" />
        <NInput v-model:value="packageForm.remark" type="textarea" placeholder="组合说明" />
        <div class="selected-tags modal-tags">
          <NTag v-for="(tag, index) in selectedTags" :key="`${tag.name}-${index}`" closable :type="tag.mode === 'exclude' ? 'error' : tag.source === 'jq_person_zj_tags' ? 'warning' : 'info'" @close="removeTag(index)">
            {{ tag.mode === 'exclude' ? '排除' : '包含' }} {{ tag.name }}
          </NTag>
        </div>
        <template v-if="!selectedTags.length"><NEmpty description="请先添加标签" /></template>
        <NSpace justify="end">
          <NButton @click="packageModalVisible = false">取消</NButton>
          <NButton type="primary" @click="submitPackage">保存</NButton>
        </NSpace>
      </NSpace>
    </NModal>

    <NDrawer v-model:show="detailVisible" width="720">
      <NDrawerContent :title="selectedRow?.fkdbh || '警情详情'" closable>
        <template v-if="selectedRow">
          <div class="detail-section">
            <h3>基础信息</h3>
            <p><b>接警单号：</b>{{ selectedRow.jjdbh || '-' }}</p>
            <p><b>报警时间：</b>{{ selectedRow.bjsj || '-' }}</p>
            <p><b>反馈单位：</b>{{ selectedRow.fkdwmc || '-' }}</p>
            <p><b>警情内容：</b>{{ maskCjqkText(selectedRow.cjqk || '') || '-' }}</p>
          </div>
          <NDivider />
          <div class="detail-section">
            <h3>警情标签</h3>
            <div v-for="group in groupTagsByDomain(selectedRow.tags || [])" :key="group.domain" class="domain-group">
              <div class="domain-title">{{ group.domain }}</div>
              <div class="tag-cell">
                <NTag v-for="tag in group.items" :key="`${tag.id}-${tag.tagPath}`" size="small" type="info" bordered>{{ tag.tagPath }}</NTag>
              </div>
            </div>
          </div>
          <NDivider />
          <div class="detail-section">
            <h3>涉及人员与治安标签</h3>
            <div v-if="selectedRow.persons?.length" class="person-list">
              <div
                v-for="person in selectedRow.persons"
                :key="`${person.personRole}-${person.idNo}-${person.personName}`"
                class="person-card"
              >
                <div class="person-title">
                  <span>{{ maskPersonName(personDisplayName(person)) }}</span>
                  <NTag size="small" :bordered="false">{{ personRoleLabel(person.personRole) }}</NTag>
                </div>
                <div class="person-meta">
                  {{ [maskIdNo(person.idNo || ''), maskPhone(person.phone || '')].filter(Boolean).join(' / ') || '证件、电话未提取' }}
                </div>
                <div class="tag-cell">
                  <NTag
                    v-for="tag in person.tags || []"
                    :key="`${tag.id}-${tag.tagPath}`"
                    size="small"
                    :bordered="false"
                    :type="tag.tagPath?.startsWith('治安标签/') ? 'warning' : 'success'"
                  >
                    {{ personTagLeaf(tag) }}
                  </NTag>
                  <span v-if="!(person.tags || []).length" class="muted">暂无标签</span>
                </div>
              </div>
            </div>
            <NEmpty v-else description="暂无人员标签" />
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<style scoped>
.judgment-page {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 16px;
  min-height: calc(100vh - 104px);
}
.left-panel,
.right-panel { min-width: 0; }
.left-panel {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid #eef1f6;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.panel-header,
.result-header,
.package-main,
.pool-tools,
.selected-area,
.pager,
.person-title { display: flex; align-items: center; gap: 12px; }
.panel-header { justify-content: space-between; }
.panel-header h2 { margin: 0; font-size: 20px; }
.panel-header p,
.muted,
.package-remark,
.pool-meta,
.summary,
.person-meta { margin: 0; color: #6b7280; font-size: 12px; }
.package-spin { flex: 1; min-height: 0; }
.package-list { display: flex; flex-direction: column; gap: 10px; max-height: calc(100vh - 230px); overflow: auto; padding-right: 4px; }
.package-item { border: 1px solid #edf0f5; border-radius: 12px; padding: 12px; cursor: pointer; transition: all .18s; background: #fafbfc; }
.package-item:hover,
.package-item.active { border-color: #1890ff; background: #eef7ff; }
.package-name { font-weight: 700; color: #1f2937; }
.package-tags,
.selected-tags,
.tag-cell { display: flex; flex-wrap: wrap; gap: 6px; }
.package-tags { margin-top: 10px; }
.package-actions { margin-top: 8px; display: flex; justify-content: flex-end; gap: 8px; }
.right-panel { display: flex; flex-direction: column; gap: 14px; }
.search-card,
.pool-card,
.result-card { border-radius: 14px; box-shadow: 0 8px 24px rgba(15, 23, 42, .04); }
.card-title { display: inline-flex; align-items: center; gap: 8px; font-weight: 700; }
.filter-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.selected-area { margin-top: 12px; justify-content: space-between; align-items: flex-start; }
.selected-title { font-weight: 700; margin-bottom: 8px; }
.pool-tools { margin-bottom: 12px; }
.pool-select { width: 150px; }
.domain-select { width: 180px; }
.pool-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; max-height: 260px; overflow: auto; }
.pool-item { border: 1px solid #edf0f5; border-radius: 10px; padding: 10px; background: #fbfdff; display: flex; flex-direction: column; gap: 8px; }
.pool-name { display: flex; align-items: center; gap: 6px; min-width: 0; font-weight: 600; }
.pool-name span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.result-header { justify-content: space-between; }
.pager { justify-content: flex-end; margin-top: 12px; color: #4b5563; }
.package-modal { width: 640px; }
.modal-tags { min-height: 48px; padding: 8px; border: 1px dashed #d8dee9; border-radius: 10px; }
.detail-section h3 { margin: 0 0 12px; }
.detail-section p { margin: 8px 0; line-height: 1.7; }
.domain-group { margin-bottom: 12px; }
.domain-title { font-weight: 700; color: #374151; margin-bottom: 8px; }
.person-list { display: flex; flex-direction: column; gap: 10px; }
.person-card { border: 1px solid #edf0f5; border-radius: 10px; padding: 10px; background: #fafafa; }
.person-title { justify-content: space-between; font-weight: 700; }
.person-meta { margin: 6px 0; }
@media (max-width: 1280px) {
  .judgment-page { grid-template-columns: 1fr; }
  .package-list { max-height: 360px; }
  .pool-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
