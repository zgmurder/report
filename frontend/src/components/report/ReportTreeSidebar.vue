<script setup lang="ts">
import { computed, ref } from 'vue'
import { BookOpen, ChevronDown, FileText, FolderOpen, FolderPlus, PanelLeftClose, RefreshCw } from 'lucide-vue-next'
import type { ReportFolderItem, ReportItem } from '@/api/report'

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
  refresh: []
  templates: []
}>()

const folderExpanded = ref(true)
const deptLabel = '义乌市局'

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
  emit('select-folder', props.selectedFolderId === id ? null : id)
  folderExpanded.value = true
}
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <template v-if="!collapsed">
      <div class="sidebar-head">
        <h3>报告</h3>
        <div class="head-actions">
          <button class="icon-btn" type="button" title="新建文件夹" @click="emit('create-folder')"><FolderPlus :size="16" /></button>
          <button class="icon-btn" type="button" title="刷新" @click="emit('refresh')"><RefreshCw :size="15" /></button>
        </div>
      </div>

      <button class="dept-select" type="button"><span>{{ deptLabel }}</span><ChevronDown :size="14" /></button>

      <div class="tree">
        <div class="tree-summary">全部报告 ({{ reportCount }})</div>
        <button v-for="folder in visibleFolders" :key="folder.id" class="folder-row" type="button" :class="{ active: selectedFolderId === folder.id }" @click="chooseFolder(folder.id)">
          <FolderOpen :size="16" class="folder-icon" />
          <span>{{ folder.name }}</span>
          <em>{{ folder.report_count }}</em>
        </button>

        <div v-show="folderExpanded" class="file-list">
          <button v-for="report in visibleReports" :key="report.id" class="file-row" type="button" :class="{ active: selectedReportId === report.id }" @click="emit('open-report', report)">
            <FileText :size="15" class="file-icon" />
            <div class="file-meta">
              <div class="file-title">{{ report.title }}</div>
              <div class="file-time">最后修改于 {{ formatTime(report.updated_at) }}</div>
            </div>
          </button>
        </div>
      </div>

      <div class="sidebar-foot">
        <button class="template-btn" type="button" @click="emit('templates')"><BookOpen :size="15" /><span>模板库</span></button>
        <button class="icon-btn collapse-btn" type="button" title="收起侧栏" @click="emit('update:collapsed', true)"><PanelLeftClose :size="16" /></button>
      </div>
    </template>

    <button v-else class="expand-btn" type="button" title="展开侧栏" @click="emit('update:collapsed', false)"><FileText :size="18" /></button>
  </aside>
</template>

<style scoped>
.sidebar { width: var(--sidebar-width); flex-shrink:0; background:#fff; border-right:1px solid #e8e8e8; display:flex; flex-direction:column; min-height:0; transition:width .2s ease; }
.sidebar.collapsed { width:48px; align-items:center; padding-top:12px; }
.sidebar-head { height:48px; padding:0 12px 0 16px; display:flex; align-items:center; justify-content:space-between; flex-shrink:0; }
.sidebar-head h3 { margin:0; font-size:16px; font-weight:600; color:#262626; }
.head-actions { display:flex; align-items:center; gap:2px; }
.icon-btn { width:28px; height:28px; border:0; border-radius:4px; background:transparent; color:#595959; display:inline-flex; align-items:center; justify-content:center; }
.icon-btn:hover { color:#1890ff; background:#e6f7ff; }
.dept-select { margin:0 12px 12px; height:32px; border:1px solid #d9d9d9; border-radius:4px; background:#fff; display:flex; align-items:center; justify-content:space-between; padding:0 10px; color:#262626; }
.tree { flex:1; min-height:0; overflow:auto; padding:0 8px 12px; }
.tree-summary { padding:6px 8px 10px; font-size:12px; color:#8c8c8c; }
.folder-row { width:100%; border:0; background:transparent; border-radius:4px; padding:8px; display:flex; align-items:center; gap:8px; color:#262626; text-align:left; font-weight:500; }
.folder-row:hover,.folder-row.active { background:#f5f5f5; }
.folder-row span { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.folder-row em { color:#8c8c8c; font-style:normal; font-size:12px; }
.folder-icon { color:#faad14; flex-shrink:0; }
.file-list { padding-left:8px; }
.file-row { width:100%; border:0; background:transparent; border-radius:4px; padding:8px; display:flex; align-items:flex-start; gap:8px; text-align:left; margin-bottom:2px; }
.file-row:hover,.file-row.active { background:#e6f7ff; }
.file-icon { color:#1890ff; margin-top:2px; flex-shrink:0; }
.file-meta { min-width:0; }
.file-title { font-size:13px; color:#262626; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.file-time { margin-top:2px; font-size:11px; color:#8c8c8c; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sidebar-foot { height:48px; border-top:1px solid #f0f0f0; padding:8px; display:flex; align-items:center; gap:6px; flex-shrink:0; }
.template-btn { flex:1; height:32px; border:0; border-radius:4px; background:#f5f5f5; color:#595959; display:flex; align-items:center; justify-content:center; gap:6px; }
.template-btn:hover { color:#1890ff; background:#e6f7ff; }
.collapse-btn { flex-shrink:0; }
.expand-btn { width:36px; height:36px; border:0; border-radius:8px; background:#e6f7ff; color:#1890ff; display:flex; align-items:center; justify-content:center; }
</style>
