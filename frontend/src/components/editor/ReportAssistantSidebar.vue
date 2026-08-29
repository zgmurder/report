<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { BarChart3, Bot, CalendarDays, Database, FileText, Play, Plus, RefreshCw, Sparkles } from 'lucide-vue-next'
import { useCatalogStore } from '@/stores/catalog'

const emit = defineEmits<{
  generateDraft: []
  insertHtml: [html: string]
}>()

const catalogStore = useCatalogStore()
const activeMode = ref<'atomic' | 'ai'>('atomic')
const runningId = ref<number | null>(null)
const params = reactive({
  dateRange: '近30天',
  unit: '义乌市局',
  dataSource: '本地警情库',
  excludeTraffic: true,
})

const components = computed(() => catalogStore.components)

function typeLabel(type: string) {
  return ({ text: '文本', table: '表格', chart: '图表', api: '接口' } as Record<string, string>)[type] || type
}

async function runComponent(id: number) {
  runningId.value = id
  window.setTimeout(() => {
    runningId.value = null
  }, 450)
}

function insertComponent(name: string, type: string) {
  if (type === 'table') {
    emit('insertHtml', `<h3>${name}</h3><table><tbody><tr><th>类别</th><th>数量</th><th>占比</th></tr><tr><td>示例类别</td><td>0</td><td>0%</td></tr></tbody></table>`)
    return
  }
  if (type === 'chart') {
    emit('insertHtml', `<h3>${name}</h3><p>[图表占位] ${params.unit} ${params.dateRange} 趋势图，待接入真实统计结果。</p>`)
    return
  }
  emit('insertHtml', `<p><strong>${name}：</strong>${params.unit}${params.dateRange}共接报相关警情 0 起，具体数据待统计组件执行后回填。</p>`)
}

onMounted(() => catalogStore.loadComponents())
</script>

<template>
  <aside class="assistant-panel">
    <div class="panel-title"><Bot :size="16" /> AI / 数据助手</div>

    <div class="mode-switch">
      <button :class="{ active: activeMode === 'atomic' }" @click="activeMode = 'atomic'"><BarChart3 :size="15" /> 原子组件</button>
      <button :class="{ active: activeMode === 'ai' }" @click="activeMode = 'ai'"><Sparkles :size="15" /> AI 写作</button>
    </div>

    <section class="param-card">
      <h4>全局参数</h4>
      <label><CalendarDays :size="14" /> 时间范围<input v-model="params.dateRange" /></label>
      <label><FileText :size="14" /> 统计单位<input v-model="params.unit" /></label>
      <label><Database :size="14" /> 数据源<input v-model="params.dataSource" /></label>
      <label class="check-row"><input v-model="params.excludeTraffic" type="checkbox" /> 除交通警情</label>
    </section>

    <section v-if="activeMode === 'atomic'" class="component-list">
      <div class="section-head"><h4>统计组件</h4><button @click="catalogStore.loadComponents"><RefreshCw :size="14" /></button></div>
      <article v-for="item in components" :key="item.id" class="component-card">
        <div>
          <h5>{{ item.name }}</h5>
          <p>{{ typeLabel(item.component_type) }} · {{ item.usage || '通用' }}</p>
        </div>
        <div class="card-actions">
          <button @click="runComponent(item.id)"><Play :size="13" /> {{ runningId === item.id ? '执行中' : '执行' }}</button>
          <button @click="insertComponent(item.name, item.component_type)"><Plus :size="13" /> 插入</button>
        </div>
      </article>
    </section>

    <section v-else class="ai-list">
      <button class="ai-action" @click="emit('generateDraft')"><Sparkles :size="15" /> 生成全文草稿</button>
      <button class="ai-action" @click="emit('insertHtml', '<p>经综合研判，相关警情总体平稳，需持续关注重点区域和高发时段。</p>')">插入研判建议</button>
      <button class="ai-action" @click="emit('insertHtml', '<p>请对以上数据进一步核实，避免直接使用未经确认的 AI 草稿。</p>')">插入核验提示</button>
    </section>
  </aside>
</template>

<style scoped>
.assistant-panel { height:100%; padding:16px; background:rgba(255,255,255,.82); }
.panel-title { display:flex; align-items:center; gap:8px; font-weight:800; margin-bottom:14px; }
.mode-switch { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:14px; }
.mode-switch button { border:0; border-radius:12px; padding:9px 8px; background:#f3f7ff; color:#52647f; display:flex; align-items:center; justify-content:center; gap:5px; }
.mode-switch button.active { color:#1468f6; background:#e7f1ff; font-weight:800; }
.param-card { border-radius:16px; padding:13px; background:#f8fbff; border:1px solid #e7eef8; margin-bottom:14px; }
h4 { margin:0 0 10px; font-size:14px; }
.param-card label { display:grid; gap:5px; color:#66758e; font-size:12px; margin-bottom:9px; }
.param-card label:not(.check-row) { grid-template-columns:16px 68px 1fr; align-items:center; }
.param-card input { min-width:0; border:1px solid #dce7f5; border-radius:9px; padding:6px 8px; outline:none; }
.check-row { display:flex!important; flex-direction:row; align-items:center; gap:7px; }
.section-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; }
.section-head button { width:28px; height:28px; border:0; border-radius:9px; background:#edf5ff; color:#2878ff; }
.component-list, .ai-list { display:grid; gap:10px; }
.component-card { padding:12px; border-radius:15px; background:#fff; border:1px solid #eef3fb; box-shadow:0 8px 20px rgba(43,83,140,.06); }
.component-card h5 { margin:0 0 5px; color:#23324a; }
.component-card p { margin:0 0 10px; color:#8191aa; font-size:12px; }
.card-actions { display:flex; gap:7px; }
.card-actions button, .ai-action { border:0; border-radius:11px; padding:8px 10px; background:#edf5ff; color:#2878ff; display:inline-flex; align-items:center; gap:5px; cursor:pointer; }
.ai-action { width:100%; justify-content:flex-start; background:#fff8e8; color:#8a6626; }
</style>
