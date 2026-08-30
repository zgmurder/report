<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import type { DataTableColumns, FormInst, UploadFileInfo } from 'naive-ui'
import {
  NButton,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NSpace,
  NTag,
  NUpload,
  useDialog,
  useMessage,
} from 'naive-ui'
import { ArrowLeft, Download, FileText, Pencil, Plus, Trash2, Upload } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { downloadTemplate, type ReportTemplateItem } from '@/api/catalog'
import { useCatalogStore } from '@/stores/catalog'

const store = useCatalogStore()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const submitting = ref(false)
const keyword = ref('')
const modalVisible = ref(false)
const modalMode = ref<'create' | 'edit' | 'upload'>('upload')
const editingId = ref<number | null>(null)
const selectedFile = ref<File | null>(null)
const fileList = ref<UploadFileInfo[]>([])
const formRef = ref<FormInst | null>(null)

const statusOptions = [
  { label: '启用', value: 'enabled' },
  { label: '停用', value: 'disabled' },
]
const form = reactive({ name: '', description: '', status: 'enabled' })
const rules = {
  name: { required: true, message: '请输入模板名称', trigger: ['input', 'blur'] },
}

const filteredTemplates = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return store.templates.filter((item) => (
    !text || item.name.toLowerCase().includes(text) || item.description.toLowerCase().includes(text)
  ))
})

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/home/reports')
}

function formatSize(size?: number | null) {
  if (!size) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(value: string) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-'
}

function renderAction(icon: typeof Pencil, text: string, onClick: () => void, type: 'primary' | 'error' | 'default' = 'default', disabled = false) {
  return h(NButton, { text: true, type, disabled, onClick }, { icon: () => h(icon, { size: 15 }), default: () => text })
}

const columns: DataTableColumns<ReportTemplateItem> = [
  {
    title: '模板名称',
    key: 'name',
    minWidth: 220,
    render: (row) => h('div', { class: 'name-cell' }, [
      h('div', { class: 'name-main' }, [
        h('div', { class: 'word-icon' }, [h(FileText, { size: 20 })]),
        h('strong', row.name),
      ]),
      h('small', row.original_filename || '未上传 Word 文件'),
    ]),
  },
  { title: '说明', key: 'description', minWidth: 220, ellipsis: { tooltip: true }, render: (row) => row.description || '-' },
  { title: '大小', key: 'file_size', width: 100, render: (row) => formatSize(row.file_size) },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row) => h(NTag, { type: row.status === 'enabled' ? 'success' : 'default', size: 'small', bordered: false }, { default: () => row.status === 'enabled' ? '启用' : '停用' }),
  },
  { title: '更新时间', key: 'updated_at', width: 180, render: (row) => formatDate(row.updated_at) },
  {
    title: '操作',
    key: 'actions',
    width: 230,
    fixed: 'right',
    render: (row) => h(NSpace, { size: 14 }, {
      default: () => [
        renderAction(Download, '下载', () => handleDownload(row), 'primary', !row.original_filename),
        renderAction(Pencil, '编辑', () => openEdit(row)),
        renderAction(Trash2, '删除', () => confirmDelete(row), 'error'),
      ],
    }),
  },
]

async function load() {
  loading.value = true
  try {
    await store.loadTemplates()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '模板列表加载失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editingId.value = null
  selectedFile.value = null
  fileList.value = []
  Object.assign(form, { name: '', description: '', status: 'enabled' })
}

function openUpload() {
  resetForm()
  modalMode.value = 'upload'
  modalVisible.value = true
}

function openCreate() {
  resetForm()
  modalMode.value = 'create'
  modalVisible.value = true
}

function openEdit(row: ReportTemplateItem) {
  resetForm()
  modalMode.value = 'edit'
  editingId.value = row.id
  Object.assign(form, { name: row.name, description: row.description, status: row.status })
  modalVisible.value = true
}

function handleFileChange(options: { file: UploadFileInfo; fileList: UploadFileInfo[] }) {
  fileList.value = options.fileList.slice(-1)
  selectedFile.value = options.file.file || null
  if (!form.name && selectedFile.value) form.name = selectedFile.value.name.replace(/\.docx?$/i, '')
}

async function submit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  if (modalMode.value === 'upload' && !selectedFile.value) {
    message.warning('请选择 Word 文件')
    return
  }
  submitting.value = true
  try {
    if (modalMode.value === 'upload') {
      await store.uploadTemplate(selectedFile.value!, form)
      message.success('Word 模板上传成功')
    } else {
      await store.saveTemplate({ ...form, content_json: modalMode.value === 'create' ? {} : undefined }, editingId.value || undefined)
      message.success(modalMode.value === 'edit' ? '模板更新成功' : '模板创建成功')
    }
    modalVisible.value = false
  } catch (error) {
    message.error(error instanceof Error ? error.message : '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDownload(row: ReportTemplateItem) {
  try {
    await downloadTemplate(row.id, row.original_filename || `${row.name}.docx`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '下载失败')
  }
}

function confirmDelete(row: ReportTemplateItem) {
  dialog.warning({
    title: '删除模板',
    content: `确定删除“${row.name}”吗？关联的 Word 文件也会一并删除。`,
    positiveText: '删除',
    negativeText: '取消',
    async onPositiveClick() {
      try {
        await store.removeTemplate(row.id)
        message.success('模板已删除')
      } catch (error) {
        message.error(error instanceof Error ? error.message : '删除失败')
        return false
      }
    },
  })
}

onMounted(load)
</script>

<template>
  <section class="glass-card content-card">
    <div class="section-toolbar">
      <div class="title-area">
        <n-button quaternary circle aria-label="返回" title="返回" @click="goBack">
          <template #icon><ArrowLeft :size="20" /></template>
        </n-button>
        <div>
          <h2>模板库</h2>
          <p class="muted">上传和维护自己的 Word 报告模板；编辑器中只能选择当前账号的模板</p>
        </div>
      </div>
      <n-space>
        <n-button @click="openCreate"><template #icon><Plus :size="16" /></template>新建记录</n-button>
        <n-button type="primary" @click="openUpload"><template #icon><Upload :size="16" /></template>上传 Word</n-button>
      </n-space>
    </div>

    <div class="filters">
      <n-input v-model:value="keyword" clearable placeholder="搜索模板名称或说明" />
    </div>

    <n-data-table
      :columns="columns"
      :data="filteredTemplates"
      :loading="loading"
      :row-key="(row: ReportTemplateItem) => row.id"
      :scroll-x="1040"
      :pagination="{ pageSize: 10 }"
      striped
    />

    <n-modal v-model:show="modalVisible" :mask-closable="!submitting" transform-origin="center">
      <div class="modal-card">
        <h3>{{ modalMode === 'upload' ? '上传 Word 模板' : modalMode === 'edit' ? '编辑模板' : '新建模板记录' }}</h3>
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-form-item v-if="modalMode === 'upload'" label="Word 文件" required>
            <n-upload
              accept=".doc,.docx"
              :default-upload="false"
              :max="1"
              :file-list="fileList"
              @change="handleFileChange"
            >
              <n-button><template #icon><Upload :size="16" /></template>选择文件</n-button>
            </n-upload>
            <span class="upload-hint">支持 .doc、.docx，单个文件不超过 20MB</span>
          </n-form-item>
          <n-form-item label="模板名称" path="name"><n-input v-model:value="form.name" maxlength="200" show-count /></n-form-item>
          <n-form-item label="模板说明"><n-input v-model:value="form.description" type="textarea" maxlength="500" show-count :autosize="{ minRows: 3, maxRows: 6 }" /></n-form-item>
          <n-form-item label="状态"><n-select v-model:value="form.status" :options="statusOptions" /></n-form-item>
        </n-form>
        <n-space justify="end">
          <n-button :disabled="submitting" @click="modalVisible = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="submit">保存</n-button>
        </n-space>
      </div>
    </n-modal>
  </section>
</template>

<style scoped>
.content-card { min-height: 100%; padding: 22px; }
.section-toolbar { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 18px; }
.title-area { display: flex; align-items: flex-start; gap: 8px; }
h2 { margin: 0 0 4px; font-size: 20px; }
p { margin: 0; }
.filters { width: min(360px, 100%); margin-bottom: 16px; }
.name-cell { display: flex; min-width: 0; flex-direction: column; gap: 4px; }
.name-main { display: flex; min-width: 0; align-items: center; gap: 8px; }
.name-main strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.name-cell small { display: block; overflow: hidden; color: #8c8c8c; font-weight: 400; text-overflow: ellipsis; white-space: nowrap; }
.word-icon { display: grid; place-items: center; width: 28px; height: 28px; flex: none; color: #1890ff; background: #e6f7ff; border-radius: 5px; }
.modal-card { width: min(560px, calc(100vw - 32px)); padding: 22px; background: #fff; border-radius: 8px; }
.modal-card h3 { margin: 0 0 18px; font-size: 18px; }
.upload-hint { display: block; margin-top: 8px; color: #8c8c8c; font-size: 12px; }
@media (max-width: 700px) {
  .section-toolbar { flex-direction: column; }
  .filters { grid-template-columns: 1fr; }
}
</style>
