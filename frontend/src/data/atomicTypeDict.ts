/** 原子指标：类型代码 → 中文名（后端字典缺失时前端兜底） */
export const ATOMIC_TYPE_LABEL_MAP: Record<string, string> = {
  '24000': '违章停车',
  '25000': '交通信号灯故障'
}

/**
 * 将占比文案中的类型代码替换为中文名。
 * 匹配形如「24000234起」或「24000 234起」。
 */
export function applyAtomicTypeLabels(text: string): string {
  const raw = String(text || '')
  if (!raw || raw === '无') return raw
  let result = raw
  for (const [code, label] of Object.entries(ATOMIC_TYPE_LABEL_MAP)) {
    if (!code || !label) continue
    result = result.replace(new RegExp(`(?<!\\d)${code}(?=\\s*\\d+起)`, 'g'), label)
  }
  return result
}
