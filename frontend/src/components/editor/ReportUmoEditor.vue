<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { UmoEditor } from '@umoteam/editor'
import { Node } from '@tiptap/core'
import '@umoteam/editor/style'
import type { EditorPageConfig, ReportEditorConfig } from '@/api/report'
import type { ReportQueryBlock } from '@/api/reportSearch'

const props = withDefaults(
  defineProps<{
    title?: string
    modelValue?: string
    readOnly?: boolean
    editorConfig?: ReportEditorConfig
    documentJson?: Record<string, unknown> | null
    dynamicBlockCount?: number
    refreshingQueryBlocks?: boolean
    renderQueryBlock?: (block: ReportQueryBlock) => string
    queryBlocks?: Record<string, ReportQueryBlock>
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
    dynamicBlockCount: 0,
    refreshingQueryBlocks: false,
    renderQueryBlock: undefined,
    queryBlocks: () => ({}),
    saveHandler: undefined,
    exportWordHandler: undefined,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:editorConfig': [value: ReportEditorConfig]
  'update:documentJson': [value: Record<string, unknown> | null]
  save: [value: string, config: ReportEditorConfig, documentJson: Record<string, unknown> | null]
  refreshQueryBlocks: []
  queryBlockDropped: [block: ReportQueryBlock]
  queryBlockIdsChanged: [ids: string[]]
}>()

const shellRef = ref<HTMLElement | null>(null)
const umoRef = ref<UmoEditorInstance | null>(null)
const restoringInitialContent = ref(true)
const currentEditorConfig = ref<ReportEditorConfig>(normalizeEditorConfig(props.editorConfig))
const AUTO_SAVE_DEBOUNCE_MS = 2000
let autoSaveTimer: number | null = null
let autoSaveSequence = 0

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

interface TiptapEditorInstance {
  commands?: {
    insertContent?: (content: unknown) => boolean
    insertContentAt?: (position: number, content: unknown) => boolean
  }
  chain?: () => { focus: () => { insertContent: (content: unknown) => { run: () => boolean } } }
  state?: { doc?: { descendants?: (callback: (node: any, position: number) => void) => void }; tr?: any }
  view?: {
    posAtCoords?: (coords: { left: number; top: number }) => { pos: number } | null
    dispatch?: (transaction: unknown) => void
  }
}

interface UmoEditorInstance {
  setContent?: (content: string | Record<string, unknown>, options?: Record<string, unknown>) => void
  getHTML?: () => string
  getJSON?: () => Record<string, unknown>
  setPage?: (params: UmoPageParams) => void
  getPage?: () => unknown
  useEditor?: () => TiptapEditorInstance | undefined
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
      const migrated = migrateLegacyQueryBlocks(props.queryBlocks)
      restoringInitialContent.value = false
      nextTick(() => {
        const currentHtml = umoRef.value?.getHTML?.() || ''
        const currentJson = umoRef.value?.getJSON?.() || null
        if (migrated) {
          emit('update:modelValue', currentHtml)
          emit('update:documentJson', currentJson)
          scheduleAutoSave()
        }
        emitQueryBlockIds(currentJson)
      })
    }, 0)
  })
}

function insertContent(content: unknown, position?: number) {
  const editor = umoRef.value?.useEditor?.()
  if (position !== undefined && editor?.commands?.insertContentAt) {
    return editor.commands.insertContentAt(position, content)
  }
  return editor?.chain?.().focus().insertContent(content).run()
    ?? editor?.commands?.insertContent?.(content)
    ?? false
}

function serializeQueryBlock(block: ReportQueryBlock) {
  return JSON.stringify(block)
}

function parseQueryBlock(value: unknown): ReportQueryBlock | null {
  if (typeof value !== 'string' || !value) return null
  try {
    const block = JSON.parse(value) as ReportQueryBlock
    return block?.id && block?.query ? block : null
  } catch {
    return null
  }
}

function renderQueryBlockElement(block: ReportQueryBlock) {
  const dom = document.createElement('div')
  dom.dataset.reportQueryNode = 'true'
  dom.dataset.blockJson = serializeQueryBlock(block)
  dom.contentEditable = 'false'
  dom.innerHTML = props.renderQueryBlock?.(block) || block.title
  return dom
}

const reportQueryBlockExtension = Node.create({
  name: 'reportQueryBlock',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes() {
    return {
      blockJson: {
        default: '',
        parseHTML: (element: HTMLElement) => element.dataset.blockJson || '',
      },
    }
  },
  parseHTML() {
    return [{ tag: 'div[data-report-query-node]' }]
  },
  renderHTML({ node }) {
    const block = parseQueryBlock(node.attrs.blockJson)
    return block ? renderQueryBlockElement(block) : ['div', { 'data-report-query-node': 'true' }, '数据块无效']
  },
  addNodeView() {
    return ({ node }) => {
      let currentNode = node
      const render = () => {
        const block = parseQueryBlock(currentNode.attrs.blockJson)
        return block ? renderQueryBlockElement(block) : document.createElement('div')
      }
      let dom = render()
      return {
        dom,
        update(updatedNode) {
          if (updatedNode.type.name !== 'reportQueryBlock') return false
          currentNode = updatedNode
          const replacement = render()
          dom.replaceWith(replacement)
          dom = replacement
          return true
        },
      }
    }
  },
})

function collectQueryBlockIds(documentJson?: Record<string, unknown> | null) {
  const ids: string[] = []
  const visit = (node: unknown) => {
    if (!node || typeof node !== 'object') return
    const value = node as { type?: string; attrs?: { blockJson?: unknown }; content?: unknown[] }
    if (value.type === 'reportQueryBlock') {
      const block = parseQueryBlock(value.attrs?.blockJson)
      if (block?.id) ids.push(block.id)
    }
    value.content?.forEach(visit)
  }
  visit(documentJson)
  return ids
}

function emitQueryBlockIds(documentJson?: Record<string, unknown> | null) {
  emit('queryBlockIdsChanged', collectQueryBlockIds(documentJson || umoRef.value?.getJSON?.() || null))
}

function insertQueryBlockNode(block: ReportQueryBlock, position?: number) {
  return insertContent({ type: 'reportQueryBlock', attrs: { blockJson: serializeQueryBlock(block) } }, position)
}

function migrateLegacyQueryBlocks(blocks: Record<string, ReportQueryBlock>) {
  const editor = umoRef.value
  const currentHtml = editor?.getHTML?.()
  if (!editor?.setContent || !currentHtml) return false
  const dynamicBlocks = Object.values(blocks).filter((block) => block.mode === 'dynamic')
  if (!dynamicBlocks.length) return false

  const document = new DOMParser().parseFromString(`<body>${currentHtml}</body>`, 'text/html')
  const labels = Array.from(document.body.querySelectorAll('span')).filter((element) => element.textContent?.trim() === '动态数据')
  let migrated = 0
  labels.forEach((label, index) => {
    const block = dynamicBlocks[index]
    const heading = label.closest('p')
    if (!block || !heading) return
    const table = heading.nextElementSibling?.tagName === 'TABLE' ? heading.nextElementSibling : null
    const marker = renderQueryBlockElement(block)
    heading.replaceWith(marker)
    table?.remove()
    migrated += 1
  })
  if (!migrated) return false
  editor.setContent(document.body.innerHTML, { emitUpdate: true, focusPosition: null })
  return true
}

function replaceQueryBlocks(blocks: Record<string, ReportQueryBlock>) {
  const editor = umoRef.value?.useEditor?.()
  if (!editor?.state?.doc?.descendants || !editor.state.tr || !editor.view?.dispatch) return false
  let transaction = editor.state.tr
  let changed = false
  editor.state.doc.descendants((node: any, position: number) => {
    if (node.type?.name !== 'reportQueryBlock') return
    const current = parseQueryBlock(node.attrs?.blockJson)
    const block = current?.id ? blocks[current.id] : undefined
    if (!block || block.mode !== 'dynamic') return
    transaction = transaction.setNodeMarkup(position, undefined, { ...node.attrs, blockJson: serializeQueryBlock(block) })
    changed = true
  })
  if (!changed) return false
  editor.view.dispatch(transaction)
  nextTick(() => {
    const json = umoRef.value?.getJSON?.() || null
    emit('update:modelValue', umoRef.value?.getHTML?.() || '')
    emit('update:documentJson', json)
    emitQueryBlockIds(json)
    scheduleAutoSave()
  })
  return true
}

function handleDragOver(event: DragEvent) {
  if (event.dataTransfer?.types.includes('application/vnd.yw-report-query-block+json')) {
    event.preventDefault()
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy'
  }
}

function handleDrop(event: DragEvent) {
  const raw = event.dataTransfer?.getData('application/vnd.yw-report-query-block+json')
  if (!raw) return
  event.preventDefault()
  event.stopPropagation()
  try {
    const block = JSON.parse(raw) as ReportQueryBlock
    if (!block.id || !block.query || !props.renderQueryBlock) return
    const editor = umoRef.value?.useEditor?.()
    const position = editor?.view?.posAtCoords?.({ left: event.clientX, top: event.clientY })?.pos
    insertQueryBlockNode(block, position)
    emit('queryBlockDropped', block)
  } catch (error) {
    console.error('动态数据块拖入失败', error)
  }
}

function clearAutoSaveTimer() {
  if (autoSaveTimer === null) return
  window.clearTimeout(autoSaveTimer)
  autoSaveTimer = null
}

function scheduleAutoSave() {
  if (props.readOnly || !props.saveHandler || restoringInitialContent.value) return
  clearAutoSaveTimer()
  const sequence = ++autoSaveSequence
  autoSaveTimer = window.setTimeout(async () => {
    autoSaveTimer = null
    if (sequence !== autoSaveSequence) return
    const html = umoRef.value?.getHTML?.() || props.modelValue
    if (!html?.trim() || html === '<p></p>') return
    const documentJson = umoRef.value?.getJSON?.() || props.documentJson || null
    try {
      await props.saveHandler?.(html, updateEditorConfig(), documentJson)
    } catch (error) {
      console.error('报告自动保存失败', error)
    }
  }, AUTO_SAVE_DEBOUNCE_MS)
}

function handlePageOrientationChanged(payload: unknown) {
  const data = payload as { pageOrientation?: unknown }
  const orientation = data.pageOrientation === 'landscape' ? 'landscape' : 'portrait'
  updateEditorConfig({ ...readEditorConfig().page, orientation })
  scheduleAutoSave()
}

async function exportWord() {
  clearAutoSaveTimer()
  autoSaveSequence += 1
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

onBeforeUnmount(() => {
  clearAutoSaveTimer()
})

defineExpose({ insertContent, insertQueryBlockNode, migrateLegacyQueryBlocks, replaceQueryBlocks })

const editorOptions = computed(() => ({
  locale: 'zh-CN',
  extensions: [reportQueryBlockExtension],
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
    // Disable interval saving and use a trailing-edge debounce instead.
    autoSave: {
      enabled: false,
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
    emitQueryBlockIds(documentJson)
    nextTick(() => {
      updateEditorConfig()
      scheduleAutoSave()
    })
  },
  onSave: async (payload: unknown, pagePayload: unknown, documentPayload: unknown) => {
    clearAutoSaveTimer()
    autoSaveSequence += 1
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
  <div ref="shellRef" class="umo-shell" @dragover="handleDragOver" @drop="handleDrop">
    <UmoEditor
      ref="umoRef"
      v-bind="editorOptions"
      @created="handleCreated"
      @changed:page-orientation="handlePageOrientationChanged"
    >
      <template #toolbar_export>
        <button
          v-if="dynamicBlockCount"
          class="word-export-button refresh-data-button"
          type="button"
          title="按当前全局参数更新动态数据块"
          :disabled="refreshingQueryBlocks"
          @click="emit('refreshQueryBlocks')"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 11a8 8 0 1 0-2.34 5.66" />
            <path d="M20 4v7h-7" />
          </svg>
          <span>{{ refreshingQueryBlocks ? '更新中' : `更新数据(${dynamicBlockCount})` }}</span>
        </button>
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

.word-export-button:disabled {
  cursor: wait;
  opacity: 0.55;
}

.refresh-data-button {
  width: 76px;
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
