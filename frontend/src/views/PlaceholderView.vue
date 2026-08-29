<script setup lang="ts">
import { useRoute } from 'vue-router'
import { NCard, NEmpty } from 'naive-ui'

const route = useRoute()
</script>

<template>
  <section class="placeholder">
    <n-card style="width: min(520px, 100%)" :bordered="true">
      <n-empty :description="`${String(route.meta.title || '功能')}建设中，后续按业务优先级实现。`">
        <template #extra>
          <span class="muted">该模块先保留导航入口</span>
        </template>
      </n-empty>
    </n-card>
  </section>
</template>

<style scoped>
.placeholder {
  height: 100%;
  display: grid;
  place-items: center;
  padding: 24px;
  background: var(--color-bg);
}
.muted { color: #8c8c8c; font-size: 13px; }
</style>
