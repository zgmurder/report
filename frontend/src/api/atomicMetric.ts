import { apiPost } from '@/api/request'

/** 与后端 AtomicMetricQueryRequest 对齐（snake_case） */
export interface AtomicMetricQueryPayload {
  data_source?: string | null
  dept_code?: string | null
  date_start?: string | null
  date_end?: string | null
  document_type?: string | null
  category_code?: string | null
  category_name?: string | null
  type_code?: string | null
  subtype_code?: string | null
  include_yoy?: boolean
  include_mom?: boolean
  include_share?: boolean
  include_mom_count?: boolean
  include_yoy_count?: boolean
  include_cumulative?: boolean
  include_dim_combo?: boolean
  dim_combo_levels?: string | null
  include_category_share?: boolean
  include_type_share?: boolean
  include_subtype_share?: boolean
  include_hot_community?: boolean
  org_dimension?: string | null
  include_hot_period?: boolean
  hot_period_hours?: number | null
  include_region_table?: boolean
  filter_duplicate?: boolean
  exclude_non_police?: boolean
  exclude_traffic?: boolean
  filter_self_received?: boolean
  exclude_self_received?: boolean
  tag_package_id?: number | null
  yoy_trend?: string | null
  trend_compare?: string | null
  yoy_analysis_drill?: string | null
  yoy_trend_top_n?: number | null
  rank_sort_by?: string | null
  rank_sort_order?: string | null
  count_threshold_op?: string | null
  count_threshold_value?: number | null
  include_warning?: boolean
  warning_rule_type?: string | null
  params?: Record<string, unknown>
}

/** 与后端 AtomicMetricQueryResult 对齐（snake_case） */
export interface AtomicMetricQueryResult {
  total?: number | null
  yoy?: number | null
  mom?: number | null
  yoy_change?: string | null
  mom_change?: string | null
  yoy_count?: number | null
  mom_count?: number | null
  cumulative?: number | null
  dim_combo?: string | null
  dim_table_headers?: string[] | null
  dim_table_rows?: string[][] | null
  share?: number | null
  category_share?: string | null
  type_share?: string | null
  subtype_share?: string | null
  hot_communities?: string | null
  org_units?: string | null
  hot_periods?: string | null
  regions?: string | null
  yoy_stations?: string | null
  warning_text?: string | null
  table_title?: string | null
  table_headers?: string[] | null
  table_rows?: string[][] | null
  html_fragment?: string | null
  field_values?: Record<string, unknown>
  content_segments?: Array<Record<string, unknown>>
  text_content?: string | null
  executed_sql?: string | null
}

export function queryAtomicMetric(
  data: AtomicMetricQueryPayload,
  options?: { signal?: AbortSignal; timeout?: number },
) {
  return apiPost<AtomicMetricQueryResult>('/atomic-metric/query', data, {
    timeout: 180000,
    ...options,
  })
}
