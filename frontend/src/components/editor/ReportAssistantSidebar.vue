<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NCollapse,
  NCollapseItem,
  NEmpty,
  NIcon,
  NSelect,
  NSpace,
  NTreeSelect,
  NTabPane,
  NTabs,
  NDatePicker,
} from 'naive-ui'
import { Filter, RefreshCw, Search, Sparkles } from 'lucide-vue-next'
import { useDepartmentStore } from '@/stores/department'

const emit = defineEmits<{
  generateDraft: []
  insertHtml: [html: string]
  query: [params: Record<string, unknown>]
}>()

const departmentStore = useDepartmentStore()
const deptOptions = computed(() => departmentStore.treeOptions)
const activeMode = ref<'atomic' | 'ai' | 'component'>('atomic')
const activePreset = ref('本月')
const timePresets = ['昨天', '今天', '本周', '上周', '本月', '上月', '本年', '去年']

const range = ref<[number, number] | null>([
  new Date('2024-04-01 00:00:00').getTime(),
  new Date('2024-04-02 00:00:00').getTime(),
])
const department = ref<string | null>(null)
const officer = ref<string | null>(null)

const selectedDimensions = ref<string[]>(['环比', '同比'])
const selectedIndicators = ref<string[]>(['累计'])
const selectedLocations = ref<string[]>(['全市'])

const dimensionOptions = ['环比', '同比', '占比', '排名', '趋势']
const indicatorOptions = ['累计', '增量', '日均', '峰值', '均值']
const locationOptions = ['全市', '派出所', '街道', '社区', '重点部位']

const officerOptions = [
  { label: '张三', value: '张三' },
  { label: '李四', value: '李四' },
]

const componentItems = ['接报总量', '警情类别分布', '高发时段分析', '区域对比表']

const expandedNames = ref(['params'])

const dateDisplay = computed(() => {
  if (!range.value) return { start: '', end: '' }
  const fmt = (ts: number) => {
    const d = new Date(ts)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  }
  return { start: fmt(range.value[0]), end: fmt(range.value[1]) }
})

function applyPreset(preset: string) {
  activePreset.value = preset
}

function runQuery() {
  emit('query', {
    preset: activePreset.value,
    startDate: dateDisplay.value.start,
    endDate: dateDisplay.value.end,
    department: department.value,
    officer: officer.value,
    dimensions: [...selectedDimensions.value],
    indicators: [...selectedIndicators.value],
    locations: [...selectedLocations.value],
  })
}

function resetParams() {
  activePreset.value = '本月'
  range.value = [
    new Date('2024-04-01 00:00:00').getTime(),
    new Date('2024-04-02 00:00:00').getTime(),
  ]
  department.value = null
  officer.value = null
  selectedDimensions.value = ['环比', '同比']
  selectedIndicators.value = ['累计']
  selectedLocations.value = ['全市']
}

onMounted(() => {
  departmentStore.loadDepartmentTree().catch(() => {
    // 部门接口不可用时保持空态，不影响报告编辑主流程。
  })
})
</script>

<template>
  <aside class="atomic-panel">
    <div class="panel-head">
      <h3>原子输出</h3>
      <n-space :size="2">
        <n-button quaternary circle size="small">
          <template #icon><n-icon :component="Filter" :size="14" /></template>
        </n-button>
        <n-button quaternary circle size="small" @click="resetParams">
          <template #icon><n-icon :component="RefreshCw" :size="14" /></template>
        </n-button>
      </n-space>
    </div>

    <n-tabs v-model:value="activeMode" type="segment" size="small" class="mode-tabs">
      <n-tab-pane name="atomic" tab="原子模式" />
      <n-tab-pane name="ai" tab="AI模式" />
      <n-tab-pane name="component" tab="组件模式" />
    </n-tabs>

    <div class="panel-body">
      <template v-if="activeMode === 'atomic'">
        <n-collapse v-model:expanded-names="expandedNames">
          <n-collapse-item title="主要参数" name="params">
            <div class="preset-row">
              <n-button
                v-for="preset in timePresets"
                :key="preset"
                size="tiny"
                :type="activePreset === preset ? 'primary' : 'default'"
                :secondary="activePreset === preset"
                @click="applyPreset(preset)"
              >
                {{ preset }}
              </n-button>
            </div>

            <div class="field">
              <div class="field-label">时间范围</div>
              <n-date-picker
                v-model:value="range"
                type="datetimerange"
                clearable
                style="width: 100%"
              />
            </div>

            <div class="field-row">
              <div class="field">
                <div class="field-label">部门</div>
                <n-tree-select v-model:value="department" :options="deptOptions" clearable default-expand-all placeholder="请选择" />
              </div>
              <div class="field">
                <div class="field-label">责任警员</div>
                <n-select v-model:value="officer" :options="officerOptions" clearable placeholder="请选择" />
              </div>
            </div>

            <div class="check-group">
              <div class="field-label">维度</div>
              <n-checkbox-group v-model:value="selectedDimensions">
                <n-space :size="8" style="flex-wrap: wrap">
                  <n-checkbox v-for="item in dimensionOptions" :key="item" :value="item" :label="item" />
                </n-space>
              </n-checkbox-group>
            </div>

            <div class="check-group">
              <div class="field-label">指标</div>
              <n-checkbox-group v-model:value="selectedIndicators">
                <n-space :size="8" style="flex-wrap: wrap">
                  <n-checkbox v-for="item in indicatorOptions" :key="item" :value="item" :label="item" />
                </n-space>
              </n-checkbox-group>
            </div>

            <div class="check-group">
              <div class="field-label">位置</div>
              <n-checkbox-group v-model:value="selectedLocations">
                <n-space :size="8" style="flex-wrap: wrap">
                  <n-checkbox v-for="item in locationOptions" :key="item" :value="item" :label="item" />
                </n-space>
              </n-checkbox-group>
            </div>
          </n-collapse-item>
        </n-collapse>

        <div class="operator-block">
          <div class="operator-title">算子工作清单</div>
          <p class="operator-tip">从左侧拖入算子到此处，配置数据后可插入报告。</p>
          <n-button type="primary" block @click="runQuery">
            <template #icon><n-icon :component="Search" :size="15" /></template>
            查询生成
          </n-button>
          <div class="empty-box">
            <n-empty description="配置完成后自动生成报告" size="small" />
          </div>
        </div>
      </template>

      <template v-else-if="activeMode === 'ai'">
        <p class="ai-desc">基于当前报告上下文生成草稿，生成后需人工核对再保存。</p>
        <n-space vertical :size="10">
          <n-button type="primary" block @click="emit('generateDraft')">
            <template #icon><n-icon :component="Sparkles" :size="15" /></template>
            生成全文草稿
          </n-button>
          <n-button secondary block @click="emit('insertHtml', '<p>经综合研判，相关警情总体平稳，需持续关注重点区域和高发时段。</p>')">
            插入研判建议
          </n-button>
          <n-button secondary block @click="emit('insertHtml', '<p>请对以上数据进一步核实，避免直接使用未经确认的 AI 草稿。</p>')">
            插入核验提示
          </n-button>
        </n-space>
      </template>

      <template v-else>
        <p class="ai-desc">选择统计组件执行后，可将结果插入正文。</p>
        <n-space vertical :size="8">
          <n-button
            v-for="item in componentItems"
            :key="item"
            secondary
            block
            style="justify-content: space-between"
            @click="emit('insertHtml', `<h3>${item}</h3><p>[组件结果占位] ${item}，待接入真实统计结果。</p>`)"
          >
            <span>{{ item }}</span>
            <span class="insert-label">插入</span>
          </n-button>
        </n-space>
      </template>
    </div>
  </aside>
</template>

<style scoped>
.atomic-panel {
  width: 320px;
  flex-shrink: 0;
  height: 100%;
  background: #fff;
  border-left: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-head {
  height: 44px;
  padding: 0 12px 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.panel-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #262626;
}

.mode-tabs {
  padding: 8px 10px 0;
  flex-shrink: 0;
}

.panel-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 10px 12px 16px;
}

.preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.field {
  margin-bottom: 12px;
}

.field-label {
  margin-bottom: 6px;
  font-size: 12px;
  color: #8c8c8c;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.check-group {
  margin-bottom: 12px;
}

.operator-block {
  margin-top: 12px;
}

.operator-title {
  font-size: 13px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 6px;
}

.operator-tip {
  margin: 0 0 10px;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.6;
}

.empty-box {
  margin-top: 12px;
  min-height: 140px;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  background: #fafafa;
  display: grid;
  place-items: center;
  padding: 16px;
}

.ai-desc {
  margin: 0 0 12px;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.6;
}

.insert-label {
  color: #1890ff;
  font-size: 12px;
}
</style>
