import { reactive, ref } from 'vue'
import type { Ref } from 'vue'
import { streamPiAgent, type PiAgentEvent } from '@/api/piAgent'

export interface PiAgentTool {
  id: string
  tool: string
  label: string
  detail: string
  status: 'running' | 'success' | 'error'
  output: string
}

export interface PiAgentMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  tools?: PiAgentTool[]
  running?: boolean
  error?: string
  durationMs?: number | null
}

const TOOL_LABELS: Record<string, string> = {
  read: '读取文件', write: '写入文件', edit: '修改文件', bash: '执行命令',
  grep: '搜索内容', find: '查找文件', ls: '浏览目录', Agent: '运行子 Agent',
}

function summarizeArgs(tool: string, args: Record<string, unknown> = {}) {
  if (tool === 'bash') return String(args.command || '执行命令')
  return String(args.path || args.pattern || args.query || JSON.stringify(args))
}

export function usePiAgentChat(onError?: (message: string) => void, context?: Ref<string | undefined>) {
  const prompt = ref('')
  const running = ref(false)
  const messages = ref<PiAgentMessage[]>([])
  let controller: AbortController | null = null
  let sequence = 0

  function handleEvent(message: PiAgentMessage, event: PiAgentEvent) {
    if (event.type === 'text_delta') message.content += event.delta || ''
    if (event.type === 'thinking_delta') message.thinking = (message.thinking || '') + (event.delta || '')
    if (event.type === 'tool_start') message.tools?.push(reactive({
      id: event.id || `${Date.now()}`, tool: event.tool || '',
      label: TOOL_LABELS[event.tool || ''] || event.tool || '工具',
      detail: summarizeArgs(event.tool || '', event.args), status: 'running', output: '',
    }))
    if (event.type === 'tool_end') {
      const tool = message.tools?.find((item) => item.id === event.id)
      if (tool) Object.assign(tool, { status: event.is_error ? 'error' : 'success', output: event.output || '' })
    }
    if (event.type === 'done') Object.assign(message, { running: false, durationMs: event.duration_ms })
    if (event.type === 'error') {
      Object.assign(message, { running: false, error: event.message || 'Pi 执行失败' })
      onError?.(message.error || 'Pi 执行失败')
    }
  }

  async function send(contentOverride?: string) {
    const content = (contentOverride ?? prompt.value).trim()
    if (!content || running.value) return
    const reportContext = context?.value?.trim()
    const agentPrompt = reportContext
      ? `你正在协助用户编辑警情分析报告。以下是当前报告 HTML，仅作为上下文，请优先回答用户请求，不要直接修改数据库：\n\n${reportContext.slice(0, 12000)}\n\n用户请求：${content}`
      : content
    prompt.value = ''
    messages.value.push({ id: ++sequence, role: 'user', content })
    const assistant = reactive<PiAgentMessage>({
      id: ++sequence, role: 'assistant', content: '', thinking: '', tools: [],
      running: true, error: '', durationMs: null,
    })
    messages.value.push(assistant)
    running.value = true
    controller = new AbortController()
    try {
      await streamPiAgent(agentPrompt, { signal: controller.signal, onEvent: (event) => handleEvent(assistant, event) })
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        assistant.error = (error as Error).message
        onError?.((error as Error).message)
      }
    } finally {
      assistant.running = false
      running.value = false
      controller = null
    }
  }

  function stop() {
    const active = [...messages.value].reverse().find((item: PiAgentMessage) => item.role === 'assistant' && item.running)
    if (active) {
      active.running = false
      active.content += active.content ? '\n\n（任务已停止）' : '任务已停止'
    }
    controller?.abort()
  }

  return { prompt, running, messages, send, stop }
}
