<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NCard, NForm, NFormItem, NInput, NModal, NSpace, useDialog, useMessage } from 'naive-ui'
import { downloadReportDocx, type ReportContent, type ReportEditorConfig, type ReportFolderItem, type ReportItem } from '@/api/report'
import ReportAssistantSidebar from '@/components/editor/ReportAssistantSidebar.vue'
import ReportUmoEditor from '@/components/editor/ReportUmoEditor.vue'
import ReportTreeSidebar from '@/components/report/ReportTreeSidebar.vue'
import { useReportStore } from '@/stores/report'

const route = useRoute()
const router = useRouter()
const store = useReportStore()
const message = useMessage()
const dialog = useDialog()

const reportId = computed(() => Number(route.params.id))
const html = ref('')
const documentJson = ref<Record<string, unknown> | null>(null)
const sidebarCollapsed = ref(false)
const selectedFolderId = ref<number | null>(null)
const folderModalVisible = ref(false)
const folderName = ref('')
const folderSubmitting = ref(false)
const editorConfig = ref<ReportEditorConfig>(createDefaultEditorConfig())
const editorVersion = ref(0)
const editorReady = ref(false)

const title = computed(() => store.currentReport?.title || store.editingContent?.title || '未命名报告')

function isBlankHtml(value: string | null | undefined) {
  if (!value) return true
  const normalized = value
    .replace(/<p><\/p>/gi, '')
    .replace(/<p><br\s*\/?><\/p>/gi, '')
    .replace(/<br\s*\/?\s*>/gi, '')
    .replace(/&nbsp;/gi, '')
    .replace(/<[^>]+>/g, '')
    .trim()
  return normalized.length === 0
}

function sectionToHtml(section: ReportContent['sections'][number]) {
  const content = section.content || ''
  if (section.type === 'html') return content
  if (content.includes('<') && content.includes('>')) return content
  return `<h2>${escapeHtml(section.title)}</h2><p>${escapeHtml(content)}</p>`
}

function contentToHtml(content: ReportContent | null) {
  if (!content) return `<h1 style="text-align:center;">${escapeHtml(title.value)}</h1><p></p>`
  if (!content.sections?.length) return `<h1 style="text-align:center;">${escapeHtml(content.title || title.value)}</h1><p></p>`

  const htmlSections = content.sections.map(sectionToHtml).filter((item) => !isBlankHtml(item))
  if (htmlSections.length) return htmlSections.join('')
  return `<h1 style="text-align:center;">${escapeHtml(content.title || title.value)}</h1><p></p>`
}

function resolveEditorHtml(report: ReportItem | null, content: ReportContent | null) {
  if (!isBlankHtml(report?.html_snapshot)) return report?.html_snapshot || ''
  return contentToHtml(content)
}

function escapeHtml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function cloneEditorDocument(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object') return null
  // Pinia/Vue wraps nested JSON in Proxy objects, which structuredClone cannot clone.
  return JSON.parse(JSON.stringify(value)) as Record<string, unknown>
}

function createDefaultEditorConfig(): ReportEditorConfig {
  return {
    page: {
      orientation: 'portrait',
      margin: { left: 2.54, right: 2.54, top: 2.54, bottom: 2.54 },
      layout: 'page',
      background: '#ffffff',
      size: null,
    },
  }
}

function buildReportContent(value: string, editorDocument = documentJson.value): ReportContent {
  return {
    title: title.value,
    type: 'html',
    params: {
      ...(store.editingContent?.params || {}),
      editor_document: editorDocument,
    },
    sections: [{ id: 'umo_content', title: '报告正文', type: 'html', content: value, blocks: [], source: [], ai_generated: false }],
  }
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
    message.warning('目录列表加载失败，请检查后端服务是否已更新并重启')
  }
}

async function loadCurrent() {
  editorReady.value = false
  try {
    await store.loadReport(reportId.value)
    selectedFolderId.value = store.currentReport?.folder_id ?? null
    editorConfig.value = store.editorConfig || createDefaultEditorConfig()
    const savedDocument = store.editingContent?.params?.editor_document
    documentJson.value = cloneEditorDocument(savedDocument)
    html.value = resolveEditorHtml(store.currentReport, store.editingContent)
    if (isBlankHtml(html.value)) {
      html.value = `<h1 style="text-align:center;">${escapeHtml(title.value)}</h1><p></p>`
    }
    editorVersion.value += 1
    await nextTick()
    editorReady.value = true
  } catch (error) {
    documentJson.value = null
    html.value = ''
    editorReady.value = false
    message.error(error instanceof Error ? `报告内容加载失败：${error.message}` : '报告内容加载失败，请刷新后重试')
  }
}

function createFolder() {
  folderName.value = ''
  folderModalVisible.value = true
}

async function createBlankInFolder(folderId: number | null) {
  try {
    const report = await store.createBlankReport('未命名报告', folderId)
    if (folderId !== null) selectedFolderId.value = folderId
    router.push(`/home/editor/${report.id}`)
  } catch {
    message.error('新建报告失败，请检查后端服务')
  }
}

async function renameFolder(folder: ReportFolderItem, name: string) {
  try {
    await store.renameFolder(folder.id, name)
    message.success('目录已重命名')
  } catch {
    message.error('重命名目录失败')
  }
}

function closeFolderModal() {
  if (folderSubmitting.value) return
  folderModalVisible.value = false
}

async function submitFolder() {
  const name = folderName.value.trim()
  if (!name) {
    message.warning('请输入目录名称')
    return
  }
  try {
    folderSubmitting.value = true
    const folder = await store.createFolder(name)
    selectedFolderId.value = folder.id
    message.success('目录已创建')
    folderModalVisible.value = false
  } catch {
    message.error('创建目录失败')
  } finally {
    folderSubmitting.value = false
  }
}

function deleteFolder(folder: { id: number; name: string; report_count: number }) {
  dialog.warning({
    title: '删除目录',
    content: `确定删除空目录“${folder.name}”吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await store.removeFolder(folder.id)
        if (selectedFolderId.value === folder.id) selectedFolderId.value = null
        message.success('目录已删除')
      } catch {
        message.error('删除目录失败')
      }
    },
  })
}

async function renameReport(report: ReportItem, title: string) {
  try {
    await store.renameReport(report.id, title)
    if (report.id === reportId.value) await store.loadReport(reportId.value)
    message.success('报告已重命名')
  } catch {
    message.error('重命名报告失败')
  }
}

function deleteReport(report: ReportItem) {
  dialog.warning({
    title: '删除报告',
    content: `确定删除报告“${report.title}”吗？删除后不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const deletingCurrent = report.id === reportId.value
        await store.removeReport(report.id)
        message.success('报告已删除')
        if (deletingCurrent) router.push('/home/reports')
      } catch {
        message.error('删除报告失败')
      }
    },
  })
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

async function save(value = html.value, config = editorConfig.value, editorDocument = documentJson.value) {
  editorConfig.value = config
  documentJson.value = editorDocument
  const content = buildReportContent(value, editorDocument)
  await store.save(reportId.value, content, value, config)
  html.value = value
}

async function exportWord(value: string, config = editorConfig.value, editorDocument = documentJson.value) {
  try {
    await save(value, config, editorDocument)
    await downloadReportDocx(reportId.value, title.value)
    message.success('Word 文档已导出')
  } catch {
    message.error('Word 文档导出失败')
  }
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
      @create-report="createBlankInFolder"
      @rename-folder="renameFolder"
      @rename-report="renameReport"
      @delete-folder="deleteFolder"
      @delete-report="deleteReport"
      @refresh="loadAll"
      @templates="router.push('/home/templates')"
    />

    <main class="editor-center">
      <ReportUmoEditor
        v-if="editorReady"
        :key="`${reportId}-${editorVersion}`"
        v-model="html"
        v-model:document-json="documentJson"
        v-model:editor-config="editorConfig"
        :title="title"
        :save-handler="save"
        :export-word-handler="exportWord"
        @save="save"
      />
    </main>

    <ReportAssistantSidebar
      @generate-draft="generateDraft"
      @insert-html="insertHtml"
    />

    <n-modal v-model:show="folderModalVisible" :mask-closable="!folderSubmitting" transform-origin="center">
      <n-card class="folder-modal" title="新建目录" :bordered="false" role="dialog" aria-modal="true">
        <n-form label-placement="top" @submit.prevent="submitFolder">
          <n-form-item label="目录名称" required>
            <n-input
              v-model:value="folderName"
              maxlength="40"
              show-count
              clearable
              autofocus
              placeholder="请输入目录名称"
              @keyup.enter="submitFolder"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button :disabled="folderSubmitting" @click="closeFolderModal">取消</n-button>
            <n-button type="primary" :loading="folderSubmitting" @click="submitFolder">创建</n-button>
          </n-space>
        </template>
      </n-card>
    </n-modal>

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

.folder-modal {
  width: 420px;
  max-width: calc(100vw - 32px);
  border-radius: 8px;
}

@media (max-width: 1200px) {
  .editor-page :deep(.assistant-panel) {
    width: 320px;
  }
}

@media (max-width: 980px) {
  .editor-page {
    flex-direction: column;
  }
  .editor-page :deep(.sidebar),
  .editor-page :deep(.assistant-panel) {
    width: 100%;
    height: auto;
    max-height: 240px;
    border-left: 0;
    border-right: 0;
  }
}
</style>
