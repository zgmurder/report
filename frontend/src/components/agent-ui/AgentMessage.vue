<script setup>
import { computed, ref } from 'vue'
import AgentToolTimeline from './AgentToolTimeline.vue'

const props = defineProps({
  message: { type: Object, required: true },
  assistantLabel: { type: String, default: 'Agent' },
  userLabel: { type: String, default: '你' },
  thinkingLabel: { type: String, default: '思考过程' },
})
const thinkingOpen = ref(false)
const copied = ref(false)
const label = computed(() => props.message.role === 'user' ? props.userLabel : props.assistantLabel)

async function copyMessage() {
  await navigator.clipboard?.writeText(props.message.content || '')
  copied.value = true
  setTimeout(() => { copied.value = false }, 1500)
}
</script>

<template>
  <article :class="['pi-message', `is-${message.role}`]">
    <div v-if="message.role === 'user'" class="pi-user-wrap">
      <div class="pi-user-bubble">{{ message.content }}</div>
      <div class="pi-message__actions"><button type="button" @click="copyMessage">{{ copied ? '已复制' : '复制' }}</button></div>
    </div>

    <template v-else>
      <div class="pi-assistant-label">
        <span>{{ label }}</span>
        <span v-if="message.running" class="pi-streaming">正在处理</span>
      </div>
      <div class="pi-assistant-blocks">
        <section v-if="message.thinking" class="pi-thinking">
          <button type="button" @click="thinkingOpen = !thinkingOpen">
            <span>{{ thinkingLabel }}</span>
            <span v-if="message.durationMs">{{ (message.durationMs / 1000).toFixed(0) }}s</span>
          </button>
          <pre v-if="thinkingOpen">{{ message.thinking }}</pre>
        </section>
        <AgentToolTimeline :tools="message.tools || []" />
        <div v-if="message.content" class="pi-answer">{{ message.content }}</div>
        <div v-else-if="message.running" class="pi-waiting">Pi 正在处理任务…</div>
        <div v-if="message.error" class="pi-error" role="alert">Error: {{ message.error }}</div>
      </div>
      <div v-if="message.content && !message.running" class="pi-message__actions is-assistant">
        <button type="button" @click="copyMessage">{{ copied ? '已复制' : '复制' }}</button>
        <span v-if="message.durationMs">{{ (message.durationMs / 1000).toFixed(1) }}s</span>
      </div>
    </template>
  </article>
</template>

<style scoped>
.pi-message{margin-bottom:16px;color:var(--agent-text);font-family:var(--agent-font)}.pi-user-wrap{display:flex;flex-direction:column;align-items:flex-end}.pi-user-bubble{max-width:85%;max-height:300px;padding:8px 12px;overflow:auto;border:1px solid color-mix(in srgb,var(--agent-accent) 20%,transparent);border-radius:12px;background:var(--agent-user-bg);color:var(--agent-text);white-space:pre-wrap;word-break:break-word;font-size:14px;line-height:1.6}
.pi-assistant-label{display:flex;align-items:center;gap:6px;margin-bottom:4px;color:var(--agent-text-dim);font-size:11px}.pi-streaming{color:var(--agent-accent);animation:pi-pulse 1.5s infinite}.pi-assistant-blocks{display:flex;flex-direction:column;gap:8px}.pi-answer{min-width:0;max-width:100%;overflow-x:hidden;color:var(--agent-text);white-space:pre-wrap;word-break:break-word;font-size:14px;line-height:1.7}.pi-waiting{padding:2px 0;color:var(--agent-text-muted);font-size:13px;animation:pi-pulse 1.5s infinite}
.pi-thinking{overflow:hidden;border:1px solid var(--agent-border);border-radius:6px;background:var(--agent-panel);font-size:13px}.pi-thinking button{display:flex;width:100%;align-items:center;gap:6px;padding:6px 10px;border:0;background:var(--agent-panel);color:var(--agent-text-muted);font:12px var(--agent-font);text-align:left;cursor:pointer}.pi-thinking button span:last-child{margin-left:auto;color:var(--agent-text-dim);font-size:11px}.pi-thinking pre{margin:0;padding:8px 10px;border-top:1px solid var(--agent-border);color:var(--agent-text-muted);white-space:pre-wrap;font:12px/1.6 var(--agent-font)}
.pi-error{padding:7px 10px;border:1px solid color-mix(in srgb,var(--agent-danger) 30%,transparent);border-radius:6px;background:color-mix(in srgb,var(--agent-danger) 7%,transparent);color:var(--agent-danger);white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 var(--agent-mono)}.pi-message__actions{display:flex;align-items:center;gap:6px;min-height:25px;margin-top:3px;color:var(--agent-text-dim);font-size:10px}.pi-message__actions button{height:22px;padding:3px 8px;border:0;border-radius:5px;background:none;color:var(--agent-text-dim);font:11px var(--agent-font);cursor:pointer;opacity:0;transition:opacity .12s,color .12s}.pi-message:hover .pi-message__actions button{opacity:1}.pi-message__actions button:hover{color:var(--agent-accent)}.pi-message__actions.is-assistant{gap:8px;margin-top:4px}.pi-message__actions.is-assistant span{font-size:11px}
@keyframes pi-pulse{50%{opacity:.5}}
</style>
