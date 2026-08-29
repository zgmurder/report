declare module '@umoteam/editor' {
  import type { DefineComponent } from 'vue'

  export const UmoEditor: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default UmoEditor
}

declare module '@umoteam/editor/style'
