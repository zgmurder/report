<script setup>
import { nextTick, ref, watch } from 'vue'
import AgentComposer from './AgentComposer.vue'
import AgentMessage from './AgentMessage.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] }, running: Boolean,
  title: { type: String, default: 'Pi Web' }, assistantLabel: { type: String, default: 'Pi' },
  placeholder: { type: String, default: '输入消息…' }, suggestions: { type: Array, default: () => [] },
  submitLabel: { type: String, default: '发送' }, stopLabel: { type: String, default: '停止' },
  modelLabel: { type: String, default: '' }, toolLabel: { type: String, default: 'full' },
  thinkingLabel: { type: String, default: 'high' },
})
const emit = defineEmits(['submit', 'stop'])
const draft = defineModel({ type: String, default: '' })
const scrollBody = ref(null)

async function scrollBottom() {
  await nextTick()
  scrollBody.value?.scrollTo({ top: scrollBody.value.scrollHeight, behavior: 'smooth' })
}
function submit() {
  const value = draft.value.trim()
  if (!value || props.running) return
  emit('submit', value)
}
function useSuggestion(item) { draft.value = typeof item === 'string' ? item : item.prompt }
watch(() => props.messages.map((m) => [m.content, m.thinking, m.tools?.length, m.running]), scrollBottom, { deep: true })
defineExpose({ scrollBottom })
</script>

<template>
  <section class="pi-chat">
    <div v-if="!messages.length" class="pi-empty">
      <div class="pi-brand"><b>π</b><strong>{{ title }}</strong></div>
      <div class="pi-empty__composer">
        <AgentComposer v-model="draft" v-bind="{ running, placeholder, submitLabel, stopLabel, modelLabel, toolLabel, thinkingLabel }"
          @submit="submit" @stop="emit('stop')" />
      </div>
      <div v-if="suggestions.length" class="pi-suggestions">
        <button v-for="(item,index) in suggestions" :key="index" type="button" @click="useSuggestion(item)">
          {{ typeof item === 'string' ? item : item.label }}
        </button>
      </div>
    </div>

    <template v-else>
      <div ref="scrollBody" class="pi-chat__scroll">
        <main class="pi-chat__messages">
          <AgentMessage v-for="message in messages" :key="message.id" :message="message" :assistant-label="assistantLabel" />
        </main>
      </div>
      <div class="pi-composer-wrap">
        <AgentComposer v-model="draft" v-bind="{ running, placeholder, submitLabel, stopLabel, modelLabel, toolLabel, thinkingLabel }"
          @submit="submit" @stop="emit('stop')" />
      </div>
    </template>
  </section>
</template>

<style scoped>
.pi-chat{--agent-bg:#fff;--agent-panel:#f5f5f5;--agent-hover:#eee;--agent-selected:#e8e8e8;--agent-border:#e0e0e0;--agent-text:#1a1a1a;--agent-text-muted:#6b7280;--agent-text-dim:#9ca3af;--agent-accent:#2563eb;--agent-accent-hover:#1d4ed8;--agent-user-bg:#eff6ff;--agent-success:#16a34a;--agent-danger:#ef4444;--agent-bg-subtle:rgba(0,0,0,.03);--agent-font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;--agent-mono:"JetBrains Mono","Fira Code",Consolas,ui-monospace,"Microsoft YaHei",monospace;display:flex;height:100%;min-width:0;min-height:0;flex-direction:column;overflow:hidden;background:var(--agent-bg);color:var(--agent-text);font:14px var(--agent-font)}
.pi-chat__scroll{min-width:0;min-height:0;flex:1;overflow-x:hidden;overflow-y:auto;padding-top:16px;scrollbar-width:none}.pi-chat__scroll::-webkit-scrollbar{display:none}.pi-chat__messages{width:100%;max-width:820px;margin:0 auto;padding:0 16px}.pi-empty{display:flex;min-height:0;flex:1;flex-direction:column;align-items:center;justify-content:center;overflow-y:auto;padding:32px 16px}.pi-brand{display:flex;width:min(820px,100%);align-items:baseline;gap:10px;margin:0 16px 12px;color:var(--agent-text);font-family:var(--agent-mono)}.pi-brand b{font-size:28px;line-height:1}.pi-brand strong{font-size:22px}.pi-empty__composer{width:100%}.pi-suggestions{display:flex;width:min(820px,100%);flex-wrap:wrap;gap:7px;margin-top:12px}.pi-suggestions button{padding:6px 10px;border:1px solid var(--agent-border);border-radius:7px;background:transparent;color:var(--agent-text-muted);font:12px var(--agent-font);cursor:pointer}.pi-suggestions button:hover{background:var(--agent-hover);color:var(--agent-text)}.pi-composer-wrap{flex-shrink:0;padding:0 16px 8px}
@media(max-width:640px){.pi-chat__messages{padding:0 12px}.pi-composer-wrap{padding:0 8px 8px}}
</style>
