<script setup lang="ts">
import { toRef } from 'vue'
import AgentChatPanel from '@/components/agent-ui/AgentChatPanel.vue'
import { usePiAgentChat } from '@/composables/ai/usePiAgentChat'
import { useMessage } from 'naive-ui'

const props = defineProps<{ reportHtml?: string }>()
const emit = defineEmits<{
  generateDraft: []
  insertHtml: [html: string]
}>()

const message = useMessage()
const { prompt, running, messages, send, stop } = usePiAgentChat(
  (text) => message.error(text),
  toRef(props, 'reportHtml'),
)
const suggestions = [
  { label: '生成全文草稿', prompt: '请分析当前警情智能报告项目，并协助生成一份结构清晰、结论可核验的报告草稿。' },
  { label: '优化当前报告', prompt: '请检查当前报告内容，优化结构、措辞和分析逻辑，并说明修改建议。' },
  { label: '生成研判建议', prompt: '请根据当前报告项目的业务背景，生成可人工核验的警情研判建议。' },
]
</script>

<template>
  <div class="report-pi-assistant">
    <div class="quick-actions">
      <button type="button" @click="emit('generateDraft')">生成全文草稿</button>
      <button type="button" @click="emit('insertHtml', '<p>经综合研判，相关警情总体平稳，需持续关注重点区域和高发时段。</p>')">插入研判建议</button>
    </div>
    <AgentChatPanel
      v-model="prompt"
      :messages="messages"
      :running="running"
      :suggestions="suggestions"
      title="Pi 报告助手"
      assistant-label="Pi Agent"
      placeholder="让 Pi 协助分析报告或修改项目…"
      model-label="本机 Pi"
      tool-label="full"
      thinking-label="auto"
      @submit="send"
      @stop="stop"
    />
  </div>
</template>

<style scoped>
.report-pi-assistant{display:flex;height:100%;min-height:0;flex-direction:column;background:#fff}.quick-actions{display:flex;flex-shrink:0;gap:6px;padding:8px 10px;border-bottom:1px solid #e8eaee;background:#fafbfc}.quick-actions button{flex:1;padding:6px 5px;border:1px solid #d9e9fb;border-radius:6px;background:#f5faff;color:#1677d2;font-size:11px;cursor:pointer}.quick-actions button:hover{border-color:#1890ff;background:#eaf4ff}
</style>
