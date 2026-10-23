export type DevVar = { scope: string; name: string; value: string; secret: boolean }
export type Draft = { name: string; value: string; repo: string }
export type Note = { type: string; batch: string; title: string; name: string }
export type NoteDraft = { type: string; text: string }

declare module 'claude-code' {
  interface PluginState {
    dynamia: {
      vars: DevVar[]
      repos: string[]
      draft: Draft
      message: string
      logLines: string[]
      noteRows: Note[]
      noteDraft: NoteDraft
      panelNote: string
    }
  }
}
