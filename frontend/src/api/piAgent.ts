export interface PiAgentEvent {
  type: 'session' | 'status' | 'text_delta' | 'thinking_delta' | 'tool_start' | 'tool_end' | 'done' | 'error'
  session_id?: string
  status?: string
  message?: string
  delta?: string
  id?: string
  tool?: string
  args?: Record<string, unknown>
  is_error?: boolean
  output?: string
  duration_ms?: number
}

function parseLines(buffer: string, onEvent: (event: PiAgentEvent) => void) {
  const lines = buffer.split('\n')
  for (const line of lines.slice(0, -1)) {
    if (!line.trim()) continue
    try { onEvent(JSON.parse(line) as PiAgentEvent) } catch { /* 忽略非 JSON 行 */ }
  }
  return lines[lines.length - 1] || ''
}

export async function streamPiAgent(
  prompt: string,
  options: { signal: AbortSignal; onEvent: (event: PiAgentEvent) => void },
) {
  const token = localStorage.getItem('report_access_token')
  const response = await fetch('/api/v1/pi-agent/stream', {
    method: 'POST',
    signal: options.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ prompt }),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail || `Pi 请求失败：${response.status}`)
  }
  if (!response.body) throw new Error('浏览器不支持流式响应')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer = parseLines(buffer + decoder.decode(value, { stream: true }), options.onEvent)
  }
  parseLines(buffer + decoder.decode() + '\n', options.onEvent)
}
