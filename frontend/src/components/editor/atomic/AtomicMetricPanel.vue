<script setup lang="ts">
import { computed, toRef, watch } from 'vue'
import {
  NButton,
  NCheckbox,
  NEmpty,
  NIcon,
  NInputNumber,
  NSelect,
  NSpin,
  useMessage,
  type SelectOption,
} from 'naive-ui'
import { GripVertical, RotateCcw, Search, X } from 'lucide-vue-next'
import {
  useAtomicMetric,
  type AtomicCompareFlags,
} from '@/composables/useAtomicMetric'

const props = withDefaults(
  defineProps<{
    categoryOptions?: SelectOption[]
    typeOptions?: SelectOption[]
    detailOptions?: SelectOption[]
    source?: 'jjd_jjd' | 'fkd_fkd'
    range?: [number, number] | null
    deptCode?: string
    deptName?: string
    loadingClassifications?: boolean
  }>(),
  {
    categoryOptions: () => [],
    typeOptions: () => [],
    detailOptions: () => [],
    source: 'jjd_jjd',
    range: null,
    deptCode: '',
    deptName: '',
    loadingClassifications: false,
  },
)

const message = useMessage()

const metric = useAtomicMetric({
  dateRange: toRef(props, 'range'),
  source: toRef(props, 'source'),
  deptCode: toRef(props, 'deptCode'),
  deptName: toRef(props, 'deptName'),
})

const {
  flags,
  categoryCodes,
  typeCodes,
  subtypeCodes,
  categoryNames,
  typeNames,
  subtypeNames,
  showOrgDimension,
  orgDimension,
  orgDimensionOptions,
  showTag,
  showAnalysis,
  yoyTrend,
  yoyTrendOptions,
  showRank,
  topN,
  rankSortBy,
  rankSortOrder,
  rankSortByOptions,
  rankSortOrderOptions,
  showThreshold,
  countThresholdOp,
  countThresholdValue,
  countThresholdOpOptions,
  showWarning,
  querying,
  lastError,
  atomicMetricChips,
  setFlag,
  setShowOrgDimension,
  setShowAnalysis,
  setShowRank,
  setShowThreshold,
  setShowTag,
  setShowWarning,
  queryAtomicMetric,
  reset,
  cancel,
  startMetricDrag,
} = metric

watch(
  () => props.categoryOptions,
  () => {
    // 选项变化时同步已选名称
    syncNamesFromCodes('category')
  },
  { deep: true },
)
watch(
  () => props.typeOptions,
  () => syncNamesFromCodes('type'),
  { deep: true },
)
watch(
  () => props.detailOptions,
  () => syncNamesFromCodes('subtype'),
  { deep: true },
)

function syncNamesFromCodes(level: 'category' | 'type' | 'subtype') {
  const options =
    level === 'category'
      ? props.categoryOptions
      : level === 'type'
        ? props.typeOptions
        : props.detailOptions
  const codes =
    level === 'category'
      ? categoryCodes.value
      : level === 'type'
        ? typeCodes.value
        : subtypeCodes.value
  const names = codes.map((code) => {
    const found = options.find((item) => String(item.value) === code)
    return found ? String(found.label ?? code) : code
  })
  if (level === 'category') categoryNames.value = names
  else if (level === 'type') typeNames.value = names
  else subtypeNames.value = names
}

function onCategoryUpdate(value: Array<string | number> | null) {
  const codes = (value || []).map((item) => String(item))
  categoryCodes.value = codes
  categoryNames.value = codes.map((code) => {
    const found = props.categoryOptions.find((item) => String(item.value) === code)
    return found ? String(found.label ?? code) : code
  })
}

function onTypeUpdate(value: Array<string | number> | null) {
  const codes = (value || []).map((item) => String(item))
  typeCodes.value = codes
  typeNames.value = codes.map((code) => {
    const found = props.typeOptions.find((item) => String(item.value) === code)
    return found ? String(found.label ?? code) : code
  })
}

function onDetailUpdate(value: Array<string | number> | null) {
  const codes = (value || []).map((item) => String(item))
  subtypeCodes.value = codes
  subtypeNames.value = codes.map((code) => {
    const found = props.detailOptions.find((item) => String(item.value) === code)
    return found ? String(found.label ?? code) : code
  })
}

type FlagItem = { key: keyof AtomicCompareFlags; label: string; title: string }
type ExtraFlagItem = {
  key: 'org' | 'tag' | 'analysis' | 'rank' | 'threshold' | 'warning'
  label: string
  title: string
  checked: () => boolean
  set: (v: boolean) => void
}
type FlagGroup = {
  title: string
  flags?: FlagItem[]
  extras?: ExtraFlagItem[]
}

const flagGroups: FlagGroup[] = [
  {
    title: '对比指标',
    flags: [
      { key: 'yoy', label: '同比', title: '同比变化' },
      { key: 'mom', label: '环比', title: '环比变化' },
      { key: 'share', label: '占比', title: '当前筛选占总量比例；可与类别/类型/细类/社区/辖区联用' },
      { key: 'momCount', label: '环比数', title: '返回上期数量（环比数）' },
      { key: 'yoyCount', label: '同比数', title: '返回去年同期数量（同比数）' },
      { key: 'cumulative', label: '累计', title: '结束时间所在年 1月1日 至结束时间的总数' },
    ],
  },
  {
    title: '拆分维度',
    flags: [
      { key: 'categoryShare', label: '类别', title: '按类别拆分数量' },
      { key: 'typeShare', label: '类型', title: '按类型拆分数量' },
      { key: 'subtypeShare', label: '细类', title: '按细类拆分数量' },
      { key: 'hotCommunity', label: '社区', title: '按社区拆分数量' },
      { key: 'region', label: '辖区', title: '按派出所辖区拆分数量' },
      { key: 'hotPeriod', label: '高发时段', title: '按 2 小时跨度统计高发时段' },
    ],
    extras: [
      {
        key: 'org',
        label: '组织维度',
        title: '勾选后选择片区/共建委/警务区',
        checked: () => showOrgDimension.value,
        set: (v) => setShowOrgDimension(v),
      },
      {
        key: 'tag',
        label: '标签',
        title: '标签过滤（暂未接入标签包）',
        checked: () => showTag.value,
        set: (v) => setShowTag(v),
      },
    ],
  },
  {
    title: '过滤条件',
    flags: [
      { key: 'duplicate', label: '重复', title: '仅接警单重复过滤' },
      { key: 'excludeNonPolice', label: '除去非警务', title: '排除非警务类别' },
      { key: 'selfReceived', label: '自接警', title: '接警单位 = 管辖单位' },
      { key: 'excludeSelfReceived', label: '除自接警', title: '排除自接警' },
      { key: 'excludeTraffic', label: '除交通', title: '排除交通类别' },
    ],
  },
  {
    title: '分析增强',
    extras: [
      {
        key: 'analysis',
        label: '分析',
        title: '升幅/降幅/自动分析',
        checked: () => showAnalysis.value,
        set: (v) => setShowAnalysis(v),
      },
      {
        key: 'rank',
        label: '排名',
        title: '限制前 N 位',
        checked: () => showRank.value,
        set: (v) => setShowRank(v),
      },
      {
        key: 'threshold',
        label: '阈值',
        title: '按数量过滤列表结果',
        checked: () => showThreshold.value,
        set: (v) => setShowThreshold(v),
      },
      {
        key: 'warning',
        label: '预警',
        title: '预警（暂 stub）',
        checked: () => showWarning.value,
        set: (v) => setShowWarning(v),
      },
    ],
  },
]

const canQuery = computed(() => Boolean(props.range?.[0] && props.range?.[1]))

async function onQuery() {
  try {
    const ok = await queryAtomicMetric()
    if (!ok) {
      if (lastError.value) message.warning(lastError.value)
      return
    }
    message.success('原子指标查询完成')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '原子指标查询失败')
  }
}

function onOrgDimensionUpdate(value: string | null) {
  orgDimension.value = value === 'pianqu' || value === 'gongjianwei' || value === 'jingwuqu' ? value : ''
}

function onYoyTrendUpdate(value: string | null) {
  yoyTrend.value = value === 'down' || value === 'analysis' ? value : 'up'
}

function onReset() {
  reset()
  message.info('已重置选项（保留类别/类型/细类）')
}

defineExpose({
  metric,
  queryAtomicMetric,
  reset,
  cancel,
  atomicMetricChips,
})
</script>

<template>
  <section class="atomic-panel">
    <header class="atomic-panel__header">
      <div class="atomic-panel__title-wrap">
        <div class="atomic-panel__title">原子指标</div>
        <div class="atomic-panel__hint">拖入可替换文中数字；按住 Shift 则插入到光标处</div>
      </div>
      <div class="atomic-panel__actions">
        <NButton
          size="small"
          type="primary"
          :loading="querying"
          :disabled="!canQuery"
          @click="onQuery"
        >
          <template #icon><NIcon :component="Search" /></template>
          查询
        </NButton>
        <NButton size="small" secondary :disabled="querying" @click="onReset">
          <template #icon><NIcon :component="RotateCcw" /></template>
          重置
        </NButton>
      </div>
    </header>

    <div class="atomic-panel__filters">
      <label class="atomic-field">
        <span class="atomic-field__label">类别</span>
        <NSelect
          :value="categoryCodes"
          :options="categoryOptions"
          :loading="loadingClassifications"
          multiple
          clearable
          filterable
          max-tag-count="responsive"
          placeholder="全部"
          @update:value="onCategoryUpdate"
        />
      </label>
      <label class="atomic-field">
        <span class="atomic-field__label">类型</span>
        <NSelect
          :value="typeCodes"
          :options="typeOptions"
          :loading="loadingClassifications"
          multiple
          clearable
          filterable
          max-tag-count="responsive"
          placeholder="全部"
          @update:value="onTypeUpdate"
        />
      </label>
      <label class="atomic-field">
        <span class="atomic-field__label">细类</span>
        <NSelect
          :value="subtypeCodes"
          :options="detailOptions"
          :loading="loadingClassifications"
          multiple
          clearable
          filterable
          max-tag-count="responsive"
          placeholder="全部"
          @update:value="onDetailUpdate"
        />
      </label>
    </div>

    <div class="atomic-flag-groups">
      <div v-for="group in flagGroups" :key="group.title" class="atomic-flag-group">
        <div class="atomic-flag-group__title">{{ group.title }}</div>
        <div class="atomic-flags">
          <NCheckbox
            v-for="item in group.flags || []"
            :key="item.key"
            size="small"
            :checked="flags[item.key]"
            :title="item.title"
            @update:checked="(v) => setFlag(item.key, Boolean(v))"
          >
            <span class="atomic-flags__label">{{ item.label }}</span>
          </NCheckbox>
          <NCheckbox
            v-for="item in group.extras || []"
            :key="item.key"
            size="small"
            :checked="item.checked()"
            :title="item.title"
            @update:checked="(v) => item.set(Boolean(v))"
          >
            <span class="atomic-flags__label">{{ item.label }}</span>
          </NCheckbox>
        </div>
      </div>
    </div>

    <div v-if="showOrgDimension" class="atomic-extra">
      <label class="atomic-field">
        <span class="atomic-field__label">组织维度</span>
        <NSelect
          :value="orgDimension || null"
          :options="[...orgDimensionOptions]"
          placeholder="请选择片区/共建委/警务区"
          @update:value="onOrgDimensionUpdate"
        />
      </label>
    </div>

    <div v-if="showTag" class="atomic-extra atomic-extra--stub">
      标签过滤暂未接入，勾选后暂不生效。
    </div>

    <div v-if="showWarning" class="atomic-extra atomic-extra--stub">
      预警规则暂未接入，勾选后暂不查询预警文案。
    </div>

    <div v-if="showThreshold" class="atomic-extra atomic-extra--row">
      <label class="atomic-field atomic-field--narrow">
        <span class="atomic-field__label">比较</span>
        <NSelect
          v-model:value="countThresholdOp"
          :options="[...countThresholdOpOptions]"
        />
      </label>
      <label class="atomic-field atomic-field--narrow">
        <span class="atomic-field__label">数量(起)</span>
        <NInputNumber
          v-model:value="countThresholdValue"
          :min="0"
          :show-button="false"
          placeholder="请输入"
        />
      </label>
    </div>

    <div v-if="showRank || showAnalysis" class="atomic-extra atomic-extra--row">
      <label v-if="showRank" class="atomic-field atomic-field--narrow">
        <span class="atomic-field__label">排序</span>
        <NSelect v-model:value="rankSortBy" :options="[...rankSortByOptions]" />
      </label>
      <label v-if="showRank" class="atomic-field atomic-field--narrow">
        <span class="atomic-field__label">升降序</span>
        <NSelect v-model:value="rankSortOrder" :options="[...rankSortOrderOptions]" />
      </label>
      <label v-if="showRank" class="atomic-field atomic-field--narrow">
        <span class="atomic-field__label">前N位</span>
        <NInputNumber
          v-model:value="topN"
          :min="1"
          :max="200"
          :show-button="false"
          placeholder="全部"
        />
      </label>
      <label v-if="showAnalysis" class="atomic-field atomic-field--narrow">
        <span class="atomic-field__label">分析方向</span>
        <NSelect
          :value="yoyTrend || 'up'"
          :options="[...yoyTrendOptions]"
          @update:value="onYoyTrendUpdate"
        />
      </label>
    </div>

    <NSpin :show="querying" class="atomic-panel__result">
      <template #description>
        <div v-if="querying" class="atomic-panel__loading">
          <span>查询中…</span>
          <NButton size="small" secondary type="warning" @click="cancel">
            <template #icon><NIcon :component="X" :size="14" /></template>
            取消
          </NButton>
        </div>
      </template>

      <div v-if="atomicMetricChips.length" class="atomic-chips">
        <div
          v-for="chip in atomicMetricChips"
          :key="chip.field"
          class="atomic-chip"
          draggable="true"
          title="拖入文档"
          @dragstart="startMetricDrag($event, chip)"
        >
          <NIcon :component="GripVertical" class="atomic-chip__grip" :size="16" />
          <div class="atomic-chip__body">
            <div class="atomic-chip__label">{{ chip.label }}</div>
            <div class="atomic-chip__value">{{ chip.displayValue }}</div>
          </div>
          <span class="atomic-chip__field">{{ chip.field }}</span>
        </div>
      </div>
      <NEmpty v-else class="atomic-empty" size="small" description="设置全局参数后点击查询" />
    </NSpin>
  </section>
</template>

<style scoped>
.atomic-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.atomic-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  flex-shrink: 0;
}

.atomic-panel__title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.atomic-panel__hint {
  margin-top: 2px;
  font-size: 11px;
  color: #94a3b8;
}

.atomic-panel__actions {
  display: flex;
  flex-shrink: 0;
  gap: 6px;
}

.atomic-panel__filters {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  flex-shrink: 0;
}

.atomic-field {
  display: block;
  min-width: 0;
}

.atomic-field__label {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  color: #64748b;
}

.atomic-field--narrow {
  width: 120px;
  flex-shrink: 0;
}

.atomic-flag-groups {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
}

.atomic-flag-group__title {
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  letter-spacing: 0.02em;
}

.atomic-flags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}

.atomic-flags__label {
  font-size: 12px;
  color: #475569;
}

.atomic-extra {
  flex-shrink: 0;
}

.atomic-extra--row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-end;
}

.atomic-extra--stub {
  font-size: 12px;
  color: #94a3b8;
  padding: 6px 8px;
  background: #f8fafc;
  border-radius: 6px;
}

.atomic-panel__result {
  min-height: 0;
  flex: 1;
  overflow: auto;
}

.atomic-panel__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 12px;
  color: #64748b;
}

.atomic-chips {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 8px;
}

.atomic-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: rgba(239, 246, 255, 0.65);
  cursor: grab;
  transition: box-shadow 0.15s ease;
}

.atomic-chip:hover {
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25);
}

.atomic-chip:active {
  cursor: grabbing;
}

.atomic-chip__grip {
  flex-shrink: 0;
  color: #93c5fd;
}

.atomic-chip__body {
  min-width: 0;
  flex: 1;
}

.atomic-chip__label {
  font-size: 11px;
  color: #64748b;
}

.atomic-chip__value {
  margin-top: 2px;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  word-break: break-all;
}

.atomic-chip__field {
  flex-shrink: 0;
  align-self: flex-start;
  padding: 1px 6px;
  border-radius: 4px;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 11px;
}

.atomic-empty {
  padding: 40px 0;
}
</style>
