<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  NButton,
  NCheckbox,
  NEmpty,
  NInput,
  NModal,
  NSpace,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  NVirtualList,
  useMessage,
} from 'naive-ui'
import {
  getStatisticsDictionaryConfig,
  updateStatisticsDictionaryConfig,
  type SearchClassificationItem,
  type StatisticsDictionarySource,
} from '@/api/reportSearch'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ 'update:show': [value: boolean]; saved: [] }>()
const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const sources = ref<StatisticsDictionarySource[]>([])
const activeSource = ref<'jjd_jjd' | 'fkd_fkd'>('jjd_jjd')
const activeLevel = ref<'category' | 'type' | 'detail'>('category')
const keyword = ref('')
const enabled = ref<Record<string, Record<'category' | 'type' | 'detail', Set<string>>>>({})

const currentSource = computed(() => sources.value.find((item) => item.source === activeSource.value) || null)
const levelItems = computed<SearchClassificationItem[]>(() => {
  const source = currentSource.value
  if (!source) return []
  if (activeLevel.value === 'category') return source.categories
  if (activeLevel.value === 'type') return source.types
  return source.details
})
const filteredItems = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return levelItems.value
  return levelItems.value.filter((item) => item.code.toLowerCase().includes(text) || item.name.toLowerCase().includes(text))
})
const filteredRows = computed(() => {
  const rows: Array<{ key: string; items: SearchClassificationItem[] }> = []
  for (let index = 0; index < filteredItems.value.length; index += 2) {
    const items = filteredItems.value.slice(index, index + 2)
    rows.push({ key: items.map((item) => item.code).join(':'), items })
  }
  return rows
})
const currentEnabled = computed(() => enabled.value[activeSource.value]?.[activeLevel.value] || new Set<string>())
const enabledCount = computed(() => currentEnabled.value.size)

function initializeEnabled() {
  const next: Record<string, Record<'category' | 'type' | 'detail', Set<string>>> = {}
  for (const source of sources.value) {
    next[source.source] = {
      category: new Set(source.categories.map((item) => item.code).filter((code) => !source.disabled.category.includes(code))),
      type: new Set(source.types.map((item) => item.code).filter((code) => !source.disabled.type.includes(code))),
      detail: new Set(source.details.map((item) => item.code).filter((code) => !source.disabled.detail.includes(code))),
    }
  }
  enabled.value = next
}

async function loadConfig() {
  loading.value = true
  try {
    const response = await getStatisticsDictionaryConfig()
    sources.value = response.sources
    initializeEnabled()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '字典配置加载失败')
    emit('update:show', false)
  } finally {
    loading.value = false
  }
}

function toggle(code: string, checked: boolean) {
  const sourceSets = enabled.value[activeSource.value]
  if (!sourceSets) return
  const next = new Set(sourceSets[activeLevel.value])
  if (checked) next.add(code)
  else next.delete(code)
  sourceSets[activeLevel.value] = next
  enabled.value = { ...enabled.value }
}

function setFilteredEnabled(checked: boolean) {
  const sourceSets = enabled.value[activeSource.value]
  if (!sourceSets) return
  const next = new Set(sourceSets[activeLevel.value])
  for (const item of filteredItems.value) {
    if (checked) next.add(item.code)
    else next.delete(item.code)
  }
  sourceSets[activeLevel.value] = next
  enabled.value = { ...enabled.value }
}

async function save() {
  saving.value = true
  try {
    for (const source of sources.value) {
      const sourceEnabled = enabled.value[source.source]
      if (!sourceEnabled) continue
      await updateStatisticsDictionaryConfig({
        source: source.source,
        disabled_categories: source.categories.map((item) => item.code).filter((code) => !sourceEnabled.category.has(code)),
        disabled_types: source.types.map((item) => item.code).filter((code) => !sourceEnabled.type.has(code)),
        disabled_details: source.details.map((item) => item.code).filter((code) => !sourceEnabled.detail.has(code)),
      })
    }
    window.dispatchEvent(new CustomEvent('statistics-dictionary-updated'))
    message.success('统计字典配置已保存')
    emit('saved')
    emit('update:show', false)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

watch(() => props.show, (show) => {
  if (show) loadConfig()
})
watch([activeSource, activeLevel], () => { keyword.value = '' })
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    title="统计字典配置"
    class="dictionary-modal"
    :mask-closable="false"
    @update:show="emit('update:show', $event)"
  >
    <n-spin :show="loading">
      <div class="config-tip">勾选的字典项参与全局统计；取消勾选后，将从搜索选项和统计结果中排除。</div>
      <n-tabs v-model:value="activeSource" type="segment" animated>
        <n-tab-pane v-for="source in sources" :key="source.source" :name="source.source">
          <template #tab>{{ source.name || source.source }}</template>
        </n-tab-pane>
      </n-tabs>
      <n-tabs v-model:value="activeLevel" type="line" animated class="level-tabs">
        <n-tab-pane name="category"><template #tab>类别</template></n-tab-pane>
        <n-tab-pane name="type"><template #tab>类型</template></n-tab-pane>
        <n-tab-pane name="detail"><template #tab>细类</template></n-tab-pane>
      </n-tabs>

      <div class="config-toolbar">
        <n-input v-model:value="keyword" clearable placeholder="搜索名称或代码" />
        <n-space :wrap="false">
          <n-button size="small" @click="setFilteredEnabled(true)">全选当前结果</n-button>
          <n-button size="small" @click="setFilteredEnabled(false)">取消当前结果</n-button>
        </n-space>
      </div>
      <div class="config-summary">
        <span>已启用 {{ enabledCount }} / {{ levelItems.length }}</span>
        <n-tag size="small" :bordered="false">当前显示 {{ filteredItems.length }} 项</n-tag>
      </div>

      <n-virtual-list
        v-if="filteredRows.length"
        :key="`${activeSource}-${activeLevel}-${keyword}`"
        class="checkbox-list"
        :items="filteredRows"
        :item-size="40"
        key-field="key"
      >
        <template #default="{ item: row }">
          <div class="checkbox-row">
            <label v-for="item in row.items" :key="item.code" class="checkbox-item">
              <n-checkbox :checked="currentEnabled.has(item.code)" @update:checked="toggle(item.code, $event)" />
              <span class="item-name" :title="item.name">{{ item.name }}</span>
              <span class="item-code">{{ item.code }}</span>
            </label>
          </div>
        </template>
      </n-virtual-list>
      <div v-else class="checkbox-list empty-list">
        <n-empty description="没有匹配的字典项" />
      </div>
    </n-spin>

    <template #footer>
      <div class="modal-footer">
        <n-button @click="emit('update:show', false)">取消</n-button>
        <n-button type="primary" :loading="saving" :disabled="loading" @click="save">保存配置</n-button>
      </div>
    </template>
  </n-modal>
</template>

<style scoped>
:global(.dictionary-modal) { width: min(820px, calc(100vw - 40px)); }
.config-tip { margin-bottom: 14px; padding: 10px 12px; color: #606266; background: #f5f8fc; border: 1px solid #e4edf8; border-radius: 6px; font-size: 12px; line-height: 1.6; }
.level-tabs { margin-top: 8px; }
.config-toolbar { display: grid; grid-template-columns: minmax(220px, 1fr) auto; gap: 12px; align-items: center; margin-bottom: 10px; }
.config-summary { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; color: #606266; font-size: 12px; }
.checkbox-list { height: 430px; padding: 6px; border: 1px solid #e5e7eb; border-radius: 6px; background: #fafbfc; }
.checkbox-row { height: 40px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.checkbox-item { min-width: 0; height: 36px; padding: 0 9px; display: flex; align-items: center; gap: 8px; border-radius: 4px; background: #fff; cursor: pointer; }
.checkbox-item:hover { background: #edf6ff; }
.item-name { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #303133; font-size: 13px; }
.item-code { flex-shrink: 0; color: #a0a4aa; font-size: 11px; }
.empty-list { display: flex; align-items: center; justify-content: center; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; }
@media (max-width: 680px) { .config-toolbar { grid-template-columns: 1fr; } }
</style>
