<template>
  <section class="glass-card content-card">
    <h2>统计分析</h2>
    <p class="muted">预留总量、趋势、类别、区域、时段分布等图表组件。</p>
    <div class="stat-grid">
      <div v-for="item in stats" :key="item.label" class="stat-card"><span>{{ item.label }}</span><strong>{{ item.value }}</strong></div>
    </div>
  </section>
</template>
<script setup lang="ts">
const stats = [{ label: '警情总量', value: '--' }, { label: '环比变化', value: '--' }, { label: '高发类别', value: '--' }, { label: '重点区域', value: '--' }]
</script>
<style scoped>
.content-card { padding:22px; } h2 { margin-top:0; } .stat-grid { display:grid; grid-template-columns: repeat(4,1fr); gap:14px; margin-top:18px; } .stat-card { padding:18px; border-radius:18px; background:rgba(255,255,255,.72); } .stat-card span { color:#70819c; } .stat-card strong { display:block; margin-top:8px; font-size:26px; }
</style>
