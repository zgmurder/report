import { apiPost } from './request'

export interface PoliceEventQuery {
  start_time?: string
  end_time?: string
  keyword?: string
  event_type?: string
  unit_code?: string
  page: number
  page_size: number
}

export function searchPoliceEvents(query: PoliceEventQuery) {
  return apiPost<{ total: number; page: number; page_size: number; items: unknown[] }>('/police-events/search', query)
}

export function getPoliceOverview(query: PoliceEventQuery) {
  return apiPost<{ total: number; by_type: unknown[]; by_unit: unknown[]; trend: unknown[] }>('/police-events/overview', query)
}
