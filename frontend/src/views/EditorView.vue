<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { ReportContent, ReportItem } from '@/api/report'
import ReportAssistantSidebar from '@/components/editor/ReportAssistantSidebar.vue'
import ReportUmoEditor from '@/components/editor/ReportUmoEditor.vue'
import ReportTreeSidebar from '@/components/report/ReportTreeSidebar.vue'
import { useReportStore } from '@/stores/report'

const route = useRoute()
const router = useRouter()
const store = useReportStore()

const reportId = computed(() => Number(route.params.id))
const html = ref('')
const sidebarCollapsed = ref(false)
const selectedFolderId = ref<number | null>(null)

const title = computed(() => store.currentReport?.title || store.editingContent?.title || '未命名报告')

function contentToHtml(content: ReportContent | null) {
  if (!content) return `<h1 style="text-align:center;">${escapeHtml(title.value)}</h1><p></p>`
  if (!content.sections?.length) return `<h1 style="text-align:center;">${escapeHtml(content.title || title.value)}</h1><p></p>`
  return content.sections
    .map((s) => `<h2>${escapeHtml(s.title)}</h2><p>${escapeHtml(s.content || '')}</p>`)
    .join('')
}

function escapeHtml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

async function loadAll() {
  try {
    await store.loadReports()
  } catch {
    // ignore
  }
  try {
    await store.loadFolders()
  } catch {
    // 文件夹接口不可用时仍可编辑报告
  }
}

async function loadCurrent() {
  try {
    await store.loadReport(reportId.value)
    selectedFolderId.value = store.currentReport?.folder_id ?? null
    html.value = store.htmlSnapshot || contentToHtml(store.editingContent)
    if (!html.value.trim()) {
      html.value = `<h1 style="text-align:center;">${escapeHtml(title.value)}</h1><p></p>`
    }
  } catch {
    html.value = `<h1 style="text-align:center;">${escapeHtml(title.value)}</h1><p></p>`
  }
}

async function createFolder() {
  const name = window.prompt('请输入文件夹名称', '新建文件夹')
  if (!name?.trim()) return
  await store.createFolder(name.trim())
}

function openReport(report: ReportItem) {
  if (report.id === reportId.value) return
  router.push(`/home/editor/${report.id}`)
}

async function generateDraft() {
  const result = await store.generateDraft(reportId.value, 'monthly', {})
  html.value = contentToHtml(result.draft_json)
}

function insertHtml(fragment: string) {
  html.value = `${html.value || ''}${fragment}`
}

async function save(value = html.value) {
  const content: ReportContent = {
    title: title.value,
    type: 'html',
    params: {},
    sections: [{ id: 'umo_content', title: '报告正文', type: 'html', content: value, blocks: [], source: [], ai_generated: false }],
  }
  await store.save(reportId.value, content, value)
  html.value = value
}

watch(reportId, async (id) => {
  if (!Number.isFinite(id) || id <= 0) return
  await loadCurrent()
})

onMounted(async () => {
  await loadAll()
  await loadCurrent()
})
</script>

<template>
  <div class="editor-page">
    <ReportTreeSidebar
      v-model:collapsed="sidebarCollapsed"
      :reports="store.reports"
      :folders="store.folders"
      :selected-report-id="reportId"
      :selected-folder-id="selectedFolderId"
      @select-folder="selectedFolderId = $event"
      @open-report="openReport"
      @create-folder="createFolder"
      @refresh="loadAll"
      @templates="router.push('/home/templates')"
    />

    <main class="editor-center">
      <ReportUmoEditor :key="reportId" v-model="html" :title="title" @save="save" />
    </main>

    <ReportAssistantSidebar
      @generate-draft="generateDraft"
      @insert-html="insertHtml"
    />
  </div>
</template>

<style scoped>
.editor-page {
  height: 100%;
  display: flex;
  background: #f0f2f5;
  min-height: 0;
}

.editor-center {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

@media (max-width: 1200px) {
  .editor-page :deep(.atomic-panel) {
    width: 280px;
  }
}

@media (max-width: 980px) {
  .editor-page {
    flex-direction: column;
  }
  .editor-page :deep(.sidebar),
  .editor-page :deep(.atomic-panel) {
    width: 100%;
    height: auto;
    max-height: 240px;
    border-left: 0;
    border-right: 0;
  }
}
</style>
