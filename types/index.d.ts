export type DevVar = { scope: string; name: string; value: string; secret: boolean }
export type Draft = { name: string; value: string; repo: string }

declare module 'claude-code' {
  interface PluginState {
    dynamia: {
      vars: DevVar[]
      repos: string[]
      draft: Draft
      message: string
    }
  }
}
