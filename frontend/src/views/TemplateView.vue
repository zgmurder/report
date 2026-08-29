<template>
  <div class="page-wrap">
    <div class="two-column">
      <aside class="glass-card side-tree">
        <h3>模板分类</h3>
        <button v-for="item in types" :key="item" class="tree-item">{{ item }}</button>
      </aside>
      <section class="glass-card content-card">
        <div class="section-toolbar">
          <div><h2>模板库</h2><p class="muted">维护日报、周报、月报和专题研判模板</p></div>
          <div class="actions"><input class="input" placeholder="搜索模板" /><button class="ghost-btn">上传 Word</button><button class="primary-btn">新建模板</button></div>
        </div>
        <div class="template-grid">
          <article v-for="tpl in templates" :key="tpl.name" class="template-card">
            <h3>{{ tpl.name }}</h3><p>{{ tpl.description }}</p><span class="badge">{{ tpl.status === 'enabled' ? '启用' : tpl.status }}</span>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useCatalogStore } from '@/stores/catalog'

const store = useCatalogStore()
const types = ['全部模板', '警情日报', '警情周报', '警情月报', '专题报告']
const templates = computed(() => store.templates)

onMounted(() => store.loadTemplates())
</script>
<style scoped>
.two-column { display: grid; grid-template-columns: 240px 1fr; gap: 16px; min-height: calc(100% - 0px); }
.side-tree, .content-card { padding: 16px; }
.tree-item { width:100%; text-align:left; border:0; background:transparent; padding:8px 12px; border-radius:4px; color:#595959; cursor:pointer; }
.tree-item:hover { background:#e6f7ff; color:#1890ff; }
.section-toolbar { display:flex; justify-content:space-between; gap:16px; margin-bottom:16px; }
h2 { margin:0 0 4px; font-size:18px; font-weight:600; }
h3 { margin:0 0 8px; font-size:14px; }
p { margin:0; }
.actions { display:flex; gap:8px; align-items:center; }
.actions .input { width:220px; }
.template-grid { display:grid; grid-template-columns: repeat(auto-fill,minmax(240px,1fr)); gap:12px; }
.template-card { padding:16px; border-radius:6px; background:#fafafa; border:1px solid #f0f0f0; }
.template-card h3 { margin-bottom:8px; }
.template-card p { color:#8c8c8c; line-height:1.6; margin-bottom:10px; font-size:13px; }
@media (max-width: 900px){ .two-column { grid-template-columns:1fr; } .section-toolbar { flex-direction:column; } }
</style>
