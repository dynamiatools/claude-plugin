import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { DevVar, Draft } from '../types'
import { addArgv, listArgv, parseAdd, parseListing, rmArgv } from './devenv'

const vars = atom({ plugin: 'dynamia', key: 'vars' } as const, [] as DevVar[])
const repos = atom({ plugin: 'dynamia', key: 'repos' } as const, [] as string[])
const draft = atom({ plugin: 'dynamia', key: 'draft' } as const, { name: '', value: '', repo: '' } as Draft)
const message = atom({ plugin: 'dynamia', key: 'message' } as const, '')

const ALL = 'all'

// One place that calls the command-line tool, which owns the edits to workspace.toml.
async function tool($: EngineInterface, argv: string[]) {
  const out = await $.process.run(argv)

  return { ok: out.exitCode === 0, text: (out.stdout || out.stderr).trim() }
}

async function refresh($: EngineInterface) {
  const out = await tool($, listArgv($.plugin.root))
  const listing = out.ok ? parseListing(out.text) : null
  if (!listing) {
    await update($, message, () => out.text.split('\n')[0] || 'No workspace here.')
    await update($, vars, () => [])

    return false
  }
  await update($, vars, () => listing.vars)
  await update($, repos, () => listing.repos)

  return true
}

async function add($: EngineInterface) {
  const d = await read($, draft)
  if (!d.name || d.value === '') {
    await update($, message, () => 'Type a NAME and a value first.')

    return
  }
  const out = await tool($, addArgv($.plugin.root, d))
  await update($, message, () => out.text.split('\n')[0] ?? '')
  if (out.ok) await update($, draft, one => ({ ...one, name: '', value: '' }))
  await refresh($)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'env-panel',
      description: 'Development variables of the workspace: a panel, or env-panel NAME=value [repo], rm NAME [repo], list',
    })

    return next(e)
  })

  on('command.run', { command: 'env-panel' }, async ($, e) => {
    const args = e.args.trim()
    const root = $.plugin.root
    if (args === '') {
      await refresh($)
      await $.ui.open({ id: 'dev-env', title: 'Dev env', focus: true })

      return { text: 'Dev env panel opened.' }
    }
    if (args === 'list') {
      const out = await tool($, [`${root}/bin/ms-workspace`, 'dev-env', 'list'])

      return { text: out.text }
    }
    if (args.startsWith('rm ')) {
      const [, name = '', scope = ''] = args.split(/\s+/)
      const out = await tool($, rmArgv(root, name, scope))
      await refresh($)

      return { text: out.text }
    }
    await refresh($)
    const parsed = parseAdd(args, await read($, repos))
    if (!parsed) return { text: 'Usage: env-panel NAME=value [repo] | rm NAME [repo] | list' }
    const out = await tool($, addArgv(root, parsed))
    await refresh($)

    return { text: out.text }
  })

  on('ui.input', async ($, e, next) => {
    if (e.plugin !== 'dynamia') return next(e)
    if (e.element === 'name') await update($, draft, one => ({ ...one, name: e.value.trim().toUpperCase() }))
    if (e.element === 'value') await update($, draft, one => ({ ...one, value: e.value }))
    if (e.kind === 'submit') await add($)

    return next(e)
  })

  on('ui.select', async ($, e, next) => {
    if (e.plugin === 'dynamia' && e.element === 'repo') {
      await update($, draft, one => ({ ...one, repo: e.value === ALL ? '' : e.value }))
    }

    return next(e)
  })

  on('ui.press', async ($, e, next) => {
    if (e.plugin !== 'dynamia') return next(e)
    if (e.element === 'add') await add($)
    if (e.element.startsWith('rm:')) {
      const [, scope = '', name = ''] = e.element.split(':')
      const out = await tool($, rmArgv($.plugin.root, name, scope))
      await update($, message, () => out.text.split('\n')[0] ?? '')
      await refresh($)
    }

    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: 'dev-env' }, async ($, e) => {
    const { Box, Text, Button, Input, Select } = $.ui.resolve(e)
    const list = await read($, vars)
    const names = await read($, repos)
    const d = await read($, draft)
    const note = await read($, message)
    const room = Math.max(1, (e.viewport?.rows ?? 24) - 9)
    const options = [{ value: ALL, label: 'all repos' }, ...names.map(name => ({ value: name, label: name }))]

    return (
      <Box flexDirection="column">
        <Text dimColor>Development only. Saved in workspace.toml, plain text.</Text>
        {list.length === 0 && <Text dimColor>No variables yet.</Text>}
        {list.slice(0, room).map(v => (
          <Box flexDirection="row" gap={1}>
            <Text dimColor>{v.scope}</Text>
            <Text>
              {v.name}={v.value}
            </Text>
            <Button key={`rm:${v.scope}:${v.name}`} label="remove" onPress={() => {}} />
          </Box>
        ))}
        {list.length > room && <Text dimColor>{list.length - room} more: /env-panel list</Text>}
        <Input key="name" label="NAME" placeholder="API_URL" value={d.name} onSubmit={() => {}} />
        <Input key="value" label="value" placeholder="http://localhost:8080" value={d.value} onSubmit={() => {}} submitLabel="add" />
        {names.length > 0 && <Select key="repo" label="for" options={options} value={d.repo || ALL} onSelect={() => {}} />}
        <Button key="add" label="Add" variant="primary" onPress={() => {}} />
        {note !== '' && <Text dimColor>{note}</Text>}
      </Box>
    )
  })
}
