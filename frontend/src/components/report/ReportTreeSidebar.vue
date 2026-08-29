<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { NButton, NIcon, NTooltip, NTreeSelect } from 'naive-ui'
import { BookOpen, FilePlus2, FileText, FolderOpen, FolderPlus, PanelLeftClose, Pencil, RefreshCw, Trash2 } from 'lucide-vue-next'
import type { ReportFolderItem, ReportItem } from '@/api/report'
import { useDepartmentStore } from '@/stores/department'
import { formatDateTime } from '@/utils/datetime'

const props = defineProps<{
  reports: ReportItem[]
  folders: ReportFolderItem[]
  selectedReportId: number | null
  selectedFolderId: number | null
  collapsed: boolean
}>()

const emit = defineEmits<{
  'update:collapsed': [value: boolean]
  'select-folder': [id: number | null]
  'open-report': [report: ReportItem]
  'create-folder': []
  'create-report': [folderId: number | null]
  'rename-folder': [folder: ReportFolderItem, name: string]
  'rename-report': [report: ReportItem, title: string]
  'delete-folder': [folder: ReportFolderItem]
  'delete-report': [report: ReportItem]
  refresh: []
  templates: []
}>()

const departmentStore = useDepartmentStore()
const folderExpanded = ref(true)
const dept = ref<string | null>(null)
const activeTarget = ref<{ type: 'folder'; id: number } | { type: 'report'; id: number } | null>(null)
const editingTarget = ref<{ type: 'folder'; id: number } | { type: 'report'; id: number } | null>(null)
const editingName = ref('')
const editingInputRef = ref<HTMLInputElement | null>(null)
const deptOptions = computed(() => departmentStore.treeOptions)

const displayReports = computed(() => props.reports)
const reportCount = computed(() => displayReports.value.length)
const visibleFolders = computed(() => props.folders)
const visibleReports = computed(() => {
  if (props.selectedFolderId === null) return displayReports.value
  return displayReports.value.filter((report) => Number(report.folder_id) === Number(props.selectedFolderId))
})

function folderReportCount(folder: ReportFolderItem) {
  return displayReports.value.filter((report) => Number(report.folder_id) === Number(folder.id)).length
}

function canDeleteFolder(folder: ReportFolderItem) {
  return folderReportCount(folder) === 0
}

function chooseFolder(id: number) {
  activeTarget.value = { type: 'folder', id }
  emit('select-folder', id)
  folderExpanded.value = true
}

function openReport(report: ReportItem) {
  if (isEditing('report', report.id)) return
  activeTarget.value = { type: 'report', id: report.id }
  emit('open-report', report)
}

function isEditing(type: 'folder' | 'report', id: number) {
  return editingTarget.value?.type === type && editingTarget.value.id === id
}

function setEditingInputRef(el: Element | { $el?: Element } | null) {
  const node = el && '$el' in el ? el.$el : el
  editingInputRef.value = node instanceof HTMLInputElement ? node : null
}

async function startRenameFolder(folder: ReportFolderItem) {
  activeTarget.value = { type: 'folder', id: folder.id }
  editingTarget.value = { type: 'folder', id: folder.id }
  editingName.value = folder.name
  await nextTick()
  editingInputRef.value?.focus()
  editingInputRef.value?.select()
}

async function startRenameReport(report: ReportItem) {
  activeTarget.value = { type: 'report', id: report.id }
  editingTarget.value = { type: 'report', id: report.id }
  editingName.value = report.title
  await nextTick()
  editingInputRef.value?.focus()
  editingInputRef.value?.select()
}

function cancelRename() {
  editingTarget.value = null
  editingName.value = ''
}

function commitRename() {
  if (!editingTarget.value) return
  const target = editingTarget.value
  const name = editingName.value.trim()
  if (!name) {
    cancelRename()
    return
  }
  if (target.type === 'folder') {
    const folder = props.folders.find((item) => item.id === target.id)
    if (folder && folder.name !== name) emit('rename-folder', folder, name)
  } else {
    const report = props.reports.find((item) => item.id === target.id)
    if (report && report.title !== name) emit('rename-report', report, name)
  }
  cancelRename()
}

function createReportInFolder(folder: ReportFolderItem) {
  emit('create-report', folder.id)
}

watch(
  () => departmentStore.departmentTree,
  (departments) => {
    if (!dept.value && departments.length) dept.value = departments[0].code
  },
  { immediate: true },
)

onMounted(() => {
  departmentStore.loadDepartmentTree().catch(() => {
    // 部门接口不可用时下拉保持空态，不影响目录/报告功能。
  })
})
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <template v-if="!collapsed">
      <div class="sidebar-head">
        <div class="sidebar-title">
          <h3>报告</h3>
          <span class="report-total">({{ reportCount }})</span>
        </div>
        <div class="head-actions">
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button quaternary circle size="small" @click="emit('create-folder')">
                <template #icon><n-icon :component="FolderPlus" :size="16" /></template>
              </n-button>
            </template>
            新建目录
          </n-tooltip>
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button quaternary circle size="small" @click="emit('refresh')">
                <template #icon><n-icon :component="RefreshCw" :size="15" /></template>
              </n-button>
            </template>
            刷新
          </n-tooltip>
        </div>
      </div>

      <div class="dept-wrap">
        <n-tree-select v-model:value="dept" :options="deptOptions" size="medium" default-expand-all />
      </div>

      <div class="tree">
        <div v-if="!visibleFolders.length" class="tree-empty">暂无目录，点击上方新建</div>
        <div
          v-for="folder in visibleFolders"
          :key="folder.id"
          class="folder-row"
          :class="{ active: selectedFolderId === folder.id || (activeTarget?.type === 'folder' && activeTarget.id === folder.id) }"
        >
          <div class="folder-main" role="button" tabindex="0" @click="chooseFolder(folder.id)" @keydown.enter="chooseFolder(folder.id)">
            <n-icon :component="FolderOpen" :size="16" class="folder-icon" />
            <input
              v-if="isEditing('folder', folder.id)"
              :ref="setEditingInputRef"
              v-model="editingName"
              class="inline-rename-input"
              maxlength="40"
              @click.stop
              @keydown.enter.prevent="commitRename"
              @keydown.esc.prevent="cancelRename"
              @blur="commitRename"
            />
            <span v-else>{{ folder.name }}</span>
            <em>{{ folderReportCount(folder) }}</em>
          </div>
          <div class="row-actions">
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button class="row-action row-create" quaternary circle size="tiny" @click.stop="createReportInFolder(folder)">
                  <template #icon><n-icon :component="FilePlus2" :size="14" /></template>
                </n-button>
              </template>
              新建报告
            </n-tooltip>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button class="row-action row-rename" quaternary circle size="tiny" @click.stop="startRenameFolder(folder)">
                  <template #icon><n-icon :component="Pencil" :size="14" /></template>
                </n-button>
              </template>
              重命名目录
            </n-tooltip>
            <n-tooltip v-if="canDeleteFolder(folder)" trigger="hover">
              <template #trigger>
                <n-button class="row-action row-delete" quaternary circle size="tiny" @click.stop="emit('delete-folder', folder)">
                  <template #icon><n-icon :component="Trash2" :size="14" /></template>
                </n-button>
              </template>
              删除目录
            </n-tooltip>
          </div>
        </div>

        <div v-show="folderExpanded" class="file-list">
          <div
            v-for="report in visibleReports"
            :key="report.id"
            class="file-row"
            role="button"
            tabindex="0"
            :class="{ active: selectedReportId === report.id || (activeTarget?.type === 'report' && activeTarget.id === report.id) }"
            @click="openReport(report)"
            @keydown.enter="openReport(report)"
          >
            <n-icon :component="FileText" :size="15" class="file-icon" />
            <div class="file-meta">
              <input
                v-if="isEditing('report', report.id)"
                :ref="setEditingInputRef"
                v-model="editingName"
                class="inline-rename-input report-rename-input"
                maxlength="80"
                @click.stop
                @keydown.enter.prevent="commitRename"
                @keydown.esc.prevent="cancelRename"
                @blur="commitRename"
              />
              <div v-else class="file-title">{{ report.title }}</div>
              <div class="file-time">最后修改于 {{ formatDateTime(report.updated_at) }}</div>
            </div>
            <div class="row-actions report-actions">
              <n-tooltip trigger="hover">
                <template #trigger>
                  <n-button class="row-action row-rename" quaternary circle size="tiny" @click.stop="startRenameReport(report)">
                    <template #icon><n-icon :component="Pencil" :size="14" /></template>
                  </n-button>
                </template>
                重命名报告
              </n-tooltip>
              <n-tooltip trigger="hover">
                <template #trigger>
                  <n-button class="row-action row-delete" quaternary circle size="tiny" @click.stop="emit('delete-report', report)">
                    <template #icon><n-icon :component="Trash2" :size="14" /></template>
                  </n-button>
                </template>
                删除报告
              </n-tooltip>
            </div>
          </div>
        </div>
      </div>

      <div class="sidebar-foot">
        <n-button class="template-btn" secondary block @click="emit('templates')">
          <template #icon><n-icon :component="BookOpen" :size="15" /></template>
          模板库
        </n-button>
        <n-button quaternary circle size="small" @click="emit('update:collapsed', true)">
          <template #icon><n-icon :component="PanelLeftClose" :size="16" /></template>
        </n-button>
      </div>
    </template>

    <n-button v-else type="primary" ghost circle @click="emit('update:collapsed', false)">
      <template #icon><n-icon :component="FileText" :size="18" /></template>
    </n-button>
  </aside>
</template>

<style scoped>
.sidebar { width: var(--sidebar-width); flex-shrink:0; background:#fff; border-right:1px solid #e8e8e8; display:flex; flex-direction:column; min-height:0; transition:width .2s ease; }
.sidebar.collapsed { width:48px; align-items:center; padding-top:12px; }
.sidebar-head { height:48px; padding:0 8px 0 16px; display:flex; align-items:center; justify-content:space-between; flex-shrink:0; }
.sidebar-title { display:flex; align-items:baseline; gap:6px; min-width:0; }
.sidebar-head h3 { margin:0; font-size:16px; font-weight:600; color:#262626; }
.report-total { font-size:12px; color:#8c8c8c; line-height:1; }
.head-actions { display:flex; align-items:center; gap:2px; }
.dept-wrap { padding:0 12px 12px; }
.tree { flex:1; min-height:0; overflow:auto; padding:0 8px 12px; }
.tree-empty { padding:16px 8px; font-size:12px; color:#8c8c8c; text-align:center; }
.folder-row { width:100%; border-radius:4px; display:flex; align-items:center; color:#262626; font-weight:500; }
.folder-row:hover,.folder-row.active { background:#f5f5f5; }
.folder-main { flex:1; min-width:0; border:0; background:transparent; padding:8px; display:flex; align-items:center; gap:8px; color:inherit; text-align:left; font-weight:inherit; cursor:pointer; }
.folder-main:focus-visible,.file-row:focus-visible { outline:2px solid rgba(24,144,255,.35); outline-offset:-2px; }
.folder-main span { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.folder-main em { color:#8c8c8c; font-style:normal; font-size:12px; flex-shrink:0; }
.row-actions { display:flex; align-items:center; gap:2px; margin-right:4px; flex-shrink:0; opacity:0; pointer-events:none; transition:opacity .12s ease; }
.folder-row:hover .row-actions,
.folder-row:focus-within .row-actions,
.file-row:hover .row-actions,
.file-row:focus-within .row-actions { opacity:1; pointer-events:auto; }
.row-action { color:#8c8c8c; }
.row-create:hover,.row-rename:hover { color:#1890ff; }
.row-delete:hover { color:#ff4d4f; }
.folder-icon { color:#faad14; flex-shrink:0; }
.file-list { padding-left:8px; }
.file-row { width:100%; border:0; background:transparent; border-radius:4px; padding:8px 4px 8px 8px; display:flex; align-items:flex-start; gap:8px; text-align:left; margin-bottom:2px; cursor:pointer; }
.file-row:hover,.file-row.active { background:#e6f7ff; }
.file-icon { color:#1890ff; margin-top:2px; flex-shrink:0; }
.file-meta { flex:1; min-width:0; }
.report-actions { margin-top:0; }
.inline-rename-input { flex:1; min-width:0; height:22px; border:1px solid #1890ff; border-radius:3px; padding:0 6px; color:#262626; background:#fff; font:inherit; outline:none; box-shadow:0 0 0 2px rgba(24,144,255,.12); }
.report-rename-input { width:100%; display:block; font-size:13px; }
.file-title { font-size:13px; color:#262626; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.file-row.active .file-title, .file-row:hover .file-title { color:#1890ff; }
.file-time { margin-top:2px; font-size:11px; color:#8c8c8c; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sidebar-foot { height:48px; border-top:1px solid #f0f0f0; padding:8px; display:flex; align-items:center; gap:6px; flex-shrink:0; }
.template-btn { flex:1; }
</style>
