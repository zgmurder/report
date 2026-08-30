<script setup>
import { ref } from 'vue'

defineProps({
  tools: { type: Array, default: () => [] },
  labels: { type: Object, default: () => ({ running: '运行中', success: '完成', error: '失败' }) },
})
const expanded = ref(new Set())

function toggle(id) {
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expanded.value = next
}
</script>

<template>
  <div v-if="tools.length" class="pi-tools">
    <section v-for="tool in tools" :key="tool.id" :class="['pi-tool', `is-${tool.status}`]">
      <button class="pi-tool__header" type="button" @click="toggle(tool.id)">
        <strong>{{ tool.tool || tool.label }}</strong>
        <span class="pi-tool__preview">{{ tool.detail }}</span>
        <span class="pi-tool__state">{{ labels[tool.status] || tool.status }}</span>
        <svg viewBox="0 0 10 10" :class="{ expanded: expanded.has(tool.id) }" aria-hidden="true">
          <polyline points="2 3.5 5 6.5 8 3.5" />
        </svg>
      </button>
      <div v-if="expanded.has(tool.id)" class="pi-tool__expanded">
        <pre v-if="tool.detail">{{ tool.detail }}</pre>
        <pre v-if="tool.output" :class="{ error: tool.status === 'error' }">{{ tool.output }}</pre>
      </div>
    </section>
  </div>
</template>

<style scoped>
.pi-tools{display:flex;flex-direction:column;gap:8px}.pi-tool{overflow:hidden;border:1px solid color-mix(in srgb,var(--agent-success) 25%,transparent);border-radius:7px;background:color-mix(in srgb,var(--agent-success) 4%,transparent);font-size:12px}.pi-tool.is-error{border-color:color-mix(in srgb,var(--agent-danger) 45%,transparent);background:color-mix(in srgb,var(--agent-danger) 5%,transparent)}.pi-tool.is-running{border-color:color-mix(in srgb,var(--agent-accent) 28%,transparent);background:color-mix(in srgb,var(--agent-accent) 4%,transparent)}
.pi-tool__header{display:flex;width:100%;min-width:0;align-items:center;gap:7px;padding:6px 10px;border:0;background:none;color:var(--agent-text-muted);font:12px var(--agent-font);text-align:left;cursor:pointer}.pi-tool__header strong{flex-shrink:0;color:var(--agent-success);font:600 11px var(--agent-mono)}.is-error .pi-tool__header strong{color:var(--agent-danger)}.is-running .pi-tool__header strong{color:var(--agent-accent)}.pi-tool__preview{min-width:0;flex:1;overflow:hidden;color:var(--agent-text-dim);font:11px var(--agent-mono);text-overflow:ellipsis;white-space:nowrap}.pi-tool__state{flex-shrink:0;color:var(--agent-text-dim);font-size:11px}.pi-tool__header svg{width:10px;height:10px;flex-shrink:0;fill:none;stroke:var(--agent-text-dim);stroke-linecap:round;stroke-linejoin:round;stroke-width:1.6;transition:transform .15s}.pi-tool__header svg.expanded{transform:rotate(180deg)}
.pi-tool__expanded{border-top:1px solid color-mix(in srgb,var(--agent-success) 20%,transparent)}.is-error .pi-tool__expanded{border-color:color-mix(in srgb,var(--agent-danger) 25%,transparent)}.pi-tool__expanded pre{max-height:280px;margin:0;padding:8px 10px;overflow:auto;border-top:1px solid var(--agent-border);background:var(--agent-bg-subtle);color:var(--agent-text-muted);white-space:pre-wrap;word-break:break-all;font:12px/1.5 var(--agent-mono)}.pi-tool__expanded pre:first-child{border-top:0}.pi-tool__expanded pre.error{color:var(--agent-danger)}
</style>
