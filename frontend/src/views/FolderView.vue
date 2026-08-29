<template>
  <section class="glass-card content-card"><h2>报告目录</h2><p class="muted">用于维护报告文件夹和分组。第一版作为工作台分组入口。</p><div class="folder-grid"><div v-for="f in folders" :key="f" class="folder-card">{{ f }}</div></div></section>
</template>
<script setup lang="ts">
const folders = ['警情日报', '警情周报', '警情月报', '专题研判']
</script>
<style scoped>
.content-card { padding:22px; } h2 { margin-top:0; } .folder-grid { display:grid; grid-template-columns: repeat(auto-fill,minmax(180px,1fr)); gap:14px; margin-top:18px; } .folder-card { padding:22px; border-radius:18px; background:#edf5ff; color:#2878ff; font-weight:800; }
</style>
