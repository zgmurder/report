<template>
  <section class="glass-card content-card">
    <div class="section-toolbar">
      <div><h2>统计组件</h2><p class="muted">用 SQL、接口或 AI 模板生成报告中的指标、表格和图表</p></div>
      <div class="actions"><button class="ghost-btn" disabled title="暂未开放">关系树（暂未开放）</button><button class="ghost-btn" disabled title="暂未开放">测试执行（暂未开放）</button><button class="primary-btn" disabled title="暂未开放">新增组件（暂未开放）</button></div>
    </div>
    <div class="filter-row"><input class="input" disabled placeholder="组件名称（暂未开放）" /><select class="select" disabled title="暂未开放"><option>全部类型</option><option>文本</option><option>表格</option><option>图表</option></select><button class="ghost-btn" disabled title="暂未开放">搜索（暂未开放）</button></div>
    <table class="table">
      <thead><tr><th>组件名称</th><th>类型</th><th>数据源</th><th>用途</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="item in items" :key="item.id"><td>{{ item.name }}</td><td>{{ componentTypeLabel(item.component_type) }}</td><td>{{ item.data_source }}</td><td>{{ item.usage }}</td><td><span class="badge">{{ item.status === 'enabled' ? '启用' : item.status }}</span></td><td><button class="link-btn" disabled title="暂未开放">编辑（暂未开放）</button><button class="link-btn" disabled title="暂未开放">预览（暂未开放）</button></td></tr>
      </tbody>
    </table>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useCatalogStore } from '@/stores/catalog'

const store = useCatalogStore()
const items = computed(() => store.components)

function componentTypeLabel(type: string) {
  return ({ text: '文本', table: '表格', chart: '图表' } as Record<string, string>)[type] || type
}

onMounted(() => store.loadComponents())
</script>
<style scoped>
.content-card { padding:22px; }
.section-toolbar { display:flex; justify-content:space-between; gap:16px; margin-bottom:18px; }
h2,p { margin-top:0; }
.actions,.filter-row { display:flex; gap:10px; align-items:center; }
.filter-row { margin-bottom:14px; }
.filter-row .input { max-width:240px; }
.filter-row .select { max-width:160px; }
.link-btn { border:0; background:transparent; color:#2878ff; cursor:pointer; margin-right:8px; }
button:disabled, input:disabled, select:disabled { cursor:not-allowed; opacity:.55; }
</style>
