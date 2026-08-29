<template>
  <section class="glass-card content-card">
    <div class="section-toolbar">
      <div><h2>统计组件</h2><p class="muted">用 SQL、接口或 AI 模板生成报告中的指标、表格和图表</p></div>
      <div class="actions"><button class="ghost-btn">关系树</button><button class="ghost-btn">测试执行</button><button class="primary-btn">新增组件</button></div>
    </div>
    <div class="filter-row"><input class="input" placeholder="组件名称" /><select class="select"><option>全部类型</option><option>文本</option><option>表格</option><option>图表</option></select><button class="ghost-btn">搜索</button></div>
    <table class="table">
      <thead><tr><th>组件名称</th><th>类型</th><th>数据源</th><th>用途</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="item in items" :key="item.name"><td>{{ item.name }}</td><td>{{ item.type }}</td><td>{{ item.source }}</td><td>{{ item.usage }}</td><td><span class="badge">启用</span></td><td><button class="link-btn">编辑</button><button class="link-btn">预览</button></td></tr>
      </tbody>
    </table>
  </section>
</template>
<script setup lang="ts">
const items = [
  { name: '警情总量', type: '文本', source: '本地警情库', usage: '总体情况' },
  { name: '类别排行', type: '表格', source: '本地警情库', usage: '类别分析' },
  { name: '日趋势', type: '图表', source: '本地警情库', usage: '趋势分析' },
]
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
</style>
