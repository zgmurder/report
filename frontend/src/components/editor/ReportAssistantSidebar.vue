<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  Filter,
  Inbox,
  RefreshCw,
  Search,
  Sparkles,
} from 'lucide-vue-next'
import { useCatalogStore } from '@/stores/catalog'

const emit = defineEmits<{
  generateDraft: []
  insertHtml: [html: string]
  query: [params: Record<string, unknown>]
}>()

const catalogStore = useCatalogStore()
const activeMode = ref<'atomic' | 'ai' | 'component'>('atomic')
const paramsOpen = ref(true)

const timePresets = ['昨天', '今天', '本周', '上周', '本月', '上月', '本年', '去年']
const activePreset = ref('本月')

const params = reactive({
  startDate: '2024-04-01 00:00:00',
  endDate: '2024-04-02 00:00:00',
  department: '',
  officer: '',
})

const dimensionOptions = ['环比', '同比', '占比', '排名', '趋势']
const indicatorOptions = ['累计', '增量', '日均', '峰值', '均值']
const locationOptions = ['全市', '派出所', '街道', '社区', '重点部位']

const selectedDimensions = ref<string[]>(['环比', '同比'])
const selectedIndicators = ref<string[]>(['累计'])
const selectedLocations = ref<string[]>(['全市'])
const fallbackComponents = ['接报总量', '警情类别分布', '高发时段分析', '区域对比表']
const componentNames = computed(() => {
  const names = catalogStore.components.map((item) => item.name).filter(Boolean)
  return names.length ? names : fallbackComponents
})

function toggle(kind: 'dimensions' | 'indicators' | 'locations', value: string) {
  const list = kind === 'dimensions' ? selectedDimensions : kind === 'indicators' ? selectedIndicators : selectedLocations
  const idx = list.value.indexOf(value)
  if (idx >= 0) list.value.splice(idx, 1)
  else list.value.push(value)
}

function applyPreset(preset: string) {
  activePreset.value = preset
}

function runQuery() {
  emit('query', {
    preset: activePreset.value,
    startDate: params.startDate,
    endDate: params.endDate,
    department: params.department,
    officer: params.officer,
    dimensions: [...selectedDimensions.value],
    indicators: [...selectedIndicators.value],
    locations: [...selectedLocations.value],
  })
}

function resetParams() {
  activePreset.value = '本月'
  params.startDate = '2024-04-01 00:00:00'
  params.endDate = '2024-04-02 00:00:00'
  params.department = ''
  params.officer = ''
  selectedDimensions.value = ['环比', '同比']
  selectedIndicators.value = ['累计']
  selectedLocations.value = ['全市']
}

onMounted(() => {
  catalogStore.loadComponents().catch(() => {
    // 组件库不可用时保留设计稿中的本地占位项，不影响页面交互。
  })
})
</script>

<template>
  <aside class="atomic-panel">
    <div class="panel-head">
      <h3>原子输出</h3>
      <div class="head-actions">
        <button class="icon-btn" type="button" title="筛选"><Filter :size="14" /></button>
        <button class="icon-btn" type="button" title="刷新" @click="resetParams"><RefreshCw :size="14" /></button>
      </div>
    </div>

    <div class="mode-tabs">
      <button type="button" :class="{ active: activeMode === 'atomic' }" @click="activeMode = 'atomic'">原子模式</button>
      <button type="button" :class="{ active: activeMode === 'ai' }" @click="activeMode = 'ai'">AI模式</button>
      <button type="button" :class="{ active: activeMode === 'component' }" @click="activeMode = 'component'">组件模式</button>
    </div>

    <div class="panel-body">
      <template v-if="activeMode === 'atomic'">
        <section class="block">
          <button class="block-title" type="button" @click="paramsOpen = !paramsOpen">
            <span>主要参数</span>
            <span class="chevron" :class="{ open: paramsOpen }">▾</span>
          </button>

          <div v-show="paramsOpen" class="block-content">
            <div class="preset-row">
              <button
                v-for="preset in timePresets"
                :key="preset"
                type="button"
                class="preset-btn"
                :class="{ active: activePreset === preset }"
                @click="applyPreset(preset)"
              >
                {{ preset }}
              </button>
            </div>

            <div class="field">
              <label>时间范围</label>
              <div class="range-row">
                <input v-model="params.startDate" class="input" />
                <span class="range-sep">至</span>
                <input v-model="params.endDate" class="input" />
              </div>
            </div>

            <div class="field-row">
              <div class="field">
                <label>部门</label>
                <select v-model="params.department" class="select">
                  <option value="">请选择</option>
                  <option value="义乌市局">义乌市局</option>
                  <option value="稠城所">稠城所</option>
                  <option value="北苑所">北苑所</option>
                </select>
              </div>
              <div class="field">
                <label>责任警员</label>
                <select v-model="params.officer" class="select">
                  <option value="">请选择</option>
                  <option value="张三">张三</option>
                  <option value="李四">李四</option>
                </select>
              </div>
            </div>

            <div class="check-group">
              <div class="check-label">维度</div>
              <div class="check-grid">
                <label v-for="item in dimensionOptions" :key="item" class="check-item">
                  <input type="checkbox" :checked="selectedDimensions.includes(item)" @change="toggle('dimensions', item)" />
                  <span>{{ item }}</span>
                </label>
              </div>
            </div>

            <div class="check-group">
              <div class="check-label">指标</div>
              <div class="check-grid">
                <label v-for="item in indicatorOptions" :key="item" class="check-item">
                  <input type="checkbox" :checked="selectedIndicators.includes(item)" @change="toggle('indicators', item)" />
                  <span>{{ item }}</span>
                </label>
              </div>
            </div>

            <div class="check-group">
              <div class="check-label">位置</div>
              <div class="check-grid">
                <label v-for="item in locationOptions" :key="item" class="check-item">
                  <input type="checkbox" :checked="selectedLocations.includes(item)" @change="toggle('locations', item)" />
                  <span>{{ item }}</span>
                </label>
              </div>
            </div>
          </div>
        </section>

        <section class="block operator-block">
          <div class="block-title static">
            <span>算子工作清单</span>
          </div>
          <p class="operator-tip">从左侧拖入算子到此处，配置数据后可插入报告。</p>
          <button class="query-btn" type="button" @click="runQuery">
            <Search :size="15" />
            <span>查询生成</span>
          </button>
          <div class="empty-box">
            <Inbox :size="40" :stroke-width="1.4" />
            <p>配置完成后自动生成报告</p>
          </div>
        </section>
      </template>

      <template v-else-if="activeMode === 'ai'">
        <section class="ai-panel">
          <p class="ai-desc">基于当前报告上下文生成草稿，生成后需人工核对再保存。</p>
          <button class="primary-action" type="button" @click="emit('generateDraft')">
            <Sparkles :size="15" /> 生成全文草稿
          </button>
          <button class="secondary-action" type="button" @click="emit('insertHtml', '<p>经综合研判，相关警情总体平稳，需持续关注重点区域和高发时段。</p>')">
            插入研判建议
          </button>
          <button class="secondary-action" type="button" @click="emit('insertHtml', '<p>请对以上数据进一步核实，避免直接使用未经确认的 AI 草稿。</p>')">
            插入核验提示
          </button>
        </section>
      </template>

      <template v-else>
        <section class="component-panel">
          <p class="ai-desc">选择统计组件执行后，可将结果插入正文。</p>
          <button
            v-for="item in componentNames"
            :key="item"
            class="component-item"
            type="button"
            @click="emit('insertHtml', `<h3>${item}</h3><p>[组件结果占位] ${item}，待接入真实统计结果。</p>`)"
          >
            {{ item }}
            <span>插入</span>
          </button>
        </section>
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

.head-actions {
  display: flex;
  gap: 2px;
}

.icon-btn {
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #8c8c8c;
  display: grid;
  place-items: center;
}

.icon-btn:hover {
  color: #1890ff;
  background: #e6f7ff;
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  padding: 8px 10px;
  gap: 4px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.mode-tabs button {
  height: 30px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #595959;
  font-size: 13px;
}

.mode-tabs button.active {
  color: #1890ff;
  background: #e6f7ff;
  font-weight: 600;
}

.panel-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 10px 12px 16px;
}

.block {
  margin-bottom: 12px;
}

.block-title {
  width: 100%;
  border: 0;
  background: transparent;
  padding: 4px 0 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #262626;
  font-size: 13px;
  font-weight: 600;
}

.block-title.static {
  cursor: default;
}

.chevron {
  color: #8c8c8c;
  font-size: 12px;
  transition: transform .2s;
}

.chevron.open {
  transform: rotate(180deg);
}

.preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.preset-btn {
  height: 26px;
  padding: 0 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fff;
  color: #595959;
  font-size: 12px;
}

.preset-btn.active,
.preset-btn:hover {
  color: #1890ff;
  border-color: #1890ff;
  background: #e6f7ff;
}

.field {
  margin-bottom: 10px;
}

.field label,
.check-label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: #8c8c8c;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.range-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 6px;
  align-items: center;
}

.range-sep {
  color: #8c8c8c;
  font-size: 12px;
}

.input,
.select {
  width: 100%;
  height: 30px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 0 8px;
  background: #fff;
  color: #262626;
  font-size: 12px;
  outline: none;
}

.input:focus,
.select:focus {
  border-color: #40a9ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, .15);
}

.check-group {
  margin-bottom: 10px;
}

.check-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px 4px;
}

.check-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #595959;
  cursor: pointer;
}

.check-item input {
  accent-color: #1890ff;
}

.operator-tip {
  margin: 0 0 10px;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.6;
}

.query-btn {
  width: 100%;
  height: 34px;
  border: 0;
  border-radius: 4px;
  background: #1890ff;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-bottom: 12px;
}

.query-btn:hover {
  background: #40a9ff;
}

.empty-box {
  min-height: 160px;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  background: #fafafa;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  color: #bfbfbf;
  text-align: center;
  padding: 20px;
}

.empty-box p {
  margin: 0;
  font-size: 12px;
  color: #8c8c8c;
}

.ai-panel,
.component-panel {
  display: grid;
  gap: 10px;
}

.ai-desc {
  margin: 0 0 4px;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.6;
}

.primary-action,
.secondary-action,
.component-item {
  width: 100%;
  border: 0;
  border-radius: 4px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
}

.primary-action {
  background: #1890ff;
  color: #fff;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
}

.secondary-action {
  background: #fff7e6;
  color: #ad6800;
}

.component-item {
  background: #f5f5f5;
  color: #262626;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.component-item span {
  color: #1890ff;
  font-size: 12px;
}

.component-item:hover {
  background: #e6f7ff;
}
</style>
