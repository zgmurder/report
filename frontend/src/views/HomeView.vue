<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { FilePlus2 } from 'lucide-vue-next'
import type { ReportItem } from '@/api/report'
import ReportTreeSidebar from '@/components/report/ReportTreeSidebar.vue'
import { useReportStore } from '@/stores/report'

const router = useRouter()
const store = useReportStore()
const selectedReportId = ref<number | null>(null)
const selectedFolderId = ref<number | null>(null)
const sidebarCollapsed = ref(false)

async function load() {
  try {
    await Promise.all([store.loadReports(), store.loadFolders()])
  } catch {
    // 首页保留空态，错误提示后续统一接入 message 组件。
  }
}

async function createBlank() {
  try {
    const report = await store.createBlankReport('未命名报告', selectedFolderId.value)
    selectedReportId.value = report.id
    router.push(`/editor/${report.id}`)
  } catch {
    // API 不可用时仍保留界面交互反馈。
  }
}

async function createFolder() {
  const name = window.prompt('请输入文件夹名称', '新建文件夹')
  if (!name?.trim()) return
  await store.createFolder(name.trim())
}

function openReport(report: ReportItem) {
  selectedReportId.value = report.id
  router.push(`/editor/${report.id}`)
}

onMounted(load)
</script>

<template>
  <div class="report-page">
    <ReportTreeSidebar
      v-model:collapsed="sidebarCollapsed"
      :reports="store.reports"
      :folders="store.folders"
      :selected-report-id="selectedReportId"
      :selected-folder-id="selectedFolderId"
      @select-folder="selectedFolderId = $event"
      @open-report="openReport"
      @create-folder="createFolder"
      @refresh="load"
      @templates="router.push('/home/templates')"
    />

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
.report-page { height:100%; display:flex; background:var(--color-bg); }
.workspace { flex:1; min-width:0; height:100%; overflow:auto; display:flex; align-items:center; justify-content:center; padding:32px; }
.empty-stage { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:18px; min-height:420px; color:#8c8c8c; }
.create-card { width:168px; height:132px; border:1px dashed #adc6ff; border-radius:8px; background:#fff; color:#1890ff; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:12px; font-size:15px; box-shadow:0 4px 12px rgba(24,144,255,.08); transition:all .2s; }
.create-card:hover { border-color:#1890ff; box-shadow:0 8px 24px rgba(24,144,255,.16); transform:translateY(-1px); }
.create-icon { color:#1890ff; }
.import-btn { min-width:126px; height:36px; border:0; border-radius:4px; background:#fff; color:#262626; display:flex; align-items:center; justify-content:center; gap:8px; box-shadow:0 1px 4px rgba(0,0,0,.08); }
.import-btn:hover { color:#1890ff; box-shadow:0 4px 12px rgba(24,144,255,.16); }
.word-badge { width:20px; height:20px; border-radius:3px; background:#2b579a; color:#fff; font-weight:700; font-size:12px; display:inline-flex; align-items:center; justify-content:center; }
.hint { margin:0; color:#8c8c8c; font-size:13px; }
@media (max-width: 900px) { .report-page { flex-direction:column; } .workspace { padding:24px; } }
</style>
