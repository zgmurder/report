import { apiGet, apiPut } from './request'
import { buildQuery, wrapData, type DataEnvelope } from '@/utils/apiEnvelope'

export type WarningHandleStatus = '0' | '1' | '2'
export type WarningRuleType =
  | 'dayRise'
  | 'weekRise'
  | 'suspect'
  | 'repeat'
  | 'pcsDayHb30'
  | 'pcsWeekHb30'
  | 'pcsMonthHb30'
  | 'pcsMonthTb30'
export type WarningViewMode = 'summary' | 'detail'

export interface WarningRuleMeta {
  ruleType: WarningRuleType
  label: string
  description: string
  sourceTable: string
  supportsHandle: boolean
}

export interface SuspectWarningRow {
  xlbh: string
  lx?: string | null
  rq?: string | null
  sdpcsdm?: string | null
  sdpcs?: string | null
  tjwdbq?: string | null
  tsrybq?: string | null
  ryxm?: string | null
  rysfz?: string | null
  jjdbh?: string | null
  bjsj?: string | null
  jqsl?: string | null
  tjsj?: string | number | null
  handleStatus?: WarningHandleStatus | string | null
  handleRemark?: string | null
  handleBy?: string | null
  handleTime?: string | null
  warningText?: string | null
  alarmCount?: number | null
  ruleType?: WarningRuleType
  groupKey?: string | null
  scope?: 'city' | 'station' | string | null
  jjdMatched?: boolean
  alarmTitle?: string | null
  alarmContent?: string | null
  alarmAddress?: string | null
  alarmPhone?: string | null
  alarmCategory?: string | null
  bjlbmc?: string | null
  bjlxmc?: string | null
  bjxlmc?: string | null
  jjdwmc?: string | null
}

export interface WeekRiseWarningRow {
  xlbh: string
  weekStart?: string | null
  weekEnd?: string | null
  sdpcsdm?: string | null
  sdpcs?: string | null
  ajlb?: string | null
  jjzs?: number | null
  dzjqhb?: string | null
  szPcsjjzs?: number | null
  szJqhb?: string | null
  sszPcsjjzs?: number | null
  sszJqhb?: string | null
  tjsj?: string | number | null
  warningText?: string | null
  ruleType?: WarningRuleType
}

export interface DayRiseWarningRow {
  xlbh: string
  rq?: string | null
  sdpcsdm?: string | null
  sdpcs?: string | null
  ajlb?: string | null
  jjzs?: number | null
  drjqhb?: string | null
  zrPcsjjzs?: number | null
  zrJqhb?: string | null
  qrPcsjjzs?: number | null
  qrJqhb?: string | null
  tjsj?: string | number | null
  warningText?: string | null
  ruleType?: WarningRuleType
}

export interface PcsDayHb30WarningRow {
  xlbh: string
  rq?: string | null
  sdpcsdm?: string | null
  sdpcs?: string | null
  ajlb?: string | null
  jjzs?: number | null
  drjqhb?: string | null
  zrPcsjjzs?: number | null
  tjsj?: string | number | null
  warningText?: string | null
  ruleType?: WarningRuleType
}

export interface PcsWeekHb30WarningRow {
  xlbh: string
  weekStart?: string | null
  weekEnd?: string | null
  sdpcsdm?: string | null
  sdpcs?: string | null
  ajlb?: string | null
  jjzs?: number | null
  dzjqhb?: string | null
  szPcsjjzs?: number | null
  tjsj?: string | number | null
  warningText?: string | null
  ruleType?: WarningRuleType
}

export interface PcsMonthHb30WarningRow {
  xlbh: string
  monthStart?: string | null
  monthEnd?: string | null
  sdpcsdm?: string | null
  sdpcs?: string | null
  ajlb?: string | null
  jjzs?: number | null
  dyjqhb?: string | null
  syPcsjjzs?: number | null
  tjsj?: string | number | null
  warningText?: string | null
  ruleType?: WarningRuleType
}

export interface PcsMonthTb30WarningRow {
  xlbh: string
  monthStart?: string | null
  monthEnd?: string | null
  sdpcsdm?: string | null
  sdpcs?: string | null
  ajlb?: string | null
  jjzs?: number | null
  dyjqtb?: string | null
  syJjzs?: number | null
  tjsj?: string | number | null
  warningText?: string | null
  ruleType?: WarningRuleType
}

export interface RepeatWarningRow {
  xlbh: string
  lx?: string | null
  tjsj?: string | number | null
  ryxm?: string | null
  rysfz?: string | null
  dhhm?: string | null
  pcsdm?: string | null
  pcsmc?: string | null
  sdpcsdm?: string | null
  sdpcs?: string | null
  jjdbh?: string | null
  bjsj?: string | null
  bjcs?: number | null
  detailCount?: number | null
  warningText?: string | null
  ruleType?: WarningRuleType
  groupKey?: string | null
}

export type WarningListRow = SuspectWarningRow &
  WeekRiseWarningRow &
  DayRiseWarningRow &
  RepeatWarningRow &
  PcsDayHb30WarningRow &
  PcsWeekHb30WarningRow &
  PcsMonthHb30WarningRow &
  PcsMonthTb30WarningRow

export interface SuspectWarningSummary {
  total: number
  pending: number
  handled: number
  ignored: number
  labels: Array<{ label: string; count: number }>
  ruleType?: WarningRuleType
}

export interface SuspectWarningQuery {
  ruleType?: WarningRuleType
  pageNum?: number
  pageSize?: number
  keyword?: string
  rysfz?: string
  ryxm?: string
  dhhm?: string
  sdpcs?: string
  sdpcsdm?: string
  orgCode?: string
  orgName?: string
  pcsdm?: string
  pcsmc?: string
  jjdbh?: string
  tjwdbq?: string
  /** 报警类别代码（bjlbdm） */
  bjlb?: string
  /** 报警类型代码（bjlxdm） */
  bjlx?: string
  ajlb?: string
  handleStatus?: string
  beginRq?: string
  endRq?: string
  beginBjsj?: string
  endBjsj?: string
  viewMode?: WarningViewMode
}

/** 预警列表分页外壳（与新后端 data 对齐） */
export interface WarningListPage {
  rows: WarningListRow[]
  total: number
  pageNum?: number
  pageSize?: number
  citySummaries?: unknown
}

export interface WarningCategoryNode {
  code: string
  name: string
  parentCode?: string
  level: 'category' | 'type' | 'subtype'
  children?: WarningCategoryNode[]
}

export async function listWarningRules(): Promise<DataEnvelope<WarningRuleMeta[]>> {
  const data = await apiGet<WarningRuleMeta[]>('/warnings/rules')
  return wrapData(data)
}

export async function getWarningSummary(
  ruleType: WarningRuleType = 'suspect',
): Promise<DataEnvelope<SuspectWarningSummary>> {
  const query = buildQuery({ ruleType })
  const data = await apiGet<SuspectWarningSummary>(`/warnings/summary${query}`)
  return wrapData(data)
}

export async function listWarningLabels(): Promise<DataEnvelope<string[]>> {
  const data = await apiGet<string[]>('/warnings/labels')
  return wrapData(data)
}

export async function listWarningIncidentCategories(): Promise<DataEnvelope<WarningCategoryNode[]>> {
  const data = await apiGet<WarningCategoryNode[]>('/warnings/incident-categories')
  return wrapData(data)
}

export async function listWarnings(
  params: SuspectWarningQuery,
): Promise<DataEnvelope<WarningListPage>> {
  const query = buildQuery({ ...params })
  const data = await apiGet<WarningListPage>(`/warnings/list${query}`)
  return wrapData(data)
}

export async function listSuspectGroupDetails(params: {
  sdpcsdm?: string
  sdpcs?: string
  rq?: string
  cityScope?: boolean
  bjlb?: string
  bjlx?: string
  pageNum?: number
  pageSize?: number
}): Promise<DataEnvelope<WarningListPage>> {
  const query = buildQuery({ ...params })
  const data = await apiGet<WarningListPage>(`/warnings/suspect/details${query}`)
  return wrapData(data)
}

export async function listRepeatGroupDetails(params: {
  rysfz?: string
  ryxm?: string
  dhhm?: string
  pageNum?: number
  pageSize?: number
}): Promise<DataEnvelope<WarningListPage>> {
  const query = buildQuery({ ...params })
  const data = await apiGet<WarningListPage>(`/warnings/repeat/details${query}`)
  return wrapData(data)
}

export async function getWarningDetail(
  xlbh: string | number,
  ruleType: WarningRuleType = 'suspect',
): Promise<DataEnvelope<WarningListRow>> {
  const query = buildQuery({ ruleType })
  const data = await apiGet<WarningListRow>(`/warnings/${xlbh}${query}`)
  return wrapData(data)
}

export async function handleWarning(
  xlbh: string | number,
  data: { handleStatus: WarningHandleStatus; handleRemark?: string },
): Promise<DataEnvelope<SuspectWarningRow>> {
  const result = await apiPut<SuspectWarningRow>(`/warnings/${xlbh}/handle`, data)
  return wrapData(result)
}
