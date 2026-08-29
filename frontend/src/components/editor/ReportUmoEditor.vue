<script setup lang="ts">
import { computed } from 'vue'
import { UmoEditor } from '@umoteam/editor'
import '@umoteam/editor/style'

const props = withDefaults(
  defineProps<{
    title?: string
    modelValue?: string
    readOnly?: boolean
  }>(),
  {
    title: '未命名报告',
    modelValue: '',
    readOnly: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  save: [value: string]
}>()

function escapeHtml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

const editorOptions = computed(() => ({
  locale: 'zh-CN',
  height: '100%',
  document: {
    title: props.title,
    content: props.modelValue || `<h1 style="text-align:center;">${escapeHtml(props.title)}</h1><p></p>`,
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
      interval: 30,
    },
  },
  toolbar: {
    showSaveLabel: !props.readOnly,
    defaultMode: 'classic',
    menus: ['base', 'insert', 'table', 'tools', 'page', 'export'],
  },
  page: {
    defaultMargin: {
      left: 2.54,
      right: 2.54,
      top: 2.54,
      bottom: 2.54,
    },
    layouts: ['page', 'web'],
    showToc: false,
    showBreakMarks: false,
  },
  onChanged: (editor: unknown) => {
    const api = editor as { getHTML?: () => string }
    const html = api.getHTML?.()
    if (typeof html === 'string') emit('update:modelValue', html)
  },
  onSave: async (editor: unknown) => {
    const api = editor as { getHTML?: () => string }
    emit('save', api.getHTML?.() || props.modelValue)
    return true
  },
}))
</script>

<template>
  <div class="umo-shell">
    <UmoEditor v-bind="editorOptions" />
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
</style>
