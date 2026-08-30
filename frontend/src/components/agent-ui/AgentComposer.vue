<script setup>
const props = defineProps({
  running: Boolean,
  placeholder: { type: String, default: '输入消息…' },
  submitLabel: { type: String, default: '发送' },
  stopLabel: { type: String, default: '停止' },
  modelLabel: { type: String, default: '' },
  toolLabel: { type: String, default: 'full' },
  thinkingLabel: { type: String, default: 'high' },
})
const emit = defineEmits(['submit', 'stop'])
const draft = defineModel({ type: String, default: '' })

function keydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    if (draft.value.trim() && !props.running) emit('submit')
  }
}
</script>

<template>
  <div class="pi-composer-shell">
    <div class="pi-composer">
      <textarea v-model="draft" rows="1" :placeholder="placeholder" :disabled="running" @keydown="keydown"></textarea>
      <button v-if="running" class="pi-send is-stop" type="button" :title="stopLabel" @click="emit('stop')"><span></span></button>
      <button v-else class="pi-send" type="button" :disabled="!draft.trim()" @click="emit('submit')">
        <svg viewBox="0 0 14 14" aria-hidden="true"><line x1="2" y1="7" x2="11" y2="7"/><polyline points="7.5 3 12 7 7.5 11"/></svg><span>{{ submitLabel }}</span>
      </button>
    </div>
    <div class="pi-controls">
      <div class="pi-controls__left"><button type="button" title="附件">▧</button><span v-if="modelLabel">{{ modelLabel }}</span></div>
      <div class="pi-controls__right"><span>◉ {{ thinkingLabel }}</span><span>⌘ {{ toolLabel }}</span></div>
    </div>
  </div>
</template>

<style scoped>
.pi-composer-shell{max-width:820px;margin:0 auto}.pi-composer{display:flex;min-width:0;align-items:center;gap:8px;padding:10px 10px 10px 14px;border:1px solid color-mix(in srgb,var(--agent-border) 70%,transparent);border-radius:14px;background:var(--agent-bg);box-shadow:0 1px 2px rgba(15,23,42,.04),0 8px 24px -12px rgba(15,23,42,.10)}.pi-composer:focus-within{border-color:color-mix(in srgb,var(--agent-accent) 40%,var(--agent-border));box-shadow:0 0 0 2px color-mix(in srgb,var(--agent-accent) 8%,transparent),0 8px 24px -12px rgba(15,23,42,.10)}.pi-composer textarea{min-width:0;min-height:24px;max-height:200px;flex:1;resize:none;overflow:auto;border:0;outline:0;background:none;color:var(--agent-text);font:14px/1.6 var(--agent-font)}.pi-composer textarea::placeholder{color:var(--agent-text-dim)}
.pi-send{display:flex;flex-shrink:0;align-self:flex-end;align-items:center;gap:6px;padding:7px 14px;border:0;border-radius:8px;background:var(--agent-accent);color:#fff;font:600 13px var(--agent-font);cursor:pointer;box-shadow:0 1px 3px rgba(37,99,235,.25)}.pi-send:disabled{background:var(--agent-panel);color:var(--agent-text-dim);cursor:not-allowed;box-shadow:none}.pi-send svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round;stroke-width:2}.pi-send.is-stop{display:grid;width:32px;height:32px;padding:0;place-items:center;background:var(--agent-panel);box-shadow:none}.pi-send.is-stop span{width:10px;height:10px;border-radius:2px;background:var(--agent-text-muted)}
.pi-controls{display:flex;align-items:center;gap:6px;margin-top:8px;color:var(--agent-text-muted);font-size:11px}.pi-controls__left,.pi-controls__right{display:flex;align-items:center;gap:7px}.pi-controls__right{margin-left:auto}.pi-controls button{display:grid;width:32px;height:32px;padding:0;place-items:center;border:0;border-radius:9px;background:none;color:var(--agent-text-muted);cursor:pointer}.pi-controls button:hover{background:var(--agent-hover);color:var(--agent-text)}.pi-controls span{white-space:nowrap}
@media(max-width:640px){.pi-send>span{display:none}.pi-send{width:34px;height:34px;padding:0;justify-content:center}.pi-controls__right{gap:4px}}
</style>
