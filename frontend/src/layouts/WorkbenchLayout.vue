<script setup lang="ts">
import { computed, h, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAvatar, NButton, NDropdown, NIcon } from 'naive-ui'
import { BookOpenCheck, History, LogOut, UserRound } from 'lucide-vue-next'
import { workbenchNavItems } from '@/data/navigation'
import { useUserStore } from '@/stores/user'
import StatisticsDictionaryConfigModal from '@/components/system/StatisticsDictionaryConfigModal.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const showDictionaryConfig = ref(false)
const activeNavIndex = computed(() => workbenchNavItems.findIndex((item) => isActive(item.path)))
const activeNavIndicatorStyle = computed(() => ({
  opacity: activeNavIndex.value >= 0 ? 1 : 0,
  transform: `translateX(calc(${Math.max(activeNavIndex.value, 0) * 100}% + ${Math.max(activeNavIndex.value, 0) * 4}px))`,
}))
const userOptions = computed(() => [
  ...(userStore.user?.roles.includes('admin')
    ? [{ label: '字典配置', key: 'dictionary-config', icon: () => h(NIcon, null, { default: () => h(BookOpenCheck) }) }]
    : []),
  { label: '退出登录', key: 'logout', icon: () => h(NIcon, null, { default: () => h(LogOut) }) },
])

function isActive(path: string) {
  if (path === '/home/reports') {
    return route.path.startsWith('/home/reports') || route.path.startsWith('/home/editor')
  }
  return route.path === path || route.path.startsWith(`${path}/`)
}

function handleUserAction(key: string) {
  if (key === 'dictionary-config') {
    showDictionaryConfig.value = true
    return
  }
  if (key === 'logout') {
    userStore.logout()
    router.replace('/login')
  }
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
        <span class="nav-indicator" :style="activeNavIndicatorStyle" aria-hidden="true" />
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
        <n-dropdown trigger="click" :options="userOptions" @select="handleUserAction">
          <div class="user-block">
            <n-avatar round size="small" :style="{ background: '#f0f0f0', color: '#8c8c8c' }">
              <n-icon :component="UserRound" :size="16" />
            </n-avatar>
            <div class="user-meta">
              <div class="user-name">{{ userStore.displayName }}</div>
              <div class="user-org">义乌市局</div>
            </div>
          </div>
        </n-dropdown>
      </div>
    </header>

    <main class="app-main">
      <router-view />
    </main>

    <statistics-dictionary-config-modal v-model:show="showDictionaryConfig" />
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
  --nav-item-width: 108px;
  --nav-gap: 4px;
  position: relative;
  flex: 1;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: var(--nav-gap);
}

.nav-indicator {
  position: absolute;
  left: 0;
  bottom: 0;
  width: var(--nav-item-width);
  height: 2px;
  pointer-events: none;
  transition: transform .32s cubic-bezier(.22, 1, .36, 1), opacity .2s ease;
}

.nav-indicator::after {
  content: '';
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 0;
  height: 2px;
  border-radius: 2px 2px 0 0;
  background: var(--color-primary);
}

.nav-item {
  position: relative;
  z-index: 1;
  width: var(--nav-item-width);
  height: 38px;
  padding: 0 14px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #595959;
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  gap: 7px;
  font-size: 13px;
  white-space: nowrap;
  cursor: pointer;
  transition: color .2s ease, transform .2s ease;
}

.nav-item span {
  line-height: 1;
}

.nav-item:hover {
  color: var(--color-primary);
}

.nav-item:active {
  transform: translateY(1px);
}

.nav-item:focus-visible {
  outline: 2px solid rgba(24, 144, 255, .35);
  outline-offset: 1px;
}

.nav-item.active {
  color: var(--color-primary);
  font-weight: 600;
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
  cursor: pointer;
  border-radius: 10px;
  padding: 4px 6px;
  transition: background .2s;
}

.user-block:hover {
  background: #f5f7fb;
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
  display: flex;
  flex-direction: column;
}

.app-main > * {
  flex: 1;
  min-height: 0;
  min-width: 0;
}

@media (max-width: 960px) {
  .brand { min-width: auto; }
  .brand-text { display: none; }
  .main-nav { --nav-item-width: 96px; justify-content: flex-start; overflow-x: auto; }
  .nav-item { padding: 0 10px; }
  .top-actions { min-width: auto; gap: 12px; }
}
</style>
