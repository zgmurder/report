<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  BookOpen,
  ChevronDown,
  FilePlus2,
  FileText,
  FolderOpen,
  FolderPlus,
  PanelLeftClose,
  RefreshCw,
} from 'lucide-vue-next'
import { createReport, listReports, type ReportItem } from '@/api/report'

const router = useRouter()
const reports = ref<ReportItem[]>([])
const selectedReportId = ref<number | null>(null)
const sidebarCollapsed = ref(false)
const folderExpanded = ref(true)
const deptLabel = '义乌市局'

const displayReports = computed(() => {
  if (reports.value.length > 0) return reports.value
  return [
    {
      id: -1,
      title: '未命名报告',
      report_type: 'incident',
      status: 'draft',
      created_at: '2024-07-29 21:47:32',
      updated_at: '2024-07-29 21:47:32',
    },
    {
      id: -2,
      title: '结果报告按生成报告',
      report_type: 'incident',
      status: 'draft',
      created_at: '2024-07-29 21:39:55',
      updated_at: '2024-07-29 21:39:55',
    },
  ] as ReportItem[]
})

const reportCount = computed(() => displayReports.value.length)

function formatTime(value: string) {
  if (!value) return ''
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) {
    return value.replace('T', ' ').replace(/\.\d+$/, '').slice(0, 19)
  }
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function load() {
  try {
    reports.value = await listReports()
  } catch {
    reports.value = []
  }
}

async function createBlank() {
  try {
    const report = await createReport({ title: '未命名报告', report_type: 'incident', source_query: {} })
    await load()
    selectedReportId.value = report.id
    router.push(`/editor/${report.id}`)
  } catch {
    // API 不可用时仍保留界面交互反馈
  }
}

function openReport(report: ReportItem) {
  if (report.id < 0) return
  selectedReportId.value = report.id
  router.push(`/editor/${report.id}`)
}

function goTemplates() {
  router.push('/home/templates')
}

async function refresh() {
  await load()
}

onMounted(load)
</script>

<template>
  <div class="report-page">
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <template v-if="!sidebarCollapsed">
        <div class="sidebar-head">
          <h3>报告</h3>
          <div class="head-actions">
            <button class="icon-btn" type="button" title="新建文件夹">
              <FolderPlus :size="16" :stroke-width="1.75" />
            </button>
            <button class="icon-btn" type="button" title="刷新" @click="refresh">
              <RefreshCw :size="15" :stroke-width="1.75" />
            </button>
          </div>
        </div>

        <button class="dept-select" type="button">
          <span>{{ deptLabel }}</span>
          <ChevronDown :size="14" :stroke-width="1.75" />
        </button>

        <div class="tree">
          <div class="tree-summary">全部报告 ({{ reportCount }})</div>

          <button class="folder-row" type="button" @click="folderExpanded = !folderExpanded">
            <FolderOpen :size="16" :stroke-width="1.75" class="folder-icon" />
            <span>测试报告</span>
          </button>

          <div v-show="folderExpanded" class="file-list">
            <button
              v-for="report in displayReports"
              :key="report.id"
              class="file-row"
              type="button"
              :class="{ active: selectedReportId === report.id }"
              @click="openReport(report)"
            >
              <FileText :size="15" :stroke-width="1.75" class="file-icon" />
              <div class="file-meta">
                <div class="file-title">{{ report.title }}</div>
                <div class="file-time">最后修改于 {{ formatTime(report.updated_at) }}</div>
              </div>
            </button>
          </div>
        </div>

        <div class="sidebar-foot">
          <button class="template-btn" type="button" @click="goTemplates">
            <BookOpen :size="15" :stroke-width="1.75" />
            <span>模板库</span>
          </button>
          <button class="icon-btn collapse-btn" type="button" title="收起侧栏" @click="sidebarCollapsed = true">
            <PanelLeftClose :size="16" :stroke-width="1.75" />
          </button>
        </div>
      </template>

      <button v-else class="expand-btn" type="button" title="展开侧栏" @click="sidebarCollapsed = false">
        <FileText :size="18" :stroke-width="1.75" />
      </button>
    </aside>

    <section class="workspace">
      <div class="empty-stage">
        <button class="create-card" type="button" @click="createBlank">
          <FilePlus2 :size="48" :stroke-width="1.5" class="create-icon" />
          <span>新建空白报告</span>
        </button>

        <button class="import-btn" type="button">
          <span class="word-badge">W</span>
          <span>导入 Word</span>
        </button>

        <p class="hint">输入或导入 docx 公共或内置模板，然后从列表中选择该模板。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.report-page {
  height: 100%;
  display: flex;
  background: var(--color-bg);
}

.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  min-height: 0;
  transition: width .2s ease;
}

.sidebar.collapsed {
  width: 48px;
  align-items: center;
  padding-top: 12px;
}

.sidebar-head {
  height: 48px;
  padding: 0 12px 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.sidebar-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #262626;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.icon-btn {
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #8c8c8c;
  display: grid;
  place-items: center;
  padding: 0;
}

.icon-btn:hover {
  color: var(--color-primary);
  background: #f5f5f5;
}

.dept-select {
  margin: 0 12px 8px;
  height: 32px;
  padding: 0 11px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #262626;
  flex-shrink: 0;
}

.dept-select:hover {
  border-color: var(--color-primary-hover);
}

.tree {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 4px 8px 12px;
}

.tree-summary {
  padding: 6px 8px 10px;
  font-size: 12px;
  color: #8c8c8c;
}

.folder-row {
  width: 100%;
  border: 0;
  background: transparent;
  border-radius: 4px;
  padding: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #262626;
  text-align: left;
  font-weight: 500;
}

.folder-row:hover {
  background: #f5f5f5;
}

.folder-icon {
  color: #faad14;
  flex-shrink: 0;
}

.file-list {
  padding-left: 8px;
}

.file-row {
  width: 100%;
  border: 0;
  background: transparent;
  border-radius: 4px;
  padding: 8px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  text-align: left;
  margin-bottom: 2px;
}

.file-row:hover,
.file-row.active {
  background: #e6f7ff;
}

.file-icon {
  color: var(--color-primary);
  margin-top: 2px;
  flex-shrink: 0;
}

.file-meta {
  min-width: 0;
  flex: 1;
}

.file-title {
  color: var(--color-primary);
  font-size: 13px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-row:hover .file-title,
.file-row.active .file-title {
  color: #096dd9;
}

.file-time {
  margin-top: 2px;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.4;
}

.sidebar-foot {
  flex-shrink: 0;
  padding: 10px 12px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.template-btn {
  flex: 1;
  height: 36px;
  border: 0;
  border-radius: 4px;
  background: #e6f7ff;
  color: var(--color-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-weight: 500;
}

.template-btn:hover {
  background: #bae7ff;
}

.collapse-btn {
  flex-shrink: 0;
}

.expand-btn {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 4px;
  background: #e6f7ff;
  color: var(--color-primary);
  display: grid;
  place-items: center;
}

.workspace {
  flex: 1;
  min-width: 0;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  transform: translateY(-24px);
}

.create-card {
  width: 160px;
  height: 160px;
  border: 1px solid #91d5ff;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, .08);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #262626;
  transition: border-color .2s, box-shadow .2s, color .2s;
}

.create-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 4px 12px rgba(24, 144, 255, .16);
  color: var(--color-primary);
}

.create-icon {
  color: var(--color-primary);
}

.create-card span {
  font-size: 14px;
}

.import-btn {
  width: 160px;
  height: 36px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fff;
  color: #262626;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: border-color .2s, color .2s;
}

.import-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.word-badge {
  width: 18px;
  height: 18px;
  border-radius: 2px;
  background: #2b579a;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: grid;
  place-items: center;
  line-height: 1;
  font-family: Arial, sans-serif;
}

.hint {
  margin: 4px 0 0;
  max-width: 360px;
  text-align: center;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .sidebar:not(.collapsed) {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 20;
    box-shadow: 2px 0 8px rgba(0, 0, 0, .08);
  }
}
</style>
