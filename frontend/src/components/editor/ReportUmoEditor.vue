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
    title: '警情智能报告',
    modelValue: '',
    readOnly: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  save: [value: string]
}>()

const editorOptions = computed(() => ({
  locale: 'zh-CN',
  height: '100%',
  document: {
    title: props.title,
    content: props.modelValue,
    placeholder: {
      zh_CN: '请在此编辑警情研判报告...',
      en_US: 'Edit report here...',
    },
    readOnly: props.readOnly,
    autofocus: false,
    enableBubbleMenu: !props.readOnly,
    enableBlockMenu: !props.readOnly,
    autoSave: { enabled: false },
  },
  toolbar: {
    showSaveLabel: !props.readOnly,
    defaultMode: 'classic',
    menus: ['base', 'insert', 'table', 'page', 'view'],
  },
  page: {
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
  min-height: 720px;
  background: #eef1f6;
}
</style>
