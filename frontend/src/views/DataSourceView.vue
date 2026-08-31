<template>
  <section class="glass-card content-card">
    <div class="section-toolbar">
      <div><h2>数据源</h2><p class="muted">第一版聚焦本地 MySQL 警情库 report，后续扩展外部库和内置接口</p></div>
      <div class="actions"><button class="ghost-btn" disabled title="暂未开放">测试连接（暂未开放）</button><button class="primary-btn" disabled title="暂未开放">新增数据源（暂未开放）</button></div>
    </div>
    <table class="table"><thead><tr><th>名称</th><th>类型</th><th>地址</th><th>说明</th><th>状态</th><th>操作</th></tr></thead><tbody>
      <tr v-for="item in dataSources" :key="item.id">
        <td>{{ item.name }}</td>
        <td>{{ item.source_type }}</td>
        <td>{{ item.address }}</td>
        <td>{{ item.description }}</td>
        <td><span class="badge">{{ item.status === 'enabled' ? '启用' : item.status }}</span></td>
        <td><button class="link-btn" disabled title="暂未开放">配置（暂未开放）</button></td>
      </tr>
    </tbody></table>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useCatalogStore } from '@/stores/catalog'

const store = useCatalogStore()
const dataSources = computed(() => store.dataSources)
const load = () => store.loadDataSources()

onMounted(load)
</script>
<style scoped>
.content-card { padding:22px; }
.section-toolbar { display:flex; justify-content:space-between; gap:16px; margin-bottom:18px; }
h2,p { margin-top:0; }
.actions { display:flex; gap:10px; }
.link-btn { border:0; background:transparent; color:#2878ff; cursor:pointer; }
button:disabled { cursor:not-allowed; opacity:.55; }
</style>
