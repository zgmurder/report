<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { NAvatar, NButton, NIcon } from 'naive-ui'
import { History, UserRound } from 'lucide-vue-next'
import { workbenchNavItems } from '@/data/navigation'

const route = useRoute()
const router = useRouter()

function isActive(path: string) {
  if (path === '/home/reports') {
    return route.path.startsWith('/home/reports') || route.path.startsWith('/home/editor')
  }
  return route.path === path || route.path.startsWith(`${path}/`)
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand" @click="router.push('/home/reports')">
        <img class="brand-logo" src="/logo-police.svg" alt="logo" width="40" height="40" />
        <div class="brand-text">
          <div class="brand-org">义乌市公安局</div>
          <div class="brand-name">警情智能辅助分析系统</div>
        </div>
      </div>

      <nav class="main-nav">
        <button
          v-for="item in workbenchNavItems"
          :key="item.key"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          @click="router.push(item.path)"
        >
          <component :is="item.icon" :size="18" :stroke-width="1.75" />
          <span>{{ item.title }}</span>
        </button>
      </nav>

      <div class="top-actions">
        <n-button text>
          <template #icon><n-icon :component="History" :size="15" /></template>
          更新日志
        </n-button>
        <div class="user-block">
          <n-avatar round size="small" :style="{ background: '#f0f0f0', color: '#8c8c8c' }">
            <n-icon :component="UserRound" :size="16" />
          </n-avatar>
          <div class="user-meta">
            <div class="user-name">ywj</div>
            <div class="user-org">义乌市局</div>
          </div>
        </div>
      </div>
    </header>

    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>


<style scoped>
.app-shell {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
}

.topbar {
  height: var(--header-height);
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  padding: 0 20px 0 16px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  box-shadow: 0 1px 4px rgba(0, 21, 41, .08);
  z-index: 100;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 260px;
  cursor: pointer;
  padding-right: 12px;
}

.brand-logo {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: block;
}

.brand-org {
  font-size: 12px;
  line-height: 1.2;
  color: #595959;
}

.brand-name {
  margin-top: 2px;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.25;
  color: #262626;
  letter-spacing: .3px;
}

.main-nav {
  flex: 1;
  display: flex;
  justify-content: flex-start;
  align-items: stretch;
  gap: 4px;
}

.nav-item {
  position: relative;
  min-width: 88px;
  height: 100%;
  padding: 0 18px;
  border: 0;
  background: transparent;
  color: #595959;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-size: 13px;
  transition: color .2s;
}

.nav-item span {
  line-height: 1.2;
}

.nav-item:hover {
  color: var(--color-primary);
}

.nav-item.active {
  color: var(--color-primary);
}

.nav-item.active::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 0;
  height: 2px;
  background: var(--color-primary);
  border-radius: 1px 1px 0 0;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 20px;
  min-width: 220px;
  justify-content: flex-end;
}

.user-block {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-meta {
  line-height: 1.2;
}

.user-name {
  font-size: 13px;
  color: #262626;
  font-weight: 500;
}

.user-org {
  margin-top: 2px;
  font-size: 12px;
  color: #8c8c8c;
}

.app-main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

@media (max-width: 960px) {
  .brand { min-width: auto; }
  .brand-text { display: none; }
  .main-nav { justify-content: flex-start; overflow-x: auto; }
  .nav-item { min-width: 72px; padding: 0 12px; }
  .top-actions { min-width: auto; gap: 12px; }
}
</style>
