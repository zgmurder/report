<script setup lang="ts">
import { computed, toRef, watch } from 'vue'
import {
  NButton,
  NEmpty,
  NIcon,
  NInputNumber,
  NPopover,
  NSelect,
  NSpin,
  useMessage,
  type SelectOption,
} from 'naive-ui'
import { Copy, GripVertical, Info, RotateCcw, Search, X } from 'lucide-vue-next'
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
  executedSql,
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

function groupSelectedCount(group: FlagGroup): number {
  let count = 0
  for (const item of group.flags || []) {
    if (flags.value[item.key]) count += 1
  }
  for (const item of group.extras || []) {
    if (item.checked()) count += 1
  }
  return count
}

const canQuery = computed(() => Boolean(props.range?.[0] && props.range?.[1]))
const hasFilterSelection = computed(
  () => categoryCodes.value.length + typeCodes.value.length + subtypeCodes.value.length > 0,
)

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

async function copyExecutedSql() {
  const sql = executedSql.value
  if (!sql) {
    message.warning('暂无可复制的 SQL')
    return
  }
  try {
    await navigator.clipboard.writeText(sql)
    message.success('SQL 已复制')
  } catch {
    message.error('复制失败，请手动选中复制')
  }
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
      <div class="atomic-panel__tip">
        <NIcon :component="Info" :size="12" class="atomic-panel__tip-icon" />
        <span>拖到正文可替换数字；按住 <kbd>Shift</kbd> 插入到光标处</span>
      </div>
    </header>

    <div class="atomic-panel__scroll">
      <div class="atomic-section">
        <div class="atomic-section__head">
          <span class="atomic-section__title">警情分类</span>
          <span v-if="hasFilterSelection" class="atomic-section__badge">已选</span>
        </div>
        <div class="atomic-panel__filters">
          <label class="atomic-field">
            <span class="atomic-field__label">类别</span>
            <NSelect
              size="small"
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
              size="small"
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
              size="small"
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
      </div>

      <div
        v-for="group in flagGroups"
        :key="group.title"
        class="atomic-section"
      >
        <div class="atomic-section__head">
          <span class="atomic-section__title">{{ group.title }}</span>
          <span
            v-if="groupSelectedCount(group)"
            class="atomic-section__badge atomic-section__badge--count"
          >
            {{ groupSelectedCount(group) }}
          </span>
        </div>
        <div class="atomic-chips-opts">
          <button
            v-for="item in group.flags || []"
            :key="item.key"
            type="button"
            class="atomic-opt"
            :class="{ 'is-on': flags[item.key] }"
            :title="item.title"
            @click="setFlag(item.key, !flags[item.key])"
          >
            {{ item.label }}
          </button>
          <button
            v-for="item in group.extras || []"
            :key="item.key"
            type="button"
            class="atomic-opt"
            :class="{ 'is-on': item.checked() }"
            :title="item.title"
            @click="item.set(!item.checked())"
          >
            {{ item.label }}
          </button>
        </div>
      </div>

      <div v-if="showOrgDimension" class="atomic-extra">
        <label class="atomic-field">
          <span class="atomic-field__label">组织维度</span>
          <NSelect
            size="small"
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
            size="small"
            v-model:value="countThresholdOp"
            :options="[...countThresholdOpOptions]"
          />
        </label>
        <label class="atomic-field atomic-field--narrow">
          <span class="atomic-field__label">数量(起)</span>
          <NInputNumber
            size="small"
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
          <NSelect size="small" v-model:value="rankSortBy" :options="[...rankSortByOptions]" />
        </label>
        <label v-if="showRank" class="atomic-field atomic-field--narrow">
          <span class="atomic-field__label">升降序</span>
          <NSelect size="small" v-model:value="rankSortOrder" :options="[...rankSortOrderOptions]" />
        </label>
        <label v-if="showRank" class="atomic-field atomic-field--narrow">
          <span class="atomic-field__label">前N位</span>
          <NInputNumber
            size="small"
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
            size="small"
            :value="yoyTrend || 'up'"
            :options="[...yoyTrendOptions]"
            @update:value="onYoyTrendUpdate"
          />
        </label>
      </div>
    </div>

    <div class="atomic-panel__actions">
      <NButton
        size="small"
        type="primary"
        block
        :loading="querying"
        :disabled="!canQuery"
        @click="onQuery"
      >
        <template #icon><NIcon :component="Search" /></template>
        查询指标
      </NButton>
      <NButton size="small" secondary :disabled="querying" @click="onReset">
        <template #icon><NIcon :component="RotateCcw" /></template>
        重置
      </NButton>
    </div>

    <div class="atomic-section atomic-section--result">
      <div class="atomic-section__head">
        <span class="atomic-section__title">查询结果</span>
        <span v-if="atomicMetricChips.length" class="atomic-section__badge atomic-section__badge--count">
          {{ atomicMetricChips.length }}
        </span>
        <NPopover
          v-if="executedSql"
          trigger="hover"
          placement="left-start"
          :delay="200"
          :show-arrow="false"
          style="max-width: min(560px, 72vw)"
        >
          <template #trigger>
            <button type="button" class="atomic-sql-btn" title="查看执行 SQL">SQL</button>
          </template>
          <div class="atomic-sql-pop">
            <div class="atomic-sql-pop__head">
              <span>执行 SQL</span>
              <NButton size="tiny" secondary type="primary" @click="copyExecutedSql">
                <template #icon><NIcon :component="Copy" :size="12" /></template>
                复制
              </NButton>
            </div>
            <pre class="atomic-sql-pop__code">{{ executedSql }}</pre>
          </div>
        </NPopover>
      </div>

      <NSpin :show="querying" class="atomic-panel__result">
        <template #description>
          <div v-if="querying" class="atomic-panel__loading">
            <span>查询中…</span>
            <NButton size="tiny" secondary type="warning" @click="cancel">
              <template #icon><NIcon :component="X" :size="12" /></template>
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
        <NEmpty
          v-else
          class="atomic-empty"
          size="small"
          description="勾选指标后点查询，结果可拖入正文"
        />
      </NSpin>
    </div>
  </section>
</template>

<style scoped>
.atomic-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.atomic-panel__header {
  flex-shrink: 0;
}

.atomic-panel__tip {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 4px 6px;
  border-radius: 4px;
  background: #f0f7ff;
  color: #595959;
  font-size: 11px;
  line-height: 1.45;
}

.atomic-panel__tip-icon {
  flex-shrink: 0;
  margin-top: 1px;
  color: #1890ff;
}

.atomic-panel__tip kbd {
  display: inline-block;
  padding: 0 4px;
  border: 1px solid #d9d9d9;
  border-radius: 3px;
  background: #fff;
  color: #262626;
  font: 11px/1.4 ui-monospace, Consolas, monospace;
}

.atomic-panel__actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  padding-top: 2px;
}

.atomic-panel__actions :deep(.n-button:first-child) {
  flex: 1;
}

.atomic-panel__scroll {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  flex: 1;
  overflow: auto;
  padding-right: 2px;
}

.atomic-section {
  padding: 8px 10px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  background: #fff;
}

.atomic-section--result {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
}

.atomic-panel__result {
  min-height: 0;
  flex: 1;
  overflow: auto;
}

.atomic-section__head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.atomic-section__title {
  font-size: 12px;
  font-weight: 600;
  color: #595959;
}

.atomic-sql-btn {
  appearance: none;
  margin-left: auto;
  padding: 1px 8px;
  border: 1px solid #91d5ff;
  border-radius: 4px;
  background: #e6f7ff;
  color: #1890ff;
  font: 11px/1.5 Consolas, 'Courier New', monospace;
  cursor: pointer;
}

.atomic-sql-btn:hover {
  border-color: #1890ff;
  background: #bae7ff;
}

.atomic-sql-pop {
  width: min(520px, 70vw);
}

.atomic-sql-pop__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  color: #8c8c8c;
  font-size: 12px;
}

.atomic-sql-pop__code {
  max-height: 320px;
  margin: 0;
  padding: 10px 12px;
  overflow: auto;
  border-radius: 6px;
  background: #1e1e1e;
  color: #d4d4d4;
  font: 12px/1.65 Consolas, 'Courier New', monospace;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.atomic-section__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: #e6f7ff;
  color: #1890ff;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
}

.atomic-section__badge--count {
  background: #1890ff;
  color: #fff;
}

.atomic-panel__filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.atomic-field {
  display: block;
  min-width: 0;
}

.atomic-field__label {
  display: block;
  margin-bottom: 3px;
  font-size: 11px;
  color: #8c8c8c;
}

.atomic-field--narrow {
  width: 110px;
  flex-shrink: 0;
}

.atomic-chips-opts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.atomic-opt {
  appearance: none;
  margin: 0;
  padding: 3px 10px;
  border: 1px solid #d9d9d9;
  border-radius: 14px;
  background: #fafafa;
  color: #595959;
  font-size: 12px;
  line-height: 1.5;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}

.atomic-opt:hover {
  border-color: #91d5ff;
  color: #1890ff;
  background: #f5faff;
}

.atomic-opt.is-on {
  border-color: #1890ff;
  background: #e6f7ff;
  color: #1890ff;
  font-weight: 500;
}

.atomic-extra {
  flex-shrink: 0;
  padding: 8px 10px;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  background: #fafafa;
}

.atomic-extra--row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-end;
}

.atomic-extra--stub {
  font-size: 12px;
  color: #8c8c8c;
}

.atomic-panel__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 12px;
  color: #8c8c8c;
}

.atomic-chips {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-bottom: 4px;
}

.atomic-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid #91d5ff;
  border-radius: 6px;
  background: #e6f7ff;
  cursor: grab;
  transition: box-shadow 0.15s ease;
}

.atomic-chip:hover {
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.atomic-chip:active {
  cursor: grabbing;
}

.atomic-chip__grip {
  flex-shrink: 0;
  color: #69c0ff;
}

.atomic-chip__body {
  min-width: 0;
  flex: 1;
}

.atomic-chip__label {
  font-size: 11px;
  color: #8c8c8c;
}

.atomic-chip__value {
  margin-top: 2px;
  font-size: 13px;
  font-weight: 600;
  color: #262626;
  word-break: break-all;
}

.atomic-chip__field {
  flex-shrink: 0;
  align-self: flex-start;
  padding: 1px 6px;
  border-radius: 4px;
  background: #fff;
  color: #1890ff;
  font-size: 11px;
}

.atomic-empty {
  padding: 24px 0;
}

@media (max-width: 360px) {
  .atomic-panel__filters {
    grid-template-columns: 1fr;
  }
}
</style>
