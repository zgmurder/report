<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { UmoEditor } from '@umoteam/editor'
import { Extension, Node } from '@tiptap/core'
import { Plugin } from '@tiptap/pm/state'
import '@umoteam/editor/style'
import type { EditorPageConfig, ReportEditorConfig } from '@/api/report'
import type { ReportQueryBlock } from '@/api/reportSearch'
import { getTemplateContent, listTemplates, type ReportTemplateItem } from '@/api/catalog'

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
  refreshQueryBlocks: [ids?: string[]]
  queryBlockDropped: [block: ReportQueryBlock]
  queryBlockDuplicated: [sourceId: string, duplicatedId: string]
  queryBlockIdsChanged: [ids: string[]]
}>()

const shellRef = ref<HTMLElement | null>(null)
const umoRef = ref<UmoEditorInstance | null>(null)
const queryBlockRegistry = new Map<string, ReportQueryBlock>()
const restoringInitialContent = ref(true)
const templateMenuVisible = ref(false)
const templateMenuLoading = ref(false)
const templateInsertLoadingId = ref<number | null>(null)
const templateMenuItems = ref<ReportTemplateItem[]>([])
const templateMenuQuery = ref('')
const templateMenuActiveIndex = ref(0)
const templateMenuPosition = ref({ left: 0, top: 0 })
let templateTriggerPosition: number | null = null
const currentEditorConfig = ref<ReportEditorConfig>(normalizeEditorConfig(props.editorConfig))
const AUTO_SAVE_DEBOUNCE_MS = 2000
const AUTO_SAVE_STORAGE_KEY = 'report-editor-auto-save-enabled'
const autoSaveEnabled = ref(localStorage.getItem(AUTO_SAVE_STORAGE_KEY) !== 'false')
let autoSaveTimer: number | null = null
let autoSaveSequence = 0
let reconcilingQueryBlocks = false

const REPORT_QUERY_BLOCK_MIME = 'application/vnd.yw-report-query-block+json'

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
    insertContentAt?: (position: number | { from: number; to: number }, content: unknown) => boolean
  }
  chain?: () => { focus: () => { insertContent: (content: unknown) => { run: () => boolean } } }
  state?: { selection?: { from: number; empty?: boolean }; doc?: { descendants?: (callback: (node: any, position: number) => void) => void }; tr?: any }
  view?: {
    posAtCoords?: (coords: { left: number; top: number }) => { pos: number } | null
    dispatch?: (transaction: unknown) => void
  }
}

interface UmoEditorInstance {
  setContent?: (content: string | Record<string, unknown>, options?: Record<string, unknown>) => void
  getHTML?: () => string
  getJSON?: () => Record<string, unknown>
  saveContent?: (showMessage?: boolean) => Promise<void>
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
  editor.setContent(content, {
    emitUpdate: false,
    focusPosition: 'start',
    focusOptions: { scrollIntoView: false },
  })
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
      const reconciled = reconcileQueryBlockNodes()
      restoringInitialContent.value = false
      nextTick(() => {
        const currentHtml = umoRef.value?.getHTML?.() || ''
        const currentJson = umoRef.value?.getJSON?.() || null
        if (migrated || reconciled) {
          emit('update:modelValue', currentHtml)
          emit('update:documentJson', currentJson)
          scheduleAutoSave()
        }
        emitQueryBlockIds(currentJson)
      })
    }, 0)
  })
}

function closeTemplateMenu() {
  templateMenuVisible.value = false
  templateMenuQuery.value = ''
  templateMenuActiveIndex.value = 0
  templateTriggerPosition = null
}

async function openTemplateMenu(view: any, triggerPosition: number) {
  if (props.readOnly) return
  templateTriggerPosition = triggerPosition
  templateMenuQuery.value = ''
  templateMenuActiveIndex.value = 0
  const coords = view.coordsAtPos(Math.min(triggerPosition + 1, view.state.doc.content.size))
  templateMenuPosition.value = {
    left: Math.min(coords.left, window.innerWidth - 340),
    top: Math.min(coords.bottom + 6, window.innerHeight - 320),
  }
  templateMenuVisible.value = true
  if (templateMenuItems.value.length) return
  templateMenuLoading.value = true
  try {
    templateMenuItems.value = (await listTemplates()).filter(
      (item) => item.status === 'enabled' && Boolean(item.original_filename),
    )
  } catch (error) {
    console.error('模板列表加载失败', error)
  } finally {
    templateMenuLoading.value = false
  }
}

const filteredTemplateMenuItems = computed(() => {
  const query = templateMenuQuery.value.trim().toLowerCase()
  if (!query) return templateMenuItems.value
  return templateMenuItems.value.filter((item) =>
    item.name.toLowerCase().includes(query) || item.description.toLowerCase().includes(query),
  )
})

function updateTemplateMenuFromEditor(view: any) {
  if (!templateMenuVisible.value || templateTriggerPosition === null) return
  const cursor = view.state.selection.from
  if (!view.state.selection.empty || cursor <= templateTriggerPosition) {
    closeTemplateMenu()
    return
  }
  const query = view.state.doc.textBetween(templateTriggerPosition + 1, cursor, '', '')
  if (query.includes('\n') || query.includes('@') || query.length > 30) {
    closeTemplateMenu()
    return
  }
  templateMenuQuery.value = query
  templateMenuActiveIndex.value = Math.min(templateMenuActiveIndex.value, Math.max(filteredTemplateMenuItems.value.length - 1, 0))
}

async function insertTemplateContent(item: ReportTemplateItem) {
  const editor = umoRef.value?.useEditor?.()
  if (!editor || templateTriggerPosition === null) return
  templateInsertLoadingId.value = item.id
  try {
    const content = await getTemplateContent(item.id)
    const cursor = editor.state?.selection?.from ?? templateTriggerPosition + 1
    const inserted = editor.commands?.insertContentAt?.(
      { from: templateTriggerPosition, to: cursor },
      content.html,
    ) ?? false
    if (!inserted) throw new Error('模板内容插入失败')
    closeTemplateMenu()
  } catch (error) {
    window.alert(error instanceof Error ? error.message : '模板内容加载失败')
  } finally {
    templateInsertLoadingId.value = null
  }
}

const templateMentionExtension = Extension.create({
  name: 'reportTemplateMention',
  addProseMirrorPlugins() {
    return [new Plugin({
      view: () => ({
        update(view) {
          updateTemplateMenuFromEditor(view)
        },
      }),
      props: {
        handleTextInput(view, from, _to, text) {
          if (text !== '@') return false
          window.setTimeout(() => openTemplateMenu(view, from), 0)
          return false
        },
        handleKeyDown(_view, event) {
          if (!templateMenuVisible.value) return false
          const items = filteredTemplateMenuItems.value
          if (event.key === 'Escape') {
            closeTemplateMenu()
            return true
          }
          if (event.key === 'ArrowDown') {
            templateMenuActiveIndex.value = items.length ? (templateMenuActiveIndex.value + 1) % items.length : 0
            return true
          }
          if (event.key === 'ArrowUp') {
            templateMenuActiveIndex.value = items.length ? (templateMenuActiveIndex.value - 1 + items.length) % items.length : 0
            return true
          }
          if (event.key === 'Enter' && items[templateMenuActiveIndex.value]) {
            void insertTemplateContent(items[templateMenuActiveIndex.value])
            return true
          }
          return false
        },
      },
    })]
  },
})

function insertContent(content: unknown, position?: number) {
  const editor = umoRef.value?.useEditor?.()
  if (position !== undefined && editor?.commands?.insertContentAt) {
    return editor.commands.insertContentAt(position, content)
  }
  return editor?.chain?.().focus().insertContent(content).run()
    ?? editor?.commands?.insertContent?.(content)
    ?? false
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

function resolveNodeQueryBlock(attrs: Record<string, unknown> | undefined) {
  const blockId = typeof attrs?.blockId === 'string' ? attrs.blockId : ''
  if (blockId && (props.queryBlocks[blockId] || queryBlockRegistry.get(blockId))) {
    return props.queryBlocks[blockId] || queryBlockRegistry.get(blockId) || null
  }
  return parseQueryBlock(attrs?.blockJson)
}

function renderQueryBlockElement(
  block: ReportQueryBlock | null,
  attrs?: Record<string, unknown>,
  interactive = false,
) {
  const dom = document.createElement('div')
  dom.dataset.reportQueryNode = 'true'
  const blockId = block?.id || String(attrs?.blockId || '')
  const mode = block?.mode || String(attrs?.mode || 'dynamic')
  if (blockId) dom.dataset.blockId = blockId
  dom.dataset.queryMode = mode
  dom.contentEditable = 'false'
  dom.innerHTML = block
    ? props.renderQueryBlock?.(block) || block.title
    : '<div style="padding:12px;color:#d03050;border:1px solid #f3c7cf;border-radius:8px;">数据块定义不存在</div>'
  if (interactive && block?.mode === 'dynamic') {
    dom.style.position = 'relative'
    const refreshButton = document.createElement('button')
    refreshButton.type = 'button'
    refreshButton.textContent = '更新此块'
    refreshButton.title = '按当前全局时间参数更新此数据块'
    refreshButton.style.cssText = 'position:absolute;right:12px;bottom:12px;padding:4px 10px;border:1px solid #91caff;border-radius:4px;background:#fff;color:#1677ff;cursor:pointer;font-size:12px;'
    refreshButton.addEventListener('mousedown', (event) => {
      event.preventDefault()
      event.stopPropagation()
    })
    refreshButton.addEventListener('click', (event) => {
      event.preventDefault()
      event.stopPropagation()
      emit('refreshQueryBlocks', [block.id])
    })
    dom.appendChild(refreshButton)
  }
  return dom
}

function readDraggedQueryBlock(event: DragEvent) {
  const raw = event.dataTransfer?.getData(REPORT_QUERY_BLOCK_MIME)
  if (!raw) return null
  try {
    const block = JSON.parse(raw) as ReportQueryBlock
    return block?.id && block?.query ? block : null
  } catch {
    return null
  }
}

const reportQueryBlockExtension = Node.create({
  name: 'reportQueryBlock',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes() {
    return {
      blockId: {
        default: '',
        parseHTML: (element: HTMLElement) => element.dataset.blockId || '',
      },
      mode: {
        default: 'dynamic',
        parseHTML: (element: HTMLElement) => element.dataset.queryMode || 'dynamic',
      },
      revision: {
        default: 0,
        parseHTML: (element: HTMLElement) => Number(element.dataset.revision || 0),
      },
      // 仅用于读取早期版本保存的 Tiptap JSON；首次加载后会迁移并清空。
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
    return renderQueryBlockElement(resolveNodeQueryBlock(node.attrs), node.attrs)
  },
  addNodeView() {
    return ({ node }) => {
      let currentNode = node
      const render = () => renderQueryBlockElement(resolveNodeQueryBlock(currentNode.attrs), currentNode.attrs, true)
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
  addProseMirrorPlugins() {
    const editor = this.editor
    return [
      new Plugin({
        props: {
          handleDOMEvents: {
            dragover(_view, event) {
              const dragEvent = event as DragEvent
              if (!dragEvent.dataTransfer?.types.includes(REPORT_QUERY_BLOCK_MIME)) return false
              dragEvent.preventDefault()
              dragEvent.dataTransfer.dropEffect = 'copy'
              return true
            },
            drop(view, event) {
              const dragEvent = event as DragEvent
              const block = readDraggedQueryBlock(dragEvent)
              if (!block) return false
              dragEvent.preventDefault()
              dragEvent.stopPropagation()
              const position = view.posAtCoords({ left: dragEvent.clientX, top: dragEvent.clientY })?.pos
                ?? editor.state.selection.from
              queryBlockRegistry.set(block.id, block)
              emit('queryBlockDropped', block)
              return editor.commands.insertContentAt(position, [
                {
                  type: 'reportQueryBlock',
                  attrs: { blockId: block.id, mode: block.mode, revision: 0, blockJson: '' },
                },
                { type: 'paragraph' },
              ])
            },
          },
        },
      }),
    ]
  },
})

function collectQueryBlockIds(documentJson?: Record<string, unknown> | null) {
  const ids: string[] = []
  const visit = (node: unknown) => {
    if (!node || typeof node !== 'object') return
    const value = node as { type?: string; attrs?: { blockId?: unknown; blockJson?: unknown }; content?: unknown[] }
    if (value.type === 'reportQueryBlock') {
      const legacyBlock = parseQueryBlock(value.attrs?.blockJson)
      const blockId = typeof value.attrs?.blockId === 'string' ? value.attrs.blockId : legacyBlock?.id
      if (blockId) ids.push(blockId)
    }
    value.content?.forEach(visit)
  }
  visit(documentJson)
  return ids
}

function emitQueryBlockIds(documentJson?: Record<string, unknown> | null) {
  emit('queryBlockIdsChanged', collectQueryBlockIds(documentJson || umoRef.value?.getJSON?.() || null))
}

function reconcileQueryBlockNodes() {
  if (reconcilingQueryBlocks) return false
  const editor = umoRef.value?.useEditor?.()
  if (!editor?.state?.doc?.descendants || !editor.state.tr || !editor.view?.dispatch) return false

  const seen = new Set<string>()
  let transaction = editor.state.tr
  let changed = false
  editor.state.doc.descendants((node: any, position: number) => {
    if (node.type?.name !== 'reportQueryBlock') return
    const legacyBlock = parseQueryBlock(node.attrs?.blockJson)
    let blockId = String(node.attrs?.blockId || legacyBlock?.id || '').trim()
    const mode = node.attrs?.mode === 'snapshot' || legacyBlock?.mode === 'snapshot' ? 'snapshot' : 'dynamic'
    if (legacyBlock) emit('queryBlockDropped', legacyBlock)
    if (!blockId) blockId = crypto.randomUUID()
    if (seen.has(blockId)) {
      const sourceId = blockId
      const duplicatedId = crypto.randomUUID()
      const source = props.queryBlocks[sourceId] || queryBlockRegistry.get(sourceId)
      if (source) queryBlockRegistry.set(duplicatedId, { ...source, id: duplicatedId, title: `${source.title}（副本）` })
      emit('queryBlockDuplicated', sourceId, duplicatedId)
      blockId = duplicatedId
    }
    seen.add(blockId)
    if (
      node.attrs?.blockId === blockId &&
      node.attrs?.mode === mode &&
      !node.attrs?.blockJson
    ) return
    transaction = transaction.setNodeMarkup(position, undefined, {
      ...node.attrs,
      blockId,
      mode,
      blockJson: '',
    })
    changed = true
  })
  if (!changed) return false
  reconcilingQueryBlocks = true
  editor.view.dispatch(transaction)
  nextTick(() => {
    reconcilingQueryBlocks = false
    const json = umoRef.value?.getJSON?.() || null
    emit('update:modelValue', umoRef.value?.getHTML?.() || '')
    emit('update:documentJson', json)
    emitQueryBlockIds(json)
    scheduleAutoSave()
  })
  return true
}

function insertQueryBlockNode(block: ReportQueryBlock, position?: number) {
  queryBlockRegistry.set(block.id, block)
  return insertContent([
    {
      type: 'reportQueryBlock',
      attrs: { blockId: block.id, mode: block.mode, revision: 0, blockJson: '' },
    },
    { type: 'paragraph' },
  ], position)
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
    const marker = renderQueryBlockElement(block, { blockId: block.id, mode: block.mode })
    heading.replaceWith(marker)
    table?.remove()
    migrated += 1
  })
  if (!migrated) return false
  editor.setContent(document.body.innerHTML, {
    emitUpdate: true,
    focusPosition: 'start',
    focusOptions: { scrollIntoView: false },
  })
  return true
}

function replaceQueryBlocks(blocks: Record<string, ReportQueryBlock>) {
  const editor = umoRef.value?.useEditor?.()
  if (!editor?.state?.doc?.descendants || !editor.state.tr || !editor.view?.dispatch) return false
  let transaction = editor.state.tr
  let changed = false
  editor.state.doc.descendants((node: any, position: number) => {
    if (node.type?.name !== 'reportQueryBlock') return
    const legacyBlock = parseQueryBlock(node.attrs?.blockJson)
    const blockId = String(node.attrs?.blockId || legacyBlock?.id || '')
    const block = blockId ? blocks[blockId] : undefined
    if (!block || block.mode !== 'dynamic') return
    transaction = transaction.setNodeMarkup(position, undefined, {
      ...node.attrs,
      blockId,
      mode: block.mode,
      revision: Number(node.attrs?.revision || 0) + 1,
      blockJson: '',
    })
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

function clearAutoSaveTimer() {
  if (autoSaveTimer === null) return
  window.clearTimeout(autoSaveTimer)
  autoSaveTimer = null
}

function scheduleAutoSave() {
  if (!autoSaveEnabled.value || props.readOnly || !props.saveHandler || restoringInitialContent.value) return
  clearAutoSaveTimer()
  const sequence = ++autoSaveSequence
  autoSaveTimer = window.setTimeout(async () => {
    autoSaveTimer = null
    if (sequence !== autoSaveSequence) return
    const html = umoRef.value?.getHTML?.() || props.modelValue
    if (!html?.trim() || html === '<p></p>') return
    try {
      // 必须通过 Umo Editor 自身的保存入口执行，成功后它才会同步 savedAt，
      // 否则服务器虽然已保存，工具栏仍会一直显示“文档未保存”。
      if (umoRef.value?.saveContent) {
        await umoRef.value.saveContent(false)
        return
      }
      const documentJson = umoRef.value?.getJSON?.() || props.documentJson || null
      await props.saveHandler?.(html, updateEditorConfig(), documentJson)
    } catch (error) {
      console.error('报告自动保存失败', error)
    }
  }, AUTO_SAVE_DEBOUNCE_MS)
}

function toggleAutoSave() {
  autoSaveEnabled.value = !autoSaveEnabled.value
  localStorage.setItem(AUTO_SAVE_STORAGE_KEY, String(autoSaveEnabled.value))
  if (!autoSaveEnabled.value) {
    clearAutoSaveTimer()
    autoSaveSequence += 1
    return
  }
  scheduleAutoSave()
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
  () => props.queryBlocks,
  (blocks) => {
    queryBlockRegistry.clear()
    Object.values(blocks).forEach((block) => queryBlockRegistry.set(block.id, block))
  },
  { deep: true, immediate: true },
)

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
  closeTemplateMenu()
})

defineExpose({
  insertContent,
  insertQueryBlockNode,
  migrateLegacyQueryBlocks,
  replaceQueryBlocks,
  getQueryBlockIds: () => collectQueryBlockIds(umoRef.value?.getJSON?.() || null),
})

const editorOptions = computed(() => ({
  locale: 'zh-CN',
  extensions: [reportQueryBlockExtension, templateMentionExtension],
  // 项目使用 @ 触发 Word 模板菜单，不使用 Umo Editor 自带的“提及用户”菜单。
  disableExtensions: ['mention'],
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
  onChanged: () => {
    if (restoringInitialContent.value) return
    // 长文档的 HTML/JSON 可达数十万字符。若每次按键都把完整内容写入父组件的
    // Vue 响应式状态，会触发大对象代理和依赖更新，明显阻塞输入。正文仅在保存时同步；
    // 普通编辑这里只维护防抖保存。只有文档含数据块时才执行结构扫描。
    if (queryBlockRegistry.size > 0 || Object.keys(props.queryBlocks).length > 0) {
      if (reconcileQueryBlockNodes()) return
      emitQueryBlockIds(umoRef.value?.getJSON?.() || null)
    }
    scheduleAutoSave()
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
  <div ref="shellRef" class="umo-shell">
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

    <label
      v-if="!readOnly"
      class="auto-save-switch"
      :class="{ enabled: autoSaveEnabled }"
      :title="autoSaveEnabled ? '自动保存已开启；关闭后请使用 Ctrl + S 手动保存' : '自动保存已关闭；请使用 Ctrl + S 手动保存'"
    >
      <span>自动保存</span>
      <input type="checkbox" :checked="autoSaveEnabled" @change="toggleAutoSave">
      <i aria-hidden="true"></i>
    </label>

    <div
      v-if="templateMenuVisible"
      class="template-mention-menu"
      :style="{ left: `${templateMenuPosition.left}px`, top: `${templateMenuPosition.top}px` }"
      @mousedown.prevent
    >
      <div class="template-mention-title">
        <strong>插入模板</strong>
        <span v-if="templateMenuQuery">搜索：{{ templateMenuQuery }}</span>
        <span v-else>输入名称可筛选</span>
      </div>
      <div v-if="templateMenuLoading" class="template-mention-empty">正在加载模板...</div>
      <div v-else-if="!filteredTemplateMenuItems.length" class="template-mention-empty">没有可用的 Word 模板</div>
      <button
        v-for="(item, index) in filteredTemplateMenuItems"
        :key="item.id"
        type="button"
        class="template-mention-item"
        :class="{ active: index === templateMenuActiveIndex }"
        :disabled="templateInsertLoadingId !== null"
        @mouseenter="templateMenuActiveIndex = index"
        @click="insertTemplateContent(item)"
      >
        <span class="template-mention-icon">W</span>
        <span class="template-mention-info">
          <strong>{{ item.name }}</strong>
          <small>{{ templateInsertLoadingId === item.id ? '正在加载内容...' : item.original_filename }}</small>
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.umo-shell {
  position: relative;
  height: 100%;
  min-height: 0;
  background: #f5f6f8;
}

.auto-save-switch {
  position: absolute;
  z-index: 30;
  top: 6px;
  right: 202px;
  display: flex;
  align-items: center;
  gap: 7px;
  height: 26px;
  padding: 0 8px;
  border-radius: 6px;
  background: #fff;
  color: #8c8c8c;
  font-size: 12px;
  cursor: pointer;
  user-select: none;
}

.auto-save-switch.enabled { color: #1890ff; }
.auto-save-switch input { position: absolute; opacity: 0; pointer-events: none; }
.auto-save-switch i {
  position: relative;
  width: 28px;
  height: 16px;
  border-radius: 8px;
  background: #bfbfbf;
  transition: background .2s;
}
.auto-save-switch i::after {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, .2);
  transition: transform .2s;
  content: '';
}
.auto-save-switch.enabled i { background: #1890ff; }
.auto-save-switch.enabled i::after { transform: translateX(12px); }

.template-mention-menu {
  position: fixed;
  z-index: 4000;
  width: 320px;
  max-height: 300px;
  overflow: auto;
  padding: 6px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 30px rgba(0, 0, 0, .16);
}

.template-mention-title {
  display: flex;
  justify-content: space-between;
  padding: 7px 9px;
  color: #8c8c8c;
  font-size: 12px;
}

.template-mention-title strong { color: #262626; }
.template-mention-empty { padding: 24px 10px; color: #8c8c8c; text-align: center; }
.template-mention-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  text-align: left;
}
.template-mention-item:hover, .template-mention-item.active { background: #e6f7ff; }
.template-mention-icon {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: 5px;
  background: #1890ff;
  color: #fff;
  font-weight: 700;
}
.template-mention-info { min-width: 0; }
.template-mention-info strong, .template-mention-info small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.template-mention-info small { margin-top: 2px; color: #8c8c8c; }

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
