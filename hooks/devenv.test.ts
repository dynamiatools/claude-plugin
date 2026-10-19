import { describe, expect, test } from 'claude-code/testing'

import { addArgv, listArgv, parseAdd, parseListing, rmArgv } from './devenv'

describe('dev-env helpers', () => {
  test('parseListing accepts the tool JSON and nothing else', async () => {
    const ok = parseListing('{"repos":["lib"],"vars":[{"scope":"all","name":"A","value":"1","secret":false}]}')
    expect(ok?.repos).toEqual(['lib'])
    expect(ok?.vars.length).toBe(1)
    expect(parseListing('ERROR: no workspace')).toBeNull()
    expect(parseListing('{"repos":1}')).toBeNull()
  })

  test('parseAdd reads NAME=value and an optional trailing repo', async () => {
    const repos = ['lib', 'app']
    expect(parseAdd('API_URL=http://x', repos)).toEqual({ name: 'API_URL', value: 'http://x', repo: '' })
    expect(parseAdd('DEBUG=1 app', repos)).toEqual({ name: 'DEBUG', value: '1', repo: 'app' })
    expect(parseAdd('MSG=hello world', repos)).toEqual({ name: 'MSG', value: 'hello world', repo: '' })
    expect(parseAdd('app', repos)).toBeNull()
    expect(parseAdd('=x', repos)).toBeNull()
  })

  test('argv builders never go through a shell and scope with --repo', async () => {
    expect(addArgv('/p', { name: 'A', value: 'a b', repo: '' })).toEqual(['/p/bin/ms-workspace', 'dev-env', 'add', 'A=a b'])
    expect(addArgv('/p', { name: 'A', value: '1', repo: 'lib' }).slice(-2)).toEqual(['--repo', 'lib'])
    expect(rmArgv('/p', 'A', 'all')).toEqual(['/p/bin/ms-workspace', 'dev-env', 'rm', 'A'])
    expect(rmArgv('/p', 'A', 'lib').slice(-2)).toEqual(['--repo', 'lib'])
    expect(listArgv('/p')).toEqual(['/p/bin/ms-workspace', 'dev-env', 'list', '--json'])
  })
})

describe('dev-env pane', () => {
  test('draws the form on the surfaces that take input', async $ => {
    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({
        plugin: 'dynamia',
        surface,
        component: 'Pane',
        props: {},
        requestId: 'dev-env',
        viewport: { columns: 120, rows: 30 },
      })
      expect(await ui.find({ key: 'name' })).toBeDefined()
      expect(await ui.find({ key: 'value' })).toBeDefined()
      expect(await ui.find({ key: 'add' })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /No variables yet/ })).toBeDefined()
      await ui.unmount()
    }
  })
})
