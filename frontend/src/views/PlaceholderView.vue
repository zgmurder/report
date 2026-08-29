<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <section class="placeholder">
    <div class="panel">
      <h2>{{ route.meta.title || '功能建设中' }}</h2>
      <p>该模块先保留导航入口，后续按业务优先级实现。</p>
    </div>
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

.panel {
  width: min(520px, 100%);
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 40px 32px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, .04);
}

h2 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: #262626;
}

p {
  margin: 0;
  color: #8c8c8c;
  font-size: 13px;
}
</style>
