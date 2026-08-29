<script setup lang="ts">
import { reactive, ref } from 'vue'
import { searchPoliceEvents, type PoliceEventQuery } from '@/api/police'
const query = reactive<PoliceEventQuery>({ keyword: '', event_type: '', page: 1, page_size: 20 })
const rows = ref<unknown[]>([])
async function search() { rows.value = (await searchPoliceEvents(query)).items }
</script>
<template>
  <section class="glass-card content-card">
    <div class="section-toolbar"><div><h2>警情查询</h2><p class="muted">按关键词、类别、时间范围检索本地警情数据</p></div><button class="primary-btn" @click="search">查询</button></div>
    <div class="filter-row"><input v-model="query.keyword" class="input" placeholder="关键词" /><input v-model="query.event_type" class="input" placeholder="警情类别" /></div>
    <table class="table"><thead><tr><th>接警时间</th><th>类别</th><th>单位</th><th>地址</th><th>摘要</th></tr></thead><tbody><tr v-if="rows.length===0"><td colspan="5" class="muted">暂无数据，待接入真实警情表。</td></tr></tbody></table>
  </section>
</template>
<style scoped>
.content-card { padding:22px; } .section-toolbar { display:flex; justify-content:space-between; gap:16px; margin-bottom:18px; } h2,p { margin-top:0; } .filter-row { display:grid; grid-template-columns: 240px 180px; gap:10px; margin-bottom:14px; }
</style>
