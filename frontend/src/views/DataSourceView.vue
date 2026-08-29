<template>
  <section class="glass-card content-card">
    <div class="section-toolbar">
      <div><h2>数据源</h2><p class="muted">第一版聚焦本地 MySQL 警情库 report，后续扩展外部库和内置接口</p></div>
      <div class="actions"><button class="ghost-btn">测试连接</button><button class="primary-btn">新增数据源</button></div>
    </div>
    <table class="table"><thead><tr><th>名称</th><th>类型</th><th>地址</th><th>说明</th><th>状态</th><th>操作</th></tr></thead><tbody>
      <tr><td>本地 report 库</td><td>MySQL</td><td>127.0.0.1</td><td>报告系统库，警情表后续集中适配</td><td><span class="badge">启用</span></td><td><button class="link-btn">配置</button></td></tr>
      <tr><td>内置统计服务</td><td>API</td><td>/api/v1</td><td>系统内置统计接口</td><td><span class="badge">启用</span></td><td><button class="link-btn">查看</button></td></tr>
    </tbody></table>
  </section>
</template>
<style scoped>
.content-card { padding:22px; }
.section-toolbar { display:flex; justify-content:space-between; gap:16px; margin-bottom:18px; }
h2,p { margin-top:0; }
.actions { display:flex; gap:10px; }
.link-btn { border:0; background:transparent; color:#2878ff; cursor:pointer; }
</style>
