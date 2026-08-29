<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NCard, NForm, NFormItem, NInput, NModal, NSpace, useDialog, useMessage } from 'naive-ui'
import type { ReportContent, ReportFolderItem, ReportItem } from '@/api/report'
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
const sidebarCollapsed = ref(false)
const selectedFolderId = ref<number | null>(null)
const folderModalVisible = ref(false)
const folderName = ref('')
const folderSubmitting = ref(false)

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

function createFolder() {
  folderName.value = ''
  folderModalVisible.value = true
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
    content: folder.report_count > 0
      ? `目录“${folder.name}”下有 ${folder.report_count} 份报告，删除后这些报告将移到未分类，确定删除吗？`
      : `确定删除目录“${folder.name}”吗？`,
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
      @rename-folder="renameFolder"
      @rename-report="renameReport"
      @delete-folder="deleteFolder"
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
