<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Download, PanelRightClose, RefreshCw, Save, Sparkles } from 'lucide-vue-next'
import type { ReportContent } from '@/api/report'
import ReportUmoEditor from '@/components/editor/ReportUmoEditor.vue'
import { useReportStore } from '@/stores/report'

const route = useRoute()
const router = useRouter()
const reportId = Number(route.params.id)
const store = useReportStore()
const html = ref('')

const title = computed(() => store.currentReport?.title || store.editingContent?.title || '警情智能报告')

function contentToHtml(content: ReportContent | null) {
  if (!content) return ''
  return content.sections.map((s) => `<h2>${escapeHtml(s.title)}</h2><p>${escapeHtml(s.content || '')}</p>`).join('')
}

function escapeHtml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

async function generateDraft() {
  const result = await store.generateDraft(reportId, 'monthly', {})
  html.value = contentToHtml(result.draft_json)
}

async function save(value = html.value) {
  const content: ReportContent = {
    title: title.value,
    type: 'html',
    params: {},
    sections: [{ id: 'umo_content', title: '报告正文', type: 'html', content: value, blocks: [], source: [], ai_generated: false }],
  }
  await store.save(reportId, content, value)
  html.value = value
}

onMounted(async () => {
  await store.loadReport(reportId)
  html.value = store.htmlSnapshot || contentToHtml(store.editingContent)
})
</script>

<template>
  <div class="editor-page workbench-bg">
    <header class="editor-header">
      <button class="ghost-btn" @click="router.push('/home/reports')"><ArrowLeft :size="16" /> 返回</button>
      <div class="editor-title">
        <h1>{{ title }}</h1>
        <p>Umo 在线编辑 · AI 草稿需人工确认后保存</p>
      </div>
      <div class="editor-actions">
        <button class="ghost-btn" @click="generateDraft"><Sparkles :size="16" /> AI 草稿</button>
        <button class="ghost-btn"><Download :size="16" /> 导出</button>
        <button class="primary-btn" @click="save()"><Save :size="16" /> 保存</button>
      </div>
    </header>

    <div class="editor-body">
      <aside class="glass-card outline-panel">
        <div class="panel-title">报告大纲</div>
        <div v-if="store.editingContent?.sections.length">
          <button v-for="section in store.editingContent.sections" :key="section.id" class="outline-item">{{ section.title }}</button>
        </div>
        <p v-else class="muted empty-tip">暂无大纲，请生成草稿。</p>
      </aside>

      <main class="editor-center glass-card">
        <ReportUmoEditor v-model="html" :title="title" @save="save" />
      </main>

      <aside class="glass-card ai-panel">
        <div class="panel-title"><PanelRightClose :size="16" /> AI / 数据助手</div>
        <div class="hint">这里放置报告组件、警情数据、AI 润色、敏感表述检查等定制能力。</div>
        <button class="side-action" @click="generateDraft"><RefreshCw :size="16" /> 重新生成全文</button>
        <button class="side-action"><Sparkles :size="16" /> 润色选中段落</button>
        <button class="side-action">插入统计组件</button>
        <button class="side-action">插入典型警情</button>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.editor-page { min-height: 100vh; padding: 18px; }
.editor-header { height: 72px; display: flex; align-items: center; gap: 16px; padding: 0 18px; background: rgba(255,255,255,.82); border-radius: 22px; box-shadow: 0 16px 40px rgba(43,83,140,.10); }
.editor-header button { display: inline-flex; align-items: center; gap: 6px; }
.editor-title { flex: 1; }
.editor-title h1 { margin: 0 0 4px; font-size: 20px; }
.editor-title p { margin: 0; color: #7585a0; font-size: 13px; }
.editor-actions { display: flex; gap: 10px; }
.editor-body { display: grid; grid-template-columns: 230px minmax(0, 1fr) 300px; gap: 14px; margin-top: 14px; min-height: calc(100vh - 104px); }
.outline-panel, .ai-panel { padding: 16px; }
.panel-title { display: flex; align-items: center; gap: 8px; font-weight: 800; margin-bottom: 14px; }
.outline-item { width: 100%; display: block; border: 0; border-radius: 12px; padding: 11px 12px; margin-bottom: 8px; text-align: left; background: #eef6ff; color: #276bdc; cursor: pointer; }
.empty-tip { font-size: 13px; }
.editor-center { overflow: hidden; padding: 0; }
.ai-panel .hint { padding: 12px; border-radius: 14px; background: #fff8e8; color: #8a6626; font-size: 13px; line-height: 1.7; margin-bottom: 14px; }
.side-action { width: 100%; border: 0; border-radius: 14px; padding: 12px; margin-bottom: 10px; background: rgba(255,255,255,.78); color: #34506f; cursor: pointer; display: flex; align-items: center; gap: 8px; }
@media (max-width: 1100px) { .editor-body { grid-template-columns: 1fr; } .outline-panel, .ai-panel { display: none; } }
</style>
