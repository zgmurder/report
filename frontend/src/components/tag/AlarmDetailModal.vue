<script setup lang="ts">
import {
  extractPeopleFromAlarmRow,
  parseTagResult,
  type TagAlarmRow
} from '@/api/tag'
import { NModal } from 'naive-ui'
import { computed } from 'vue'

const props = defineProps<{
  show: boolean
  row: TagAlarmRow | null
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const contentFields = computed(() => {
  const row = props.row
  if (!row) return []
  return [
    { label: '处警编号', value: row.cjdbh || '-' },
    { label: '报警时间', value: row.bjsj || '-' },
    { label: '业务时间', value: row.ywsj_dt || '-' },
    { label: '反馈单位', value: row.fkdwmc || '-' },
    { label: '反馈人', value: row.fkrxm || '-' }
  ]
})

const extracted = computed(() => {
  const row = props.row
  const empty = {
    alarmTags: [] as string[],
    dispose: [] as string[],
    times: [] as string[],
    places: [] as string[],
    people: [] as Array<{
      name: string
      idNo: string
      phone: string
      nationality: string
      roles: string[]
      tags: string[]
      identities: string[]
    }>,
    relationsText: '——'
  }
  if (!row) return empty

  const data = parseTagResult(row.result)
  const timePlace = (data['时间地点'] && typeof data['时间地点'] === 'object'
    ? (data['时间地点'] as Record<string, unknown>)
    : {}) as Record<string, unknown>

  const alarmTags: string[] = []
  Object.entries(data).forEach(([key, value]) => {
    if (['时间地点', '人物关系', '人物分析', '处置结果'].includes(key)) return
    toStringList(value).forEach((item) => alarmTags.push(item))
  })

  const people = extractPeopleFromAlarmRow(row).map((person) => ({
    name: pickScalar(person, ['姓名']),
    idNo: pickScalar(person, ['证件号码', '身份证', '证件号']),
    phone: pickScalar(person, ['联系电话', '电话', '手机号']),
    nationality: pickScalar(person, ['国籍']),
    roles: toStringList(person['事件角色'] ?? person['角色']),
    tags: toStringList(person['人物标签'] ?? person['标签']),
    identities: toStringList(person['人物身份'] ?? person['身份'])
  }))

  return {
    alarmTags,
    dispose: toStringList(data['处置结果']),
    times: toStringList(timePlace['发生时间段'] ?? timePlace['时间']),
    places: toStringList(timePlace['发生地址'] ?? timePlace['地点']),
    people,
    relationsText: formatRelations(data['人物关系'])
  }
})

const extractTagFields = computed(() => [
  { label: '警情标签', tags: extracted.value.alarmTags },
  { label: '处置结果', tags: extracted.value.dispose },
  { label: '时间', tags: extracted.value.times },
  { label: '地点', tags: extracted.value.places }
])

const cjqkSections = computed(() => {
  const raw = htmlToPlainText(String(props.row?.cjqk || '')).trim()
  if (!raw) return [] as Array<{ label: string; value: string }>

  const matches = [...raw.matchAll(/【([^】]+)】/g)]
  if (!matches.length) {
    return [{ label: '处警情况', value: raw }]
  }

  const sections: Array<{ label: string; value: string }> = []
  matches.forEach((match, index) => {
    const label = String(match[1] || '').trim()
    const start = (match.index || 0) + match[0].length
    const end = index + 1 < matches.length ? (matches[index + 1].index || raw.length) : raw.length
    const value = raw.slice(start, end).trim()
    if (!label) return
    sections.push({ label, value: value || '—' })
  })

  const firstIndex = matches[0]?.index || 0
  if (firstIndex > 0) {
    const preface = raw.slice(0, firstIndex).trim()
    if (preface) sections.unshift({ label: '摘要', value: preface })
  }
  return sections
})

function toStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item ?? '').trim()).filter(Boolean)
  }
  const text = String(value ?? '').trim()
  return text ? [text] : []
}

function pickScalar(person: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = person[key]
    if (Array.isArray(value)) {
      const text = value.map((item) => String(item ?? '').trim()).filter(Boolean).join('、')
      if (text) return text
    }
    const text = String(value ?? '').trim()
    if (text) return text
  }
  return ''
}

function formatRelations(value: unknown): string {
  if (value == null || value === '') return '——'

  if (typeof value === 'string') {
    const text = value.trim()
    if (!text) return '——'
    if (text.startsWith('{') || text.startsWith('[')) {
      try {
        return formatRelations(JSON.parse(text))
      } catch {
        return text
      }
    }
    return text
  }

  if (Array.isArray(value)) {
    const items = value.map((item) => {
      if (item == null) return ''
      if (typeof item === 'string') return item.trim()
      if (typeof item === 'object') {
        const row = item as Record<string, unknown>
        const relation = String(row['人物关系'] || row['关系'] || row['描述'] || '').trim()
        const name1 = String(row['人物姓名1'] || row['姓名1'] || '').trim()
        const name2 = String(row['人物姓名2'] || row['姓名2'] || '').trim()
        if (relation && name1 && name2) return `${name1} 与 ${name2}：${relation}`
        if (relation) return relation
        return JSON.stringify(item)
      }
      return String(item).trim()
    }).filter(Boolean)
    return items.length ? items.join('；') : '——'
  }

  if (typeof value === 'object') {
    const row = value as Record<string, unknown>
    const relation = String(row['人物关系'] || row['关系'] || row['描述'] || '').trim()
    const name1 = String(row['人物姓名1'] || row['姓名1'] || '').trim()
    const name2 = String(row['人物姓名2'] || row['姓名2'] || '').trim()
    if (relation && name1 && name2) return `${name1} 与 ${name2}：${relation}`
    if (relation) return relation
    return Object.entries(row)
      .map(([key, val]) => `${key}：${String(val ?? '').trim()}`)
      .filter((item) => !item.endsWith('：'))
      .join('；') || '——'
  }

  return String(value)
}

function displayText(value: string | undefined | null) {
  const text = String(value ?? '').trim()
  return text || '—'
}

function isWideCjqkSection(label: string) {
  return /当事人|处警信息|警情内容|处置情况|摘要/.test(label)
}

function htmlToPlainText(input: string): string {
  const raw = String(input || '')
  if (!raw) return ''
  if (!/<[a-z!][\s\S]*>/i.test(raw)) return raw

  const normalized = raw
    .replace(/<\s*br\s*\/?\s*>/gi, '\n')
    .replace(/<\s*hr\s*\/?\s*>/gi, '\n')
    .replace(/<\/\s*(p|div|tr|li|h[1-6]|table|section|article)\s*>/gi, '\n')
    .replace(/<\s*(p|div|tr|li|h[1-6]|table|section|article)(\s[^>]*)?>/gi, '\n')

  try {
    const doc = new DOMParser().parseFromString(normalized, 'text/html')
    return (doc.body.textContent || '')
      .replace(/\u00a0/g, ' ')
      .replace(/[ \t\f\v]+/g, ' ')
      .replace(/ *\n */g, '\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  } catch {
    return normalized.replace(/<[^>]+>/g, ' ').replace(/\s+\n/g, '\n').replace(/[ \t]{2,}/g, ' ').trim()
  }
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    title="警情详情"
    class="!w-[min(1080px,calc(100vw-32px))]"
    :bordered="false"
    :mask-closable="true"
    @update:show="emit('update:show', $event)"
  >
    <div v-if="row" class="grid max-h-[min(72vh,760px)] gap-4 overflow-auto text-sm leading-6 lg:grid-cols-2">
      <!-- 内容详情 -->
      <section class="min-w-0 space-y-2">
        <h3 class="flex h-7 items-center gap-2 font-medium text-slate-700">
          <span class="h-3.5 w-1 shrink-0 rounded-full bg-blue-600" />
          内容详情
        </h3>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div
            v-for="field in contentFields"
            :key="field.label"
            class="overflow-hidden rounded-md border border-slate-200/80"
          >
            <div class="h-7 px-2.5 leading-7 text-slate-500">{{ field.label }}</div>
            <div class="min-h-9 break-all bg-white px-2.5 py-1.5 text-slate-800">{{ field.value }}</div>
          </div>
          <div
            v-for="(section, index) in cjqkSections"
            :key="`${section.label}-${index}`"
            class="overflow-hidden rounded-md border border-slate-200/80"
            :class="isWideCjqkSection(section.label) ? 'sm:col-span-2' : ''"
          >
            <div class="h-7 px-2.5 leading-7 text-slate-500">{{ section.label }}</div>
            <div class="min-h-9 whitespace-pre-wrap break-words bg-white px-2.5 py-1.5 text-slate-800" v-text="section.value" />
          </div>
        </div>
      </section>

      <!-- 提取要素 -->
      <section class="min-w-0 space-y-3">
        <div>
          <h3 class="mb-2 flex h-7 items-center gap-2 font-medium text-slate-700">
            <span class="h-3.5 w-1 shrink-0 rounded-full bg-emerald-500" />
            提取标签
          </h3>
          <div class="grid grid-cols-2 gap-2">
            <div
              v-for="field in extractTagFields"
              :key="field.label"
              class="overflow-hidden rounded-md border border-slate-200/80"
            >
              <div class="h-7 px-2.5 leading-7 text-slate-500">{{ field.label }}</div>
              <div class="flex min-h-9 flex-wrap items-center gap-1 bg-white px-2.5 py-1.5">
                <template v-if="field.tags.length">
                  <span
                    v-for="tag in field.tags"
                    :key="`${field.label}-${tag}`"
                    class="inline-flex h-6 items-center rounded bg-blue-50 px-1.5 text-blue-600"
                  >{{ tag }}</span>
                </template>
                <span v-else class="text-slate-400">—</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="!extracted.people.length" class="rounded-md border border-dashed border-slate-200 px-3 py-6 text-center text-slate-400">
          暂无人物分析要素
        </div>

        <div
          v-for="(person, index) in extracted.people"
          :key="index"
        >
          <h3 class="mb-2 flex h-7 flex-wrap items-center gap-2 font-medium text-slate-700">
            <span class="h-3.5 w-1 shrink-0 rounded-full bg-blue-600" />
            <span>人物{{ index + 1 }}</span>
            <span class="font-normal text-slate-900">{{ displayText(person.name) }}</span>
            <span
              v-for="role in person.roles"
              :key="`role-${index}-${role}`"
              class="inline-flex h-6 items-center rounded bg-blue-50 px-1.5 font-normal text-blue-600"
            >{{ role }}</span>
          </h3>
          <div class="grid grid-cols-2 gap-2">
            <div class="overflow-hidden rounded-md border border-slate-200/80">
              <div class="h-7 px-2.5 leading-7 text-slate-500">国籍</div>
              <div class="min-h-9 break-all bg-white px-2.5 py-1.5">{{ displayText(person.nationality) }}</div>
            </div>
            <div class="overflow-hidden rounded-md border border-slate-200/80">
              <div class="h-7 px-2.5 leading-7 text-slate-500">联系电话</div>
              <div class="min-h-9 break-all bg-white px-2.5 py-1.5">{{ displayText(person.phone) }}</div>
            </div>
            <div class="col-span-2 overflow-hidden rounded-md border border-slate-200/80">
              <div class="h-7 px-2.5 leading-7 text-slate-500">证件号码</div>
              <div class="min-h-9 break-all bg-white px-2.5 py-1.5">{{ displayText(person.idNo) }}</div>
            </div>
            <div class="overflow-hidden rounded-md border border-slate-200/80">
              <div class="h-7 px-2.5 leading-7 text-slate-500">标签</div>
              <div class="flex min-h-9 flex-wrap items-center gap-1 bg-white px-2.5 py-1.5">
                <span
                  v-for="tag in person.tags"
                  :key="`ptag-${index}-${tag}`"
                  class="inline-flex h-6 items-center rounded bg-blue-50 px-1.5 text-blue-600"
                >{{ tag }}</span>
                <span v-if="!person.tags.length" class="text-slate-400">—</span>
              </div>
            </div>
            <div class="overflow-hidden rounded-md border border-slate-200/80">
              <div class="h-7 px-2.5 leading-7 text-slate-500">身份</div>
              <div class="flex min-h-9 flex-wrap items-center gap-1 bg-white px-2.5 py-1.5">
                <span
                  v-for="tag in person.identities"
                  :key="`id-${index}-${tag}`"
                  class="inline-flex h-6 items-center rounded bg-blue-50 px-1.5 text-blue-600"
                >{{ tag }}</span>
                <span v-if="!person.identities.length" class="text-slate-400">—</span>
              </div>
            </div>
          </div>
        </div>

        <div>
          <h3 class="mb-2 flex h-7 items-center gap-2 font-medium text-slate-700">
            <span class="h-3.5 w-1 shrink-0 rounded-full bg-amber-500" />
            人物关系
          </h3>
          <div class="overflow-hidden rounded-md border border-slate-200/80">
            <div class="h-7 px-2.5 leading-7 text-slate-500">关系</div>
            <div class="min-h-9 break-all bg-white px-2.5 py-1.5 text-slate-800">{{ extracted.relationsText }}</div>
          </div>
        </div>
      </section>
    </div>
  </NModal>
</template>
