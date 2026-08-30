/** 原子指标列表文案 ↔ 表格 互转 */

export type AtomicListTableField =
  | 'category_share'
  | 'type_share'
  | 'subtype_share'
  | 'dim_combo'
  | 'hot_communities'
  | 'org_units'
  | 'hot_periods'
  | 'regions'
  | 'yoy_stations'
  | 'warning_text'

export type AtomicListTable = {
  headers: string[]
  rows: string[][]
}

const LIST_TABLE_FIELDS = new Set<string>([
  'category_share',
  'type_share',
  'subtype_share',
  'dim_combo',
  'hot_communities',
  'org_units',
  'hot_periods',
  'regions',
  'yoy_stations',
  'warning_text'
])

export function isAtomicMetricListTableField(field: string): field is AtomicListTableField {
  return LIST_TABLE_FIELDS.has(field)
}

/** 列表类字段且有不少于 2 条可解析项时展示表格切换 */
export function canShowAtomicMetricTableToggle(field: string, text: string): boolean {
  const table = parseAtomicMetricListToTable(field, text)
  return Boolean(table && table.rows.length >= 2)
}

export function canConvertAtomicMetricToTable(field: string, text: string): boolean {
  return canShowAtomicMetricTableToggle(field, text)
}

/**
 * 将多个独立维度拆分表纵向合并（往下追加行；类别/类型/细类同级，不带「维度」列）。
 * 表头：名称 | 数量（及占比等扩展列，按各表并集对齐）
 */
export function mergeAtomicDimShareTables(
  parts: Array<{ field: AtomicListTableField; label?: string; text: string }>
): AtomicListTable | null {
  const parsedParts: AtomicListTable[] = []
  for (const part of parts) {
    const text = String(part.text || '').trim()
    const parsed = parseAtomicMetricListToTable(part.field, text)
    if (!parsed?.headers?.length || !parsed.rows?.length) continue
    parsedParts.push(parsed)
  }
  if (parsedParts.length < 2) return null

  // 扩展列（数量/占比/同比等）取并集，名称列统一为「名称」
  const extraHeaders: string[] = []
  for (const table of parsedParts) {
    for (const header of table.headers.slice(1)) {
      if (!extraHeaders.includes(header)) extraHeaders.push(header)
    }
  }
  const headers = ['名称', ...extraHeaders]
  const rows: string[][] = []
  for (const table of parsedParts) {
    const extraIndex = new Map(table.headers.map((h, i) => [h, i]))
    for (const source of table.rows) {
      const name = String(source[0] ?? '').trim()
      if (!name) continue
      const row = [name]
      for (const header of extraHeaders) {
        const idx = extraIndex.get(header)
        row.push(idx === undefined ? '' : String(source[idx] ?? ''))
      }
      rows.push(row)
    }
  }
  if (!rows.length) return null
  return { headers, rows }
}

/** 将占比/高发社区/同比所等列表文案解析为表头+行；解析失败返回 null */
export function parseAtomicMetricListToTable(
  field: string,
  text: string
): AtomicListTable | null {
  const raw = String(text || '').trim()
  if (!raw || raw === '无') return null
  if (!isAtomicMetricListTableField(field)) return null

  if (field === 'hot_communities' || field === 'org_units') {
    return parseHotCommunities(raw)
  }
  if (field === 'regions') {
    return parseRegions(raw)
  }
  if (field === 'hot_periods') {
    return parseHotPeriods(raw)
  }
  if (field === 'yoy_stations') {
    return parseYoyStations(raw)
  }
  if (field === 'warning_text') {
    return parseWarningText(raw)
  }
  return parseDimShare(field, raw)
}

/** 表格 → 列表文案（用于地区表等已是表格的结果） */
export function formatAtomicMetricTableToText(headers: string[], rows: string[][]): string {
  const cols = headers.map((h) => String(h || '').trim())
  if (!cols.length || !rows.length) return ''
  return rows
    .map((row) =>
      cols
        .map((header, index) => {
          const cell = String(row[index] ?? '').trim()
          return cell ? `${header}${cell}` : ''
        })
        .filter(Boolean)
        .join('，')
    )
    .filter(Boolean)
    .join('；')
}

/**
 * 表格2：左栏与表头互换。
 * 例：社区|数量|占比 × 行(五爱…) → 社区|五爱|… × 行(数量/占比…)
 */
export function transposeAtomicListTable(table: AtomicListTable): AtomicListTable | null {
  const headers = (table.headers || []).map((h) => String(h ?? '').trim())
  const rows = (table.rows || []).map((row) => (row || []).map((cell) => String(cell ?? '').trim()))
  if (!headers.length || !rows.length) return null
  if (headers.length < 2) return null

  const corner = headers[0] || '项目'
  const newHeaders = [corner, ...rows.map((row) => row[0] || '—')]
  const newRows: string[][] = []
  for (let col = 1; col < headers.length; col++) {
    newRows.push([headers[col] || '—', ...rows.map((row) => row[col] ?? '')])
  }
  if (!newRows.length) return null
  return { headers: newHeaders, rows: newRows }
}

/**
 * 解析列表文案为表格；mode=table2 时做左栏/表头互换（名称在头部）
 */
export function parseAtomicMetricListToTableMode(
  field: string,
  text: string,
  mode: 'table' | 'table2' = 'table'
): AtomicListTable | null {
  const parsed = parseAtomicMetricListToTable(field, text)
  if (!parsed || parsed.rows.length < 2) return null
  if (mode === 'table2') return transposeAtomicListTable(parsed)
  return parsed
}

/** 将表格转为可插入编辑器的 HTML */
export function formatAtomicListTableToHtml(table: AtomicListTable): string {
  const headers = (table.headers || []).map((h) => String(h ?? '').trim())
  const rows = (table.rows || []).map((row) => (row || []).map((cell) => String(cell ?? '').trim()))
  if (!headers.length || !rows.length) return ''
  const th = headers
    .map(
      (h) =>
        `<th style="border:1px solid #d9d9d9;padding:6px 8px;background:#f5f7fa;text-align:left;">${escapeHtml(h)}</th>`,
    )
    .join('')
  const body = rows
    .map(
      (row) =>
        `<tr>${headers
          .map((_, i) => `<td style="border:1px solid #d9d9d9;padding:6px 8px;">${escapeHtml(row[i] ?? '')}</td>`)
          .join('')}</tr>`,
    )
    .join('')
  return `<table style="width:100%;border-collapse:collapse;margin:8px 0;"><thead><tr>${th}</tr></thead><tbody>${body}</tbody></table>`
}

function escapeHtml(value: string): string {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function nameHeader(field: AtomicListTableField): string {
  if (field === 'category_share') return '类别'
  if (field === 'type_share') return '类型'
  if (field === 'subtype_share') return '细类'
  if (field === 'dim_combo') return '维度'
  if (field === 'hot_communities') return '社区'
  if (field === 'org_units') return '组织'
  if (field === 'regions') return '辖区'
  if (field === 'hot_periods') return '时段'
  if (field === 'warning_text') return '内容'
  return '单位'
}

/** 按分隔符拆分，忽略括号内的逗号/顿号 */
function splitOutsideParens(text: string, separators: string): string[] {
  const sepSet = new Set(separators.split(''))
  const parts: string[] = []
  let buf = ''
  let depth = 0
  for (const ch of text) {
    if (ch === '（' || ch === '(') {
      depth += 1
      buf += ch
      continue
    }
    if (ch === '）' || ch === ')') {
      depth = Math.max(0, depth - 1)
      buf += ch
      continue
    }
    if (depth === 0 && sepSet.has(ch)) {
      const trimmed = buf.trim()
      if (trimmed) parts.push(trimmed)
      buf = ''
      continue
    }
    buf += ch
  }
  const trimmed = buf.trim()
  if (trimmed) parts.push(trimmed)
  return parts
}

type CountItemExtras = {
  share?: string
  yoy?: string
  mom?: string
  yoyCount?: string
  momCount?: string
}

/** 同比上升91.53% / 环比下降18.71% / 同比持平 → 91.53% / -18.71% / 0% */
function toComparePercent(text: string): string {
  const raw = String(text || '').trim()
  if (!raw || raw === '—') return '—'
  if (/持平/.test(raw)) return '0%'
  const matched = raw.match(/(上升|下降|增加|减少|升高|降低)?\s*([+\-]?\d+(?:\.\d+)?)\s*%/)
  if (!matched) {
    const bare = raw.match(/^([+\-]?\d+(?:\.\d+)?)\s*%?$/)
    return bare ? `${bare[1]}%` : raw
  }
  const direction = matched[1] || ''
  const num = matched[2]
  if (/下降|减少|降低/.test(direction)) {
    return num.startsWith('-') ? `${num}%` : `-${num}%`
  }
  // 上升或无方向词：保留原数字符号
  return `${num}%`
}

function parseDetailExtras(detail: string): CountItemExtras {
  const result: CountItemExtras = {}
  const bits = detail
    .split(/[，,]/)
    .map((item) => item.trim())
    .filter(Boolean)
  for (const bit of bits) {
    const share = bit.match(/^占比\s*([\d.]+)\s*%$/)
    if (share) {
      result.share = `${share[1]}%`
      continue
    }
    const yoyCount = bit.match(/^同比数\s*(\d+)\s*起?$/)
    if (yoyCount) {
      result.yoyCount = yoyCount[1]
      continue
    }
    const momCount = bit.match(/^环比数\s*(\d+)\s*起?$/)
    if (momCount) {
      result.momCount = momCount[1]
      continue
    }
    if (/^同比/.test(bit)) {
      result.yoy = toComparePercent(bit)
      continue
    }
    if (/^环比/.test(bit)) {
      result.mom = toComparePercent(bit)
      continue
    }
  }
  return result
}

function buildCountExtraTable(
  nameCol: string,
  rows: Array<{ name: string; count: string; extras: CountItemExtras }>
): AtomicListTable | null {
  if (!rows.length) return null
  const hasShare = rows.some((row) => Boolean(row.extras.share))
  const hasYoy = rows.some((row) => Boolean(row.extras.yoy))
  const hasMom = rows.some((row) => Boolean(row.extras.mom))
  const hasYoyCount = rows.some((row) => Boolean(row.extras.yoyCount))
  const hasMomCount = rows.some((row) => Boolean(row.extras.momCount))
  const headers = [nameCol, '数量']
  if (hasShare) headers.push('占比')
  if (hasYoy) headers.push('同比')
  if (hasYoyCount) headers.push('同比数')
  if (hasMom) headers.push('环比')
  if (hasMomCount) headers.push('环比数')
  return {
    headers,
    rows: rows.map((row) => {
      const cells = [row.name, row.count]
      if (hasShare) cells.push(row.extras.share || '—')
      if (hasYoy) cells.push(row.extras.yoy || '—')
      if (hasYoyCount) cells.push(row.extras.yoyCount || '—')
      if (hasMom) cells.push(row.extras.mom || '—')
      if (hasMomCount) cells.push(row.extras.momCount || '—')
      return cells
    })
  }
}

function parseDimShare(field: AtomicListTableField, text: string): AtomicListTable | null {
  const parts = splitOutsideParens(text, '、，,；;')
  if (!parts.length) return null

  const rows: Array<{ name: string; count: string; extras: CountItemExtras }> = []
  for (const part of parts) {
    // 盗窃261起 / 盗窃261起（占比29.9%，同比上升12.3%，环比下降1%）
    const matched = part.match(
      /^(.+?)\s*(\d+)\s*起(?:\s*[（(]\s*(.+?)\s*[）)])?\s*$/
    )
    if (!matched) continue
    const name = matched[1].trim()
    if (!name) continue
    rows.push({
      name,
      count: matched[2],
      extras: matched[3] ? parseDetailExtras(matched[3]) : {}
    })
  }
  return buildCountExtraTable(nameHeader(field), rows)
}

function parseHotCommunities(text: string): AtomicListTable | null {
  // 五爱社区：30起，商博社区：10起（占比…，同比…，环比…）
  return parseNamedCountList(text, '社区')
}

function parseRegions(text: string): AtomicListTable | null {
  // 城西：30起，大陈：20起（占比…，同比…，环比…）
  return parseNamedCountList(text, '辖区')
}

function parseNamedCountList(text: string, nameCol: string): AtomicListTable | null {
  const parts = splitOutsideParens(text, '，,；;')
  if (!parts.length) return null
  const rows: Array<{ name: string; count: string; extras: CountItemExtras }> = []
  for (const part of parts) {
    const matched = part.match(
      /^(.+?)[：:]\s*(\d+)\s*起(?:\s*[（(]\s*(.+?)\s*[）)])?\s*$/
    )
    if (!matched) continue
    const name = matched[1].trim()
    if (!name) continue
    rows.push({
      name,
      count: matched[2],
      extras: matched[3] ? parseDetailExtras(matched[3]) : {}
    })
  }
  return buildCountExtraTable(nameCol, rows)
}

function parseHotPeriods(text: string): AtomicListTable | null {
  // 0-1时：12起 / 0-1时：12起（占比10%，同比上升1%）
  const parts = splitOutsideParens(text, '，,；;')
  if (!parts.length) return null
  const rows: Array<{ name: string; count: string; extras: CountItemExtras }> = []
  for (const part of parts) {
    const matched = part.match(
      /^(\d+)\s*-\s*(\d+)\s*时\s*[：:]\s*(\d+)\s*起(?:\s*[（(]\s*(.+?)\s*[）)])?\s*$/,
    )
    if (!matched) continue
    rows.push({
      name: `${matched[1]}-${matched[2]}时`,
      count: matched[3],
      extras: matched[4] ? parseDetailExtras(matched[4]) : {},
    })
  }
  return buildCountExtraTable('时段', rows)
}

function parseYoyStations(text: string): AtomicListTable | null {
  // 列表：大陈12起（14.04%）、盗窃案85起（-0.93%）
  // 兼容旧格式：大陈（14.04%）
  // 分析长文：尽量抽出「名称N起（百分比）」片段
  const rows: string[][] = []
  const withCount =
    /([^、，；;。\s（(][^、，；;。（(]*?)(\d+)起[（(]([+\-]?\d+(?:\.\d+)?%|—)[）)]/g
  const legacy =
    /([^、，；;。\s（(][^、，；;。（(]{0,40}?)[（(]([+\-]?\d+(?:\.\d+)?%|—)[）)]/g
  let matched: RegExpExecArray | null
  while ((matched = withCount.exec(text)) !== null) {
    const name = matched[1].trim().replace(/^(其中|其余|是)/, '').trim()
    if (!name) continue
    rows.push([name, matched[2], matched[3]])
  }
  if (!rows.length) {
    while ((matched = legacy.exec(text)) !== null) {
      const name = matched[1].trim().replace(/^(其中|其余|是)/, '').trim()
      if (!name) continue
      rows.push([name, '', matched[2]])
    }
  }
  if (!rows.length) return null
  // 去重保序
  const seen = new Set<string>()
  const unique = rows.filter(([name, count, pct]) => {
    const key = `${name}|${count}|${pct}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
  const hasCount = unique.some((row) => Boolean(row[1]))
  if (hasCount) {
    return { headers: ['单位', '数量', '同比'], rows: unique }
  }
  return {
    headers: ['单位', '同比'],
    rows: unique.map(([name, _count, pct]) => [name, pct])
  }
}

function parseWarningText(text: string): AtomicListTable | null {
  // 预警多为多句/多条：按句号、分号、换行拆成行
  const parts = text
    .split(/[\n；;。]/)
    .map((item) => item.trim())
    .filter(Boolean)
  if (parts.length < 2) {
    // 单条也允许转表
    if (!text.trim()) return null
    return { headers: ['预警内容'], rows: [[text.trim()]] }
  }
  return {
    headers: ['预警内容'],
    rows: parts.map((item) => [item])
  }
}
