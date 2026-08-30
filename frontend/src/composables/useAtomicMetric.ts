import { computed, isRef, ref, unref, type MaybeRef, type Ref } from 'vue'
import {
  queryAtomicMetric as requestAtomicMetric,
  type AtomicMetricQueryPayload,
  type AtomicMetricQueryResult,
} from '@/api/atomicMetric'
import { applyAtomicTypeLabels } from '@/data/atomicTypeDict'
import {
  canShowAtomicMetricTableToggle,
  formatAtomicListTableToHtml,
  mergeAtomicDimShareTables,
  parseAtomicMetricListToTableMode,
  transposeAtomicListTable,
} from '@/utils/atomicMetricTextTable'

export const REPORT_METRIC_VALUE_MIME = 'application/vnd.yw-report-metric-value'
export const REPORT_METRIC_TREND_MIME = 'application/vnd.yw-report-metric-trend'
export const REPORT_METRIC_HTML_MIME = 'application/vnd.yw-report-metric-html'

export type AtomicChipViewMode = 'text' | 'table' | 'table2'

export type AtomicMetricChipField =
  | 'total'
  | 'yoy'
  | 'mom'
  | 'yoy_change'
  | 'mom_change'
  | 'yoy_count_change'
  | 'mom_count_change'
  | 'yoy_count'
  | 'mom_count'
  | 'cumulative'
  | 'share'
  | 'category_share'
  | 'type_share'
  | 'subtype_share'
  | 'dim_combo'
  | 'hot_communities'
  | 'org_units'
  | 'hot_periods'
  | 'regions'
  | 'yoy_stations'
  | 'yoy_trend_top_n'
  | 'warning_text'

export type AtomicMetricChip = {
  field: AtomicMetricChipField
  label: string
  value: string | number
  displayValue: string
  /** 原始列表文案（表格模式拖入时仍保留） */
  textValue?: string
  canTable?: boolean
  viewMode?: AtomicChipViewMode
  tableHeaders?: string[]
  tableRows?: string[][]
  /** 拖入正文的内容（文案或表格 HTML） */
  dragPayload?: string
  dragIsHtml?: boolean
}

export type AtomicCompareFlags = {
  yoy: boolean
  mom: boolean
  share: boolean
  momCount: boolean
  yoyCount: boolean
  cumulative: boolean
  categoryShare: boolean
  typeShare: boolean
  subtypeShare: boolean
  hotCommunity: boolean
  region: boolean
  hotPeriod: boolean
  duplicate: boolean
  excludeNonPolice: boolean
  selfReceived: boolean
  excludeSelfReceived: boolean
  excludeTraffic: boolean
}

export type AtomicOrgDimension = '' | 'pianqu' | 'gongjianwei' | 'jingwuqu'
export type AtomicYoyTrend = '' | 'up' | 'down' | 'analysis'
export type AtomicRankSortBy = 'count' | 'yoy' | 'mom' | 'share'
export type AtomicRankSortOrder = 'asc' | 'desc'
export type AtomicCountThresholdOp = 'gt' | 'lt'

export type UseAtomicMetricOptions = {
  /** [startMs, endMs] 或外部 ref */
  dateRange?: MaybeRef<[number, number] | null>
  source?: MaybeRef<'jjd_jjd' | 'fkd_fkd'>
  deptCode?: MaybeRef<string>
  deptName?: MaybeRef<string>
}

const HOT_PERIOD_HOURS = 2

const DEFAULT_FLAGS: AtomicCompareFlags = {
  yoy: false,
  mom: false,
  share: false,
  momCount: false,
  yoyCount: false,
  cumulative: false,
  categoryShare: false,
  typeShare: false,
  subtypeShare: false,
  hotCommunity: false,
  region: false,
  hotPeriod: false,
  duplicate: false,
  excludeNonPolice: false,
  selfReceived: false,
  excludeSelfReceived: false,
  excludeTraffic: false,
}

function toLocalDateTime(ms: number) {
  const d = new Date(ms)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function joinCodes(codes: string[]) {
  return codes.map((c) => String(c || '').trim()).filter(Boolean).join(',')
}

function isAbortError(error: unknown) {
  if (!error) return false
  if (error instanceof DOMException && error.name === 'AbortError') return true
  if (error instanceof Error) {
    return error.name === 'AbortError' || /aborted|abort|取消/i.test(error.message || '')
  }
  return false
}

function formatCountChangePhrase(current: unknown, baseline: unknown): string {
  const cur = Number(current)
  const base = Number(baseline)
  if (!Number.isFinite(cur) || !Number.isFinite(base)) return ''
  const delta = Math.round(cur - base)
  if (delta >= 0) return `上升 ${delta} 起`
  return `下降 ${Math.abs(delta)} 起`
}

function formatDisplay(field: AtomicMetricChipField, value: unknown) {
  const text = value === undefined || value === null ? '' : String(value)
  if (
    field === 'yoy_stations' ||
    field === 'category_share' ||
    field === 'type_share' ||
    field === 'subtype_share' ||
    field === 'dim_combo' ||
    field === 'hot_communities' ||
    field === 'org_units' ||
    field === 'hot_periods' ||
    field === 'regions' ||
    field === 'warning_text'
  ) {
    if (field === 'type_share') return applyAtomicTypeLabels(text) || '无'
    return text || '无'
  }
  if (field === 'yoy_count_change' || field === 'mom_count_change') {
    return text || '上升 0 起'
  }
  if (field === 'yoy_change' || field === 'mom_change') {
    return text || '持平'
  }
  if (field === 'yoy_trend_top_n') return text || '0'
  if (field === 'yoy' || field === 'mom' || field === 'share') return text ? `${text}%` : '0%'
  return text || '0'
}

function looksLikeTrend(text: string) {
  const raw = String(text || '').trim()
  return /^持平$/.test(raw) || /^(上升|下降|增加|减少|升高|降低)\s*-?\d/.test(raw)
}

export function useAtomicMetric(options: UseAtomicMetricOptions = {}) {
  const dateRange: Ref<[number, number] | null> = isRef(options.dateRange)
    ? (options.dateRange as Ref<[number, number] | null>)
    : ref(options.dateRange ?? null)
  const source: Ref<'jjd_jjd' | 'fkd_fkd'> = isRef(options.source)
    ? (options.source as Ref<'jjd_jjd' | 'fkd_fkd'>)
    : ref(options.source ?? 'jjd_jjd')
  const deptCode: Ref<string> = isRef(options.deptCode)
    ? (options.deptCode as Ref<string>)
    : ref(options.deptCode ?? '')
  const deptName: Ref<string> = isRef(options.deptName)
    ? (options.deptName as Ref<string>)
    : ref(options.deptName ?? '')

  const flags = ref<AtomicCompareFlags>({ ...DEFAULT_FLAGS })
  const categoryCodes = ref<string[]>([])
  const typeCodes = ref<string[]>([])
  const subtypeCodes = ref<string[]>([])
  const categoryNames = ref<string[]>([])
  const typeNames = ref<string[]>([])
  const subtypeNames = ref<string[]>([])

  const showOrgDimension = ref(false)
  const orgDimension = ref<AtomicOrgDimension>('')
  /** 标签：暂 stub，不请求标签包 */
  const showTag = ref(false)
  const tagPackageId = ref<number | null>(null)
  const showAnalysis = ref(false)
  const yoyTrend = ref<AtomicYoyTrend>('')
  const showRank = ref(false)
  const topN = ref<number | null>(null)
  const rankSortBy = ref<AtomicRankSortBy>('count')
  const rankSortOrder = ref<AtomicRankSortOrder>('desc')
  const showThreshold = ref(false)
  const countThresholdOp = ref<AtomicCountThresholdOp>('gt')
  const countThresholdValue = ref<number | null>(null)
  /** 预警：暂 stub */
  const showWarning = ref(false)
  const warningRuleType = ref('')

  const queryResult = ref<AtomicMetricQueryResult | null>(null)
  const querying = ref(false)
  const lastError = ref('')
  /** 多条文案芯片：文案 / 名称在左 / 名称在头 */
  const chipViewModes = ref<Record<string, AtomicChipViewMode>>({})
  let abortController: AbortController | null = null

  const orgDimensionOptions = [
    { label: '片区', value: 'pianqu' },
    { label: '共建委', value: 'gongjianwei' },
    { label: '警务区', value: 'jingwuqu' },
  ] as const

  const yoyTrendOptions = [
    { label: '升幅', value: 'up' },
    { label: '降幅', value: 'down' },
    { label: '自动', value: 'analysis' },
  ] as const

  const rankSortByOptions = [
    { label: '数量', value: 'count' },
    { label: '同比', value: 'yoy' },
    { label: '环比', value: 'mom' },
    { label: '占比', value: 'share' },
  ] as const

  const rankSortOrderOptions = [
    { label: '降序', value: 'desc' },
    { label: '升序', value: 'asc' },
  ] as const

  const countThresholdOpOptions = [
    { label: '大于', value: 'gt' },
    { label: '小于', value: 'lt' },
  ] as const

  function resolveShareIntent() {
    return {
      category: Boolean(flags.value.categoryShare || categoryCodes.value.length > 0),
      type: Boolean(flags.value.typeShare || typeCodes.value.length > 0),
      subtype: Boolean(flags.value.subtypeShare || subtypeCodes.value.length > 0),
    }
  }

  function setFlag<K extends keyof AtomicCompareFlags>(key: K, checked: boolean) {
    const next = { ...flags.value }
    const shareLevel = key === 'categoryShare' || key === 'typeShare' || key === 'subtypeShare'
    const geoExclusive = key === 'hotCommunity' || key === 'hotPeriod' || key === 'region'

    if (showAnalysis.value && (key === 'yoy' || key === 'mom' || key === 'share')) {
      if (checked) {
        next.yoy = key === 'yoy'
        next.mom = key === 'mom'
        next.share = key === 'share'
        if (key === 'share') next.hotPeriod = false
      } else {
        next.yoy = true
        next.mom = false
        next.share = false
      }
    } else if (key === 'share') {
      next.share = checked
      if (checked) next.hotPeriod = false
    } else if (shareLevel && checked) {
      showOrgDimension.value = false
      orgDimension.value = ''
      next[key] = true as AtomicCompareFlags[K]
      next.hotCommunity = false
      next.hotPeriod = false
      next.region = false
    } else if (geoExclusive && checked) {
      showOrgDimension.value = false
      orgDimension.value = ''
      next.categoryShare = false
      next.typeShare = false
      next.subtypeShare = false
      next.hotCommunity = key === 'hotCommunity'
      next.hotPeriod = key === 'hotPeriod'
      next.region = key === 'region'
      if (key === 'hotPeriod') next.share = false
    } else if (key === 'selfReceived' && checked) {
      next.selfReceived = true
      next.excludeSelfReceived = false
    } else if (key === 'excludeSelfReceived' && checked) {
      next.excludeSelfReceived = true
      next.selfReceived = false
    } else {
      next[key] = checked as AtomicCompareFlags[K]
    }

    flags.value = next
    queryResult.value = null
  }

  function setShowOrgDimension(checked: boolean) {
    showOrgDimension.value = checked
    if (checked) {
      orgDimension.value = orgDimension.value || 'pianqu'
      flags.value = {
        ...flags.value,
        categoryShare: false,
        typeShare: false,
        subtypeShare: false,
        hotCommunity: false,
        hotPeriod: false,
        region: false,
      }
    } else {
      orgDimension.value = ''
    }
    queryResult.value = null
  }

  function setShowAnalysis(checked: boolean) {
    showAnalysis.value = checked
    if (checked) {
      yoyTrend.value = yoyTrend.value || 'up'
      if (!flags.value.yoy && !flags.value.mom && !flags.value.share) {
        flags.value = { ...flags.value, yoy: true, mom: false, share: false }
      }
      if (
        !flags.value.categoryShare &&
        !flags.value.typeShare &&
        !flags.value.subtypeShare &&
        !flags.value.hotCommunity &&
        !flags.value.region &&
        !(showOrgDimension.value && orgDimension.value)
      ) {
        flags.value = { ...flags.value, region: true }
      }
    } else {
      yoyTrend.value = ''
    }
    queryResult.value = null
  }

  function setShowRank(checked: boolean) {
    showRank.value = checked
    if (!checked) topN.value = null
    queryResult.value = null
  }

  function setShowThreshold(checked: boolean) {
    showThreshold.value = checked
    if (!checked) countThresholdValue.value = null
    queryResult.value = null
  }

  function setShowTag(checked: boolean) {
    showTag.value = checked
    if (!checked) tagPackageId.value = null
    queryResult.value = null
  }

  function setShowWarning(checked: boolean) {
    showWarning.value = checked
    if (!checked) warningRuleType.value = ''
    queryResult.value = null
  }

  function buildPayload(): AtomicMetricQueryPayload {
    const range = unref(dateRange)
    const shareIntent = resolveShareIntent()
    const trendCompare = flags.value.yoy
      ? 'yoy'
      : flags.value.mom
        ? 'mom'
        : flags.value.share
          ? 'share'
          : 'yoy'

    return {
      data_source: unref(source),
      dept_code: unref(deptCode) || null,
      date_start: range ? toLocalDateTime(range[0]) : null,
      date_end: range ? toLocalDateTime(range[1]) : null,
      category_code: joinCodes(categoryCodes.value) || null,
      category_name: joinCodes(categoryNames.value) || null,
      type_code: joinCodes(typeCodes.value) || null,
      subtype_code: joinCodes(subtypeCodes.value) || null,
      include_yoy: flags.value.yoy,
      include_mom: flags.value.mom,
      include_share: flags.value.share,
      include_mom_count: flags.value.momCount,
      include_yoy_count: flags.value.yoyCount,
      include_cumulative: flags.value.cumulative,
      include_dim_combo: false,
      include_category_share: shareIntent.category,
      include_type_share: shareIntent.type,
      include_subtype_share: shareIntent.subtype,
      include_hot_community: flags.value.hotCommunity,
      org_dimension: showOrgDimension.value && orgDimension.value ? orgDimension.value : null,
      include_hot_period: flags.value.hotPeriod,
      hot_period_hours: flags.value.hotPeriod ? HOT_PERIOD_HOURS : null,
      include_region_table: Boolean(flags.value.region && !showAnalysis.value),
      filter_duplicate: flags.value.duplicate,
      exclude_non_police: flags.value.excludeNonPolice,
      exclude_traffic: flags.value.excludeTraffic,
      filter_self_received: flags.value.selfReceived,
      exclude_self_received: flags.value.excludeSelfReceived,
      // tag / warning stubs：勾选但不强制发有效 id
      tag_package_id: showTag.value ? tagPackageId.value : null,
      yoy_trend: showAnalysis.value
        ? yoyTrend.value === 'down'
          ? 'down'
          : yoyTrend.value === 'analysis'
            ? 'analysis'
            : 'up'
        : null,
      trend_compare: showAnalysis.value ? trendCompare : null,
      yoy_trend_top_n: showRank.value ? topN.value : null,
      rank_sort_by: showRank.value ? rankSortBy.value : null,
      rank_sort_order: showRank.value ? rankSortOrder.value : null,
      count_threshold_op:
        showThreshold.value && countThresholdValue.value != null ? countThresholdOp.value : null,
      count_threshold_value:
        showThreshold.value && countThresholdValue.value != null ? countThresholdValue.value : null,
      include_warning: Boolean(showWarning.value && warningRuleType.value),
      warning_rule_type: showWarning.value ? warningRuleType.value || null : null,
    }
  }

  function countThresholdLabelSuffix() {
    if (!showThreshold.value || countThresholdValue.value == null) return ''
    const op = countThresholdOp.value === 'lt' ? '小于' : '大于'
    return `·${op}${countThresholdValue.value}`
  }

  const atomicMetricChips = computed<AtomicMetricChip[]>(() => {
    const result = queryResult.value
    if (!result) return []
    const fields = result.field_values || {}
    const shareIntent = resolveShareIntent()
    // 勾选拆分维度时，汇总芯片由维度结果承载，不再单独展示总量/同比/环比等
    const hasSplitDimension = Boolean(
      shareIntent.category ||
        shareIntent.type ||
        shareIntent.subtype ||
        flags.value.hotCommunity ||
        flags.value.region ||
        flags.value.hotPeriod ||
        (showOrgDimension.value && orgDimension.value) ||
        showTag.value ||
        showAnalysis.value,
    )

    const chips: AtomicMetricChip[] = []

    if (!hasSplitDimension) {
      const totalLabelParts: string[] = []
      if (fields.exclude_non_police) totalLabelParts.push('除去非警务')
      if (fields.exclude_traffic) totalLabelParts.push('除交通')
      if (fields.filter_self_received) totalLabelParts.push('自接警')
      if (fields.exclude_self_received) totalLabelParts.push('除自接警')
      if (fields.filter_duplicate) totalLabelParts.push('重复')

      chips.push({
        field: 'total',
        label: totalLabelParts.length ? `${totalLabelParts.join('')}总量` : '总量',
        value: (fields.total ?? result.total ?? 0) as string | number,
        displayValue: formatDisplay('total', fields.total ?? result.total ?? 0),
      })

      if (flags.value.yoy) {
        chips.push({
          field: 'yoy',
          label: '同比',
          value: (fields.yoy ?? result.yoy ?? 0) as string | number,
          displayValue: formatDisplay('yoy', fields.yoy ?? result.yoy ?? 0),
        })
        const yoyChange = String(fields.yoy_change ?? result.yoy_change ?? '').trim()
        chips.push({
          field: 'yoy_change',
          label: '同比升降',
          value: yoyChange || '持平',
          displayValue: formatDisplay('yoy_change', yoyChange || '持平'),
        })
        const yoyCountChange =
          formatCountChangePhrase(
            fields.total ?? result.total,
            fields.yoy_count ?? result.yoy_count,
          ) ||
          String(fields.yoy_count_change ?? result.yoy_count_change ?? '')
            .trim()
            .replace(/^持平$/, '') ||
          '上升 0 起'
        chips.push({
          field: 'yoy_count_change',
          label: '同比升降数',
          value: yoyCountChange,
          displayValue: formatDisplay('yoy_count_change', yoyCountChange),
        })
      }
      if (flags.value.mom) {
        chips.push({
          field: 'mom',
          label: '环比',
          value: (fields.mom ?? result.mom ?? 0) as string | number,
          displayValue: formatDisplay('mom', fields.mom ?? result.mom ?? 0),
        })
        const momChange = String(fields.mom_change ?? result.mom_change ?? '').trim()
        chips.push({
          field: 'mom_change',
          label: '环比升降',
          value: momChange || '持平',
          displayValue: formatDisplay('mom_change', momChange || '持平'),
        })
        const momCountChange =
          formatCountChangePhrase(
            fields.total ?? result.total,
            fields.mom_count ?? result.mom_count,
          ) ||
          String(fields.mom_count_change ?? result.mom_count_change ?? '')
            .trim()
            .replace(/^持平$/, '') ||
          '上升 0 起'
        chips.push({
          field: 'mom_count_change',
          label: '环比升降数',
          value: momCountChange,
          displayValue: formatDisplay('mom_count_change', momCountChange),
        })
      }
      if (flags.value.yoyCount) {
        chips.push({
          field: 'yoy_count',
          label: '同比数',
          value: (fields.yoy_count ?? result.yoy_count ?? 0) as string | number,
          displayValue: formatDisplay('yoy_count', fields.yoy_count ?? result.yoy_count ?? 0),
        })
      }
      if (flags.value.momCount) {
        chips.push({
          field: 'mom_count',
          label: '环比数',
          value: (fields.mom_count ?? result.mom_count ?? 0) as string | number,
          displayValue: formatDisplay('mom_count', fields.mom_count ?? result.mom_count ?? 0),
        })
      }
      if (flags.value.cumulative) {
        chips.push({
          field: 'cumulative',
          label: '累计',
          value: (fields.cumulative ?? result.cumulative ?? 0) as string | number,
          displayValue: formatDisplay('cumulative', fields.cumulative ?? result.cumulative ?? 0),
        })
      }

      if (flags.value.share) {
        const shareRaw = fields.share ?? result.share
        if (shareRaw !== undefined && shareRaw !== null && shareRaw !== '') {
          chips.push({
            field: 'share',
            label: fields.filter_duplicate ? '重复占比' : '占比',
            value: shareRaw as string | number,
            displayValue: formatDisplay('share', shareRaw),
          })
        }
      }
    }

    const dimShareLabelPrefix = [
      flags.value.share ? '占比' : '',
      flags.value.momCount ? '环比数' : '',
      flags.value.yoyCount ? '同比数' : '',
      flags.value.yoy ? '同比' : '',
      flags.value.mom ? '环比' : '',
    ]
      .filter(Boolean)
      .join('·')

    const categoryShare = shareIntent.category
      ? String(fields.category_share ?? result.category_share ?? '').trim()
      : ''
    const typeShareRaw = shareIntent.type
      ? String(fields.type_share ?? result.type_share ?? '').trim()
      : ''
    const typeShare = typeShareRaw ? applyAtomicTypeLabels(typeShareRaw) || typeShareRaw : ''
    const subtypeShare = shareIntent.subtype
      ? String(fields.subtype_share ?? result.subtype_share ?? '').trim()
      : ''

    const dimShareParts: Array<{
      field: 'category_share' | 'type_share' | 'subtype_share'
      label: string
      text: string
    }> = []
    if (shareIntent.category && !showAnalysis.value && categoryShare && categoryShare !== '无') {
      dimShareParts.push({ field: 'category_share', label: '类别', text: categoryShare })
    }
    if (shareIntent.type && !showAnalysis.value && typeShare && typeShare !== '无') {
      dimShareParts.push({ field: 'type_share', label: '类型', text: typeShare })
    }
    if (shareIntent.subtype && !showAnalysis.value && subtypeShare && subtypeShare !== '无') {
      dimShareParts.push({ field: 'subtype_share', label: '细类', text: subtypeShare })
    }

    const mergedDimTable =
      dimShareParts.length >= 2
        ? mergeAtomicDimShareTables(
            dimShareParts.map((part) => ({ field: part.field, label: part.label, text: part.text })),
          )
        : null

    if (mergedDimTable) {
      const levelLabel = dimShareParts.map((part) => part.label).join('·')
      const labelBase = dimShareLabelPrefix ? `${dimShareLabelPrefix}·${levelLabel}` : levelLabel
      const mergedText = dimShareParts.map((part) => part.text).join('；')
      chips.push({
        field: 'dim_combo',
        label: `${
          showRank.value && topN.value ? `${labelBase}·前${topN.value}` : labelBase
        }${countThresholdLabelSuffix()}`,
        value: mergedText,
        displayValue: mergedText || '无',
        tableHeaders: mergedDimTable.headers,
        tableRows: mergedDimTable.rows,
      })
    } else {
      for (const part of dimShareParts) {
        const labelBase = dimShareLabelPrefix ? `${dimShareLabelPrefix}·${part.label}` : part.label
        chips.push({
          field: part.field,
          label: `${
            showRank.value && topN.value ? `${labelBase}·前${topN.value}` : labelBase
          }${countThresholdLabelSuffix()}`,
          value: part.text || '无',
          displayValue: formatDisplay(part.field, part.text || '无'),
        })
      }
    }

    if (showOrgDimension.value && orgDimension.value && !showAnalysis.value) {
      const orgUnits = String(fields.org_units ?? result.org_units ?? '').trim()
      const orgLabel =
        orgDimension.value === 'pianqu'
          ? '片区'
          : orgDimension.value === 'gongjianwei'
            ? '共建委'
            : '警务区'
      const orgLabelPrefix = [
        flags.value.share ? '占比' : '',
        flags.value.momCount ? '环比数' : '',
        flags.value.yoyCount ? '同比数' : '',
        flags.value.yoy ? '同比' : '',
        flags.value.mom ? '环比' : '',
      ]
        .filter(Boolean)
        .join('+')
      const labelBase = orgLabelPrefix ? `${orgLabelPrefix}·${orgLabel}` : orgLabel
      chips.push({
        field: 'org_units',
        label: showRank.value && topN.value ? `${labelBase}·前${topN.value}` : labelBase,
        value: orgUnits || '无',
        displayValue: formatDisplay('org_units', orgUnits || '无'),
      })
    }

    if (flags.value.hotCommunity && !showAnalysis.value) {
      const hotCommunities = String(fields.hot_communities ?? result.hot_communities ?? '').trim()
      const communityLabelPrefix = [
        flags.value.share ? '占比' : '',
        flags.value.momCount ? '环比数' : '',
        flags.value.yoyCount ? '同比数' : '',
        flags.value.yoy ? '同比' : '',
        flags.value.mom ? '环比' : '',
      ]
        .filter(Boolean)
        .join('·')
      const labelBase = communityLabelPrefix ? `${communityLabelPrefix}·社区` : '社区'
      chips.push({
        field: 'hot_communities',
        label: `${
          showRank.value && topN.value ? `${labelBase}·前${topN.value}` : labelBase
        }${countThresholdLabelSuffix()}`,
        value: hotCommunities || '无',
        displayValue: formatDisplay('hot_communities', hotCommunities || '无'),
      })
    }

    if (flags.value.region && !showAnalysis.value) {
      const regions = String(fields.regions ?? result.regions ?? '').trim()
      const regionLabelPrefix = [
        flags.value.share ? '占比' : '',
        flags.value.momCount ? '环比数' : '',
        flags.value.yoyCount ? '同比数' : '',
        flags.value.yoy ? '同比' : '',
        flags.value.mom ? '环比' : '',
      ]
        .filter(Boolean)
        .join('·')
      const labelBase = regionLabelPrefix ? `${regionLabelPrefix}·辖区` : '辖区'
      chips.push({
        field: 'regions',
        label: `${
          showRank.value && topN.value ? `${labelBase}·前${topN.value}` : labelBase
        }${countThresholdLabelSuffix()}`,
        value: regions || '无',
        displayValue: formatDisplay('regions', regions || '无'),
      })
    }

    if (flags.value.hotPeriod) {
      const hotPeriods = String(fields.hot_periods ?? result.hot_periods ?? '').trim()
      const hours = Number(fields.hot_period_hours ?? HOT_PERIOD_HOURS) || HOT_PERIOD_HOURS
      chips.push({
        field: 'hot_periods',
        label: `${
          showRank.value && topN.value
            ? `高发时段(${hours}小时)·前${topN.value}`
            : `高发时段(${hours}小时)`
        }${countThresholdLabelSuffix()}`,
        value: hotPeriods || '无',
        displayValue: formatDisplay('hot_periods', hotPeriods || '无'),
      })
    }

    if (showAnalysis.value) {
      const stations = String(fields.yoy_stations ?? result.yoy_stations ?? '').trim()
      const prefix = flags.value.mom ? '环比' : flags.value.share ? '占比' : '同比'
      const scopeNoun = flags.value.hotCommunity
        ? '社区'
        : shareIntent.category
          ? '类别'
          : shareIntent.type
            ? '类型'
            : shareIntent.subtype
              ? '细类'
              : showOrgDimension.value
                ? orgDimension.value === 'pianqu'
                  ? '片区'
                  : orgDimension.value === 'gongjianwei'
                    ? '共建委'
                    : '警务区'
                : '所'
      const trendLabel =
        yoyTrend.value === 'down'
          ? `${scopeNoun}${prefix}降幅`
          : yoyTrend.value === 'analysis'
            ? `${scopeNoun}${prefix}自动`
            : `${scopeNoun}${prefix}升幅`
      chips.push({
        field: 'yoy_stations',
        label: showRank.value && topN.value ? `${trendLabel}·前${topN.value}` : trendLabel,
        value: stations || '无',
        displayValue: formatDisplay('yoy_stations', stations || '无'),
      })
    }

    if (showWarning.value && warningRuleType.value) {
      const warningText = String(fields.warning_text ?? result.warning_text ?? '').trim()
      chips.push({
        field: 'warning_text',
        label: `预警·${warningRuleType.value}`,
        value: warningText || '无',
        displayValue: formatDisplay('warning_text', warningText || '无'),
      })
    }

    return chips.map((chip) => enrichChipWithTableMode(chip))
  })

  function enrichChipWithTableMode(chip: AtomicMetricChip): AtomicMetricChip {
    const textValue = String(chip.textValue ?? chip.displayValue ?? chip.value ?? '').trim()
    const canTable =
      canShowAtomicMetricTableToggle(chip.field, textValue) ||
      Boolean(chip.tableHeaders && chip.tableHeaders.length >= 2 && chip.tableRows && chip.tableRows.length >= 2)
    const viewMode = (chipViewModes.value[chip.field] || 'text') as AtomicChipViewMode
    if (!canTable || viewMode === 'text') {
      return {
        ...chip,
        textValue,
        canTable,
        viewMode: canTable ? viewMode : 'text',
        dragPayload: textValue,
        dragIsHtml: false,
      }
    }
    let table =
      chip.tableHeaders?.length && chip.tableRows?.length
        ? { headers: chip.tableHeaders, rows: chip.tableRows }
        : null
    if (table && viewMode === 'table2') {
      table = transposeAtomicListTable(table)
    } else if (!table) {
      table = parseAtomicMetricListToTableMode(
        chip.field,
        textValue,
        viewMode === 'table2' ? 'table2' : 'table',
      )
    }
    if (!table) {
      return {
        ...chip,
        textValue,
        canTable,
        viewMode: 'text',
        dragPayload: textValue,
        dragIsHtml: false,
      }
    }
    return {
      ...chip,
      textValue,
      canTable: true,
      viewMode,
      tableHeaders: table.headers,
      tableRows: table.rows,
      displayValue: viewMode === 'table2' ? '表格（名称在头）' : '表格（名称在左）',
      dragPayload: formatAtomicListTableToHtml(table),
      dragIsHtml: true,
    }
  }

  function setChipViewMode(field: string, mode: AtomicChipViewMode) {
    chipViewModes.value = { ...chipViewModes.value, [field]: mode }
  }

  const executedSql = computed(() => String(queryResult.value?.executed_sql || '').trim())

  /** @returns true 查询成功；false 校验失败/取消 */
  async function queryAtomicMetric(): Promise<boolean> {
    const range = unref(dateRange)
    if (!range) {
      lastError.value = '请先设置全局时间范围'
      return false
    }
    if (showThreshold.value && (countThresholdValue.value == null || Number.isNaN(Number(countThresholdValue.value)))) {
      lastError.value = '请填写阈值数量'
      return false
    }

    abortController?.abort()
    const abort = new AbortController()
    abortController = abort
    querying.value = true
    lastError.value = ''
    chipViewModes.value = {}
    try {
      const result = await requestAtomicMetric(buildPayload(), { signal: abort.signal })
      if (abort.signal.aborted) return false
      queryResult.value = result
      return true
    } catch (error) {
      if (abort.signal.aborted || isAbortError(error)) {
        lastError.value = ''
        return false
      }
      queryResult.value = null
      lastError.value = error instanceof Error ? error.message : '原子指标查询失败'
      throw error
    } finally {
      if (abortController === abort) {
        abortController = null
        querying.value = false
      }
    }
  }

  function cancel() {
    if (!querying.value) return
    abortController?.abort()
    abortController = null
    querying.value = false
  }

  function reset() {
    flags.value = { ...DEFAULT_FLAGS }
    showOrgDimension.value = false
    orgDimension.value = ''
    showTag.value = false
    tagPackageId.value = null
    showAnalysis.value = false
    yoyTrend.value = ''
    showRank.value = false
    topN.value = null
    rankSortBy.value = 'count'
    rankSortOrder.value = 'desc'
    showThreshold.value = false
    countThresholdOp.value = 'gt'
    countThresholdValue.value = null
    showWarning.value = false
    warningRuleType.value = ''
    queryResult.value = null
    lastError.value = ''
    chipViewModes.value = {}
    // 保留类别/类型/细类多选
  }

  function startMetricDrag(event: DragEvent, chip: AtomicMetricChip) {
    if (!event.dataTransfer) {
      event.preventDefault()
      return
    }
    const payload = String(chip.dragPayload ?? chip.displayValue ?? '')
    const plain = String(chip.textValue ?? chip.displayValue ?? '')
    event.dataTransfer.effectAllowed = 'copy'
    if (chip.dragIsHtml && payload) {
      event.dataTransfer.setData(REPORT_METRIC_HTML_MIME, payload)
      event.dataTransfer.setData('text/html', payload)
      event.dataTransfer.setData(REPORT_METRIC_VALUE_MIME, plain)
      event.dataTransfer.setData('text/plain', plain)
      return
    }
    event.dataTransfer.setData(REPORT_METRIC_VALUE_MIME, payload)
    event.dataTransfer.setData('text/plain', payload)
    if (looksLikeTrend(payload)) {
      event.dataTransfer.setData(REPORT_METRIC_TREND_MIME, '1')
    }
  }

  return {
    dateRange,
    source,
    deptCode,
    deptName,
    flags,
    categoryCodes,
    typeCodes,
    subtypeCodes,
    categoryNames,
    typeNames,
    subtypeNames,
    showOrgDimension,
    orgDimension,
    orgDimensionOptions,
    showTag,
    tagPackageId,
    showAnalysis,
    yoyTrend,
    yoyTrendOptions,
    showRank,
    topN,
    rankSortBy,
    rankSortOrder,
    rankSortByOptions,
    rankSortOrderOptions,
    showThreshold,
    countThresholdOp,
    countThresholdValue,
    countThresholdOpOptions,
    showWarning,
    warningRuleType,
    queryResult,
    querying,
    lastError,
    atomicMetricChips,
    executedSql,
    setFlag,
    setShowOrgDimension,
    setShowAnalysis,
    setShowRank,
    setShowThreshold,
    setShowTag,
    setShowWarning,
    queryAtomicMetric,
    reset,
    cancel,
    setChipViewMode,
    startMetricDrag,
    buildPayload,
  }
}

export type UseAtomicMetricReturn = ReturnType<typeof useAtomicMetric>
