<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { NButton, NIcon, NTooltip, NTreeSelect } from 'naive-ui'
import { BookOpen, FileText, FolderOpen, FolderPlus, PanelLeftClose, Pencil, RefreshCw, Trash2 } from 'lucide-vue-next'
import type { ReportFolderItem, ReportItem } from '@/api/report'
import { useDepartmentStore } from '@/stores/department'

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
  'rename-folder': [folder: ReportFolderItem, name: string]
  'rename-report': [report: ReportItem, title: string]
  'delete-folder': [folder: ReportFolderItem]
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
const visibleFolders = computed(() =>
  props.folders.length
    ? props.folders
    : [{ id: 0, name: '未分类', parent_id: null, sort_order: 0, report_count: displayReports.value.length, created_at: '', updated_at: '' }],
)
const visibleReports = computed(() =>
  props.selectedFolderId ? displayReports.value.filter((report) => report.folder_id === props.selectedFolderId) : displayReports.value,
)

function formatTime(value: string) {
  if (!value) return ''
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return value.replace('T', ' ').replace(/\.\d+$/, '').slice(0, 19)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function chooseFolder(id: number) {
  const nextId = id === 0 || props.selectedFolderId === id ? null : id
  activeTarget.value = id === 0 ? null : { type: 'folder', id }
  emit('select-folder', nextId)
  folderExpanded.value = true
}

function openReport(report: ReportItem) {
  if (isEditing('report', report.id)) return
  activeTarget.value = { type: 'report', id: report.id }
  emit('open-report', report)
}

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName.toLowerCase()
  return tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable || !!target.closest('[contenteditable="true"]')
}

function isEditing(type: 'folder' | 'report', id: number) {
  return editingTarget.value?.type === type && editingTarget.value.id === id
}

async function startRenameFolder(folder: ReportFolderItem) {
  if (folder.id === 0) return
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

function renameActiveTarget() {
  if (activeTarget.value?.type === 'report') {
    const report = props.reports.find((item) => item.id === activeTarget.value?.id)
    if (report) {
      startRenameReport(report)
      return
    }
  }
  if (activeTarget.value?.type === 'folder') {
    const folder = props.folders.find((item) => item.id === activeTarget.value?.id)
    if (folder) {
      startRenameFolder(folder)
      return
    }
  }
  const selectedReport = props.reports.find((item) => item.id === props.selectedReportId)
  if (selectedReport) {
    startRenameReport(selectedReport)
    return
  }
  const selectedFolder = props.folders.find((item) => item.id === props.selectedFolderId)
  if (selectedFolder) startRenameFolder(selectedFolder)
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

function handleKeydown(event: KeyboardEvent) {
  if (event.key !== 'F2' || props.collapsed || isEditableTarget(event.target)) return
  event.preventDefault()
  renameActiveTarget()
}

watch(
  () => departmentStore.departmentTree,
  (departments) => {
    if (!dept.value && departments.length) dept.value = departments[0].code
  },
  { immediate: true },
)

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  departmentStore.loadDepartmentTree().catch(() => {
    // 部门接口不可用时下拉保持空态，不影响目录/报告功能。
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <template v-if="!collapsed">
      <div class="sidebar-head">
        <h3>报告</h3>
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
        <div class="tree-summary">全部报告 ({{ reportCount }})</div>
        <div
          v-for="folder in visibleFolders"
          :key="folder.id"
          class="folder-row"
          :class="{ active: selectedFolderId === folder.id }"
        >
          <div class="folder-main" role="button" tabindex="0" @click="chooseFolder(folder.id)" @keydown.enter="chooseFolder(folder.id)">
            <n-icon :component="FolderOpen" :size="16" class="folder-icon" />
            <input
              v-if="isEditing('folder', folder.id)"
              ref="editingInputRef"
              v-model="editingName"
              class="inline-rename-input"
              maxlength="40"
              @click.stop
              @keydown.enter.prevent="commitRename"
              @keydown.esc.prevent="cancelRename"
              @blur="commitRename"
            />
            <span v-else>{{ folder.name }}</span>
            <em>{{ folder.report_count }}</em>
          </div>
          <div v-if="folder.id !== 0" class="folder-actions">
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button class="folder-action folder-rename" quaternary circle size="tiny" @click.stop="startRenameFolder(folder)">
                  <template #icon><n-icon :component="Pencil" :size="14" /></template>
                </n-button>
              </template>
              重命名目录
            </n-tooltip>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button class="folder-action folder-delete" quaternary circle size="tiny" @click.stop="emit('delete-folder', folder)">
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
            :class="{ active: selectedReportId === report.id }"
            @click="openReport(report)"
            @keydown.enter="openReport(report)"
          >
            <n-icon :component="FileText" :size="15" class="file-icon" />
            <div class="file-meta">
              <input
                v-if="isEditing('report', report.id)"
                ref="editingInputRef"
                v-model="editingName"
                class="inline-rename-input report-rename-input"
                maxlength="80"
                @click.stop
                @keydown.enter.prevent="commitRename"
                @keydown.esc.prevent="cancelRename"
                @blur="commitRename"
              />
              <div v-else class="file-title">{{ report.title }}</div>
              <div class="file-time">最后修改于 {{ formatTime(report.updated_at) }}</div>
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
.sidebar-head h3 { margin:0; font-size:16px; font-weight:600; color:#262626; }
.head-actions { display:flex; align-items:center; gap:2px; }
.dept-wrap { padding:0 12px 12px; }
.tree { flex:1; min-height:0; overflow:auto; padding:0 8px 12px; }
.tree-summary { padding:6px 8px 10px; font-size:12px; color:#8c8c8c; }
.folder-row { width:100%; border-radius:4px; display:flex; align-items:center; color:#262626; font-weight:500; }
.folder-row:hover,.folder-row.active { background:#f5f5f5; }
.folder-main { flex:1; min-width:0; border:0; background:transparent; padding:8px; display:flex; align-items:center; gap:8px; color:inherit; text-align:left; font-weight:inherit; cursor:pointer; }
.folder-main:focus-visible,.file-row:focus-visible { outline:2px solid rgba(24,144,255,.35); outline-offset:-2px; }
.folder-main span { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.folder-main em { color:#8c8c8c; font-style:normal; font-size:12px; }
.folder-actions { display:flex; align-items:center; gap:2px; margin-right:4px; opacity:0; }
.folder-row:hover .folder-actions { opacity:1; }
.folder-action { color:#8c8c8c; }
.folder-rename:hover { color:#1890ff; }
.folder-delete:hover { color:#ff4d4f; }
.folder-icon { color:#faad14; flex-shrink:0; }
.file-list { padding-left:8px; }
.file-row { width:100%; border:0; background:transparent; border-radius:4px; padding:8px; display:flex; align-items:flex-start; gap:8px; text-align:left; margin-bottom:2px; cursor:pointer; }
.file-row:hover,.file-row.active { background:#e6f7ff; }
.file-icon { color:#1890ff; margin-top:2px; flex-shrink:0; }
.file-meta { flex:1; min-width:0; }
.inline-rename-input { flex:1; min-width:0; height:22px; border:1px solid #1890ff; border-radius:3px; padding:0 6px; color:#262626; background:#fff; font:inherit; outline:none; box-shadow:0 0 0 2px rgba(24,144,255,.12); }
.report-rename-input { width:100%; display:block; font-size:13px; }
.file-title { font-size:13px; color:#262626; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.file-row.active .file-title, .file-row:hover .file-title { color:#1890ff; }
.file-time { margin-top:2px; font-size:11px; color:#8c8c8c; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sidebar-foot { height:48px; border-top:1px solid #f0f0f0; padding:8px; display:flex; align-items:center; gap:6px; flex-shrink:0; }
.template-btn { flex:1; }
</style>
