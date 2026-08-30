# Agent UI

与业务、接口和宿主 UI 框架解耦的 Vue 3 Agent 对话视觉组件。视觉结构高保真迁移自 MIT 许可的 [Pi Web](https://github.com/agegr/pi-web)，参考 commit `28bab3c25f5f6770c9b0b745ebbfec1c27f7b948`；版权与许可证见仓库根目录 `THIRD_PARTY_NOTICES.md` 和 `licenses/pi-web-MIT.txt`。

## 使用

```vue
<script setup>
import { ref } from 'vue'
import { AgentChatPanel } from './components/agent-ui'

const draft = ref('')
const messages = ref([])
const running = ref(false)
</script>

<template>
  <AgentChatPanel
    v-model="draft"
    :messages="messages"
    :running="running"
    assistant-label="My Agent"
    @submit="send"
    @stop="stop"
  />
</template>
```

## 消息契约

```js
{
  id: 'unique-id',
  role: 'user' | 'assistant',
  content: '',
  thinking: '',
  running: false,
  error: '',
  durationMs: 1200,
  tools: [{
    id: 'tool-id',
    tool: 'read',
    label: '读取文件',
    detail: '/path/file',
    status: 'running' | 'success' | 'error',
    output: '',
  }],
}
```

组件不负责请求、流协议、消息持久化或全局通知。宿主项目负责把自己的 Agent 事件转换为上述消息结构。

## 主题

在组件或祖先元素覆盖 CSS 变量：

```css
.my-agent-theme {
  --agent-ui-bg: #fff;
  --agent-ui-surface-muted: #f8fafc;
  --agent-ui-user-bg: #f4f4f5;
  --agent-ui-text: #18181b;
  --agent-ui-text-muted: #71717a;
  --agent-ui-border: #e4e4e7;
  --agent-ui-border-strong: #a1a1aa;
  --agent-ui-accent: #2563eb;
  --agent-ui-success: #16a34a;
  --agent-ui-danger: #dc2626;
  --agent-ui-code-bg: #18181b;
  --agent-ui-code-text: #e4e4e7;
}
```

## 可复用边界

- 仅依赖 Vue 3。
- 不依赖 Element Plus、项目 API、Router、Pinia 或业务 composable。
- `AgentChatPanel` 只通过 props、`v-model` 和 emits 与宿主通信。
- `AgentMessage`、`AgentToolTimeline` 可以单独导入使用。
