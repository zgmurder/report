<script setup lang="ts">
import { onMounted, ref, h } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NInput, useDialog, useMessage } from 'naive-ui'
import { FilePlus2 } from 'lucide-vue-next'
import type { ReportItem } from '@/api/report'
import ReportTreeSidebar from '@/components/report/ReportTreeSidebar.vue'
import { useReportStore } from '@/stores/report'

const router = useRouter()
const store = useReportStore()
const dialog = useDialog()
const message = useMessage()
const selectedReportId = ref<number | null>(null)
const selectedFolderId = ref<number | null>(null)
const sidebarCollapsed = ref(false)

async function load() {
  try {
    await store.loadReports()
  } catch {
    message.warning('报告列表加载失败，可稍后刷新')
  }
  try {
    await store.loadFolders()
  } catch {
    // 文件夹接口未就绪时不影响首页空态
  }
}

async function createBlank() {
  try {
    const report = await store.createBlankReport('未命名报告', selectedFolderId.value)
    selectedReportId.value = report.id
    router.push(`/home/editor/${report.id}`)
  } catch {
    message.error('新建报告失败，请检查后端服务')
  }
}

function createFolder() {
  const name = ref('新建文件夹')
  dialog.create({
    title: '新建文件夹',
    content: () =>
      h(NInput, {
        value: name.value,
        maxlength: 40,
        placeholder: '请输入文件夹名称',
        'onUpdate:value': (value: string) => {
          name.value = value
        },
      }),
    positiveText: '创建',
    negativeText: '取消',
    onPositiveClick: async () => {
      if (!name.value.trim()) {
        message.warning('请输入文件夹名称')
        return false
      }
      try {
        await store.createFolder(name.value.trim())
        message.success('文件夹已创建')
      } catch {
        message.error('创建文件夹失败')
        return false
      }
    },
  })
}

function openReport(report: ReportItem) {
  selectedReportId.value = report.id
  router.push(`/home/editor/${report.id}`)
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
          <n-icon :component="FilePlus2" :size="48" class="create-icon" />
          <span>新建空白报告</span>
        </button>

        <n-button secondary>
          <template #icon>
            <span class="word-badge">W</span>
          </template>
          导入 Word
        </n-button>

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
.word-badge { width:18px; height:18px; border-radius:3px; background:#2b579a; color:#fff; font-weight:700; font-size:11px; display:inline-flex; align-items:center; justify-content:center; }
.hint { margin:0; color:#8c8c8c; font-size:13px; }
@media (max-width: 900px) { .report-page { flex-direction:column; } .workspace { padding:24px; } }
</style>
