<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { UmoEditor } from '@umoteam/editor'
import '@umoteam/editor/style'
import type { EditorPageConfig, ReportEditorConfig } from '@/api/report'

const props = withDefaults(
  defineProps<{
    title?: string
    modelValue?: string
    readOnly?: boolean
    editorConfig?: ReportEditorConfig
    documentJson?: Record<string, unknown> | null
    saveHandler?: (value: string, config: ReportEditorConfig, documentJson: Record<string, unknown> | null) => Promise<void>
    exportWordHandler?: (value: string, config: ReportEditorConfig, documentJson: Record<string, unknown> | null) => Promise<void>
  }>(),
  {
    title: '未命名报告',
    modelValue: '',
    readOnly: false,
    editorConfig: () => ({
      page: {
        orientation: 'portrait',
        margin: { left: 2.54, right: 2.54, top: 2.54, bottom: 2.54 },
        layout: 'page',
        background: '#ffffff',
        size: null,
      },
    }),
    documentJson: null,
    saveHandler: undefined,
    exportWordHandler: undefined,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:editorConfig': [value: ReportEditorConfig]
  'update:documentJson': [value: Record<string, unknown> | null]
  save: [value: string, config: ReportEditorConfig, documentJson: Record<string, unknown> | null]
}>()

const shellRef = ref<HTMLElement | null>(null)
const umoRef = ref<UmoEditorInstance | null>(null)
const restoringInitialContent = ref(true)
const currentEditorConfig = ref<ReportEditorConfig>(normalizeEditorConfig(props.editorConfig))

interface UmoEditorPayload {
  html?: string
  json?: unknown
  text?: string
  editor?: { getHTML?: () => string }
  getHTML?: () => string
}

interface UmoDocumentPayload {
  content?: string
}

interface UmoPageParams {
  orientation?: EditorPageConfig['orientation']
  margin?: EditorPageConfig['margin']
  layout?: EditorPageConfig['layout']
  background?: string
  size?: string
}

interface UmoEditorInstance {
  setContent?: (content: string | Record<string, unknown>, options?: Record<string, unknown>) => void
  getHTML?: () => string
  getJSON?: () => Record<string, unknown>
  setPage?: (params: UmoPageParams) => void
  getPage?: () => unknown
  useEditor?: () => unknown
}

function createDefaultEditorConfig(): ReportEditorConfig {
  return {
    page: {
      orientation: 'portrait',
      margin: { left: 2.54, right: 2.54, top: 2.54, bottom: 2.54 },
      layout: 'page',
      background: '#ffffff',
      size: null,
    },
  }
}

function normalizeEditorConfig(value: ReportEditorConfig | undefined): ReportEditorConfig {
  const defaults = createDefaultEditorConfig()
  const page = value?.page
  return {
    page: {
      orientation: page?.orientation === 'landscape' ? 'landscape' : 'portrait',
      margin: { ...defaults.page.margin, ...(page?.margin || {}) },
      layout: page?.layout === 'web' ? 'web' : 'page',
      background: page?.background || defaults.page.background,
      size: page?.size ? { ...page.size } : null,
    },
  }
}

function escapeHtml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function readEditorConfig(pagePayload?: unknown): ReportEditorConfig {
  const page = (pagePayload || umoRef.value?.getPage?.()) as Partial<EditorPageConfig> | undefined
  return normalizeEditorConfig({
    page: {
      ...currentEditorConfig.value.page,
      ...(page || {}),
      margin: { ...currentEditorConfig.value.page.margin, ...(page?.margin || {}) },
    },
  })
}

function updateEditorConfig(pagePayload?: unknown) {
  const config = readEditorConfig(pagePayload)
  currentEditorConfig.value = config
  emit('update:editorConfig', config)
  return config
}

function applyInitialContent() {
  const content = props.documentJson || props.modelValue
  if (!content || (typeof content === 'string' && !content.trim())) return false
  const editor = umoRef.value
  if (!editor?.setContent || !editor.useEditor?.()) return false
  editor.setContent(content, { emitUpdate: false, focusPosition: null })
  return true
}

function ensureInitialContent(retries = 20) {
  if (applyInitialContent()) return
  if (retries <= 0) return
  window.setTimeout(() => ensureInitialContent(retries - 1), 100)
}

function resolveUmoPageSize(page: EditorPageConfig) {
  const size = page.size
  if (!size) return undefined
  if (typeof size.label === 'string' && ['A3', 'A4', 'A5', 'B5'].includes(size.label)) return size.label

  const width = Number(size.width)
  const height = Number(size.height)
  const dimensions = [Math.min(width, height), Math.max(width, height)]
  const knownSizes = [
    { label: 'A3', dimensions: [29.7, 42] },
    { label: 'A4', dimensions: [21, 29.7] },
    { label: 'A5', dimensions: [14.8, 21] },
    { label: 'B5', dimensions: [17.6, 25] },
  ]
  return knownSizes.find(({ dimensions: expected }) =>
    Math.abs(dimensions[0] - expected[0]) < 0.01 && Math.abs(dimensions[1] - expected[1]) < 0.01,
  )?.label
}

function applyEditorConfig() {
  const page = currentEditorConfig.value.page
  const params: UmoPageParams = {
    orientation: page.orientation,
    margin: { ...page.margin },
    layout: page.layout,
    background: page.background,
  }
  const size = resolveUmoPageSize(page)
  if (size) params.size = size
  umoRef.value?.setPage?.(params)
}

function handleCreated() {
  nextTick(() => {
    ensureInitialContent()
    applyEditorConfig()
    window.setTimeout(() => {
      restoringInitialContent.value = false
    }, 0)
  })
}

function handlePageOrientationChanged(payload: unknown) {
  const data = payload as { pageOrientation?: unknown }
  const orientation = data.pageOrientation === 'landscape' ? 'landscape' : 'portrait'
  updateEditorConfig({ ...readEditorConfig().page, orientation })
}

async function exportWord() {
  if (!props.exportWordHandler) return
  const html = umoRef.value?.getHTML?.() || props.modelValue
  if (!html?.trim()) return
  const documentJson = umoRef.value?.getJSON?.() || props.documentJson || null
  await props.exportWordHandler(html, updateEditorConfig(), documentJson)
}

watch(
  () => props.editorConfig,
  (config) => {
    currentEditorConfig.value = normalizeEditorConfig(config)
    nextTick(applyEditorConfig)
  },
  { deep: true },
)

watch(
  () => props.modelValue,
  (content) => {
    if (props.documentJson || !content?.trim()) return
    const currentHtml = umoRef.value?.getHTML?.()
    if (currentHtml !== content) nextTick(() => ensureInitialContent())
  },
)

onMounted(() => {
  nextTick(applyEditorConfig)
})

const editorOptions = computed(() => ({
  locale: 'zh-CN',
  height: '100%',
  document: {
    title: props.title,
    content: props.documentJson || props.modelValue || `<h1 style="text-align:center;">${escapeHtml(props.title)}</h1><p></p>`,
    placeholder: {
      zh_CN: '请在此编辑警情研判报告...',
      en_US: 'Edit report here...',
    },
    readOnly: props.readOnly,
    autofocus: false,
    enableBubbleMenu: !props.readOnly,
    enableBlockMenu: !props.readOnly,
    autoSave: {
      enabled: true,
      interval: 3000,
    },
  },
  toolbar: {
    showSaveLabel: !props.readOnly,
    defaultMode: 'ribbon',
    menus: ['base', 'insert', 'table', 'tools', 'page', 'export'],
  },
  page: {
    defaultOrientation: currentEditorConfig.value.page.orientation,
    defaultMargin: currentEditorConfig.value.page.margin,
    defaultBackground: currentEditorConfig.value.page.background,
    layouts: ['page', 'web'],
    showToc: false,
    showBreakMarks: false,
  },
  onChanged: (payload: unknown) => {
    if (restoringInitialContent.value) return
    const data = payload as UmoEditorPayload
    const html = data.html ?? data.editor?.getHTML?.() ?? data.getHTML?.()
    const documentJson = data.json && typeof data.json === 'object'
      ? data.json as Record<string, unknown>
      : umoRef.value?.getJSON?.() || null
    if (typeof html === 'string') emit('update:modelValue', html)
    emit('update:documentJson', documentJson)
    nextTick(() => updateEditorConfig())
  },
  onSave: async (payload: unknown, pagePayload: unknown, documentPayload: unknown) => {
    const data = payload as UmoEditorPayload
    const documentData = documentPayload as UmoDocumentPayload | undefined
    const html = documentData?.content ?? data.html ?? data.editor?.getHTML?.() ?? data.getHTML?.() ?? props.modelValue
    if (!html || html === '<p></p>') {
      return { status: 'error', message: '未读取到编辑器内容，请稍后重试' }
    }
    const config = updateEditorConfig(pagePayload)
    const documentJson = data.json && typeof data.json === 'object'
      ? data.json as Record<string, unknown>
      : umoRef.value?.getJSON?.() || props.documentJson || null
    emit('update:modelValue', html)
    emit('update:documentJson', documentJson)
    if (props.saveHandler) {
      await props.saveHandler(html, config, documentJson)
    } else {
      emit('save', html, config, documentJson)
    }
    return { status: 'success', message: '已保存到服务器' }
  },
}))
</script>

<template>
  <div ref="shellRef" class="umo-shell">
    <UmoEditor
      ref="umoRef"
      v-bind="editorOptions"
      @created="handleCreated"
      @changed:page-orientation="handlePageOrientationChanged"
    >
      <template #toolbar_export>
        <button class="word-export-button" type="button" title="导出 Word 文档" @click="exportWord">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 2.75h8.2L19 7.55v13.7H6z" />
            <path d="M14 2.75v5h5" />
            <path d="M8.2 11.2l1.25 5.05 1.45-5.05 1.45 5.05 1.25-5.05" />
          </svg>
          <span>Word 文档</span>
        </button>
      </template>
    </UmoEditor>
  </div>
</template>

<style scoped>
.umo-shell {
  height: 100%;
  min-height: 0;
  background: #f5f6f8;
}

.umo-shell :deep(.umo-editor),
.umo-shell :deep(.umo-editor-container),
.umo-shell :deep(.umo-editor > div) {
  height: 100% !important;
}

.word-export-button {
  width: 64px;
  min-height: 58px;
  padding: 6px 5px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #303133;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  font-size: 12px;
  font-family: inherit;
}

.word-export-button:hover {
  background: rgba(24, 144, 255, 0.1);
  color: #1890ff;
}

.word-export-button svg {
  width: 24px;
  height: 24px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
