import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Note } from './views'
import { addNoteArgv, forgetArgv, logArgv, notesArgv, parseNotes } from './views'

const logLines = atom({ plugin: 'dynamia', key: 'logLines' } as const, [] as string[])
const noteRows = atom({ plugin: 'dynamia', key: 'noteRows' } as const, [] as Note[])
const noteDraft = atom({ plugin: 'dynamia', key: 'noteDraft' } as const, { type: 'lesson', text: '' })
const panelNote = atom({ plugin: 'dynamia', key: 'panelNote' } as const, '')

const TYPES = ['decision', 'lesson', 'gotcha', 'handoff']

async function run($: EngineInterface, argv: string[]) {
  const out = await $.process.run(argv)

  return { ok: out.exitCode === 0, text: (out.stdout || out.stderr).trim() }
}

async function refreshLogs($: EngineInterface, rows: number) {
  const out = await run($, logArgv($.plugin.root, Math.max(5, rows)))
  await update($, logLines, () => (out.ok ? out.text.split('\n') : []))
  await update($, panelNote, () => (out.ok ? '' : out.text.split('\n')[0] ?? ''))
}

async function refreshNotes($: EngineInterface) {
  const out = await run($, notesArgv($.plugin.root))
  await update($, noteRows, () => (out.ok ? parseNotes(out.text) : []))
  await update($, panelNote, () => (out.ok ? '' : out.text.split('\n')[0] ?? ''))
}

async function addNote($: EngineInterface) {
  const d = await read($, noteDraft)
  if (!d.text.trim()) {
    await update($, panelNote, () => 'Type the note first.')

    return
  }
  const out = await run($, addNoteArgv($.plugin.root, d.type, d.text))
  await update($, panelNote, () => out.text.split('\n')[0] ?? '')
  if (out.ok) await update($, noteDraft, one => ({ ...one, text: '' }))
  await refreshNotes($)
}

// The ui.input / ui.select / ui.press hooks live in register.tsx (one per event); they call these.
export async function panelInput($: EngineInterface, element: string, value: string, submit: boolean) {
  if (element === 'note') await update($, noteDraft, one => ({ ...one, text: value }))
  if (element === 'note' && submit) await addNote($)
}

export async function panelSelect($: EngineInterface, element: string, value: string) {
  if (element === 'note-type') await update($, noteDraft, one => ({ ...one, type: value }))
}

export async function panelPress($: EngineInterface, element: string) {
  if (element === 'logs-refresh') await refreshLogs($, 20)
  if (element === 'note-add') await addNote($)
  if (element.startsWith('forget:')) {
    const out = await run($, forgetArgv($.plugin.root, element.slice('forget:'.length)))
    await update($, panelNote, () => out.text.split('\n')[0] ?? '')
    await refreshNotes($)
  }
}

// Called from the single session.start hook in register.tsx (the engine refuses a second one).
export async function registerPanelCommands($: EngineInterface) {
  await $.command.register({ name: 'dynamia-logs-panel', description: 'Recent actions of the workspace log (ms-workspace log)' })
  await $.command.register({ name: 'dynamia-memory-panel', description: 'Workspace memory notes: browse, add, forget' })
}

export const registerPanels: Register = on => {
  on('command.run', { command: 'dynamia-logs-panel' }, async $ => {
    await refreshLogs($, 20)
    await $.ui.open({ id: 'dynamia-logs', title: 'Dynamia logs', focus: true })

    return { text: 'Dynamia logs panel opened.' }
  })

  on('command.run', { command: 'dynamia-memory-panel' }, async $ => {
    await refreshNotes($)
    await $.ui.open({ id: 'dynamia-memory', title: 'Dynamia memory', focus: true })

    return { text: 'Dynamia memory panel opened.' }
  })

  on('ui.render', { component: 'Pane', requestId: 'dynamia-logs' }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const lines = await read($, logLines)
    const note = await read($, panelNote)
    const room = Math.max(3, (e.viewport?.rows ?? 24) - 6)

    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column">
          <Text bold>Workspace log</Text>
          <Text dimColor>Latest actions, newest last. Same as: ms-workspace log</Text>
        </Box>
        {lines.length === 0 && <Text dimColor>Nothing logged yet.</Text>}
        <Box flexDirection="column">
          {lines.slice(-room).map((line, i) => (
            <Text key={i}>{line}</Text>
          ))}
        </Box>
        <Button key="logs-refresh" label="Refresh" onPress={() => {}} />
        {note !== '' && <Text color="yellow">{note}</Text>}
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: 'dynamia-memory' }, async ($, e) => {
    const { Box, Text, Button, Input, Select } = $.ui.resolve(e)
    const rows = await read($, noteRows)
    const d = await read($, noteDraft)
    const note = await read($, panelNote)
    const room = Math.max(3, (e.viewport?.rows ?? 24) - 12)

    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column">
          <Text bold>Workspace memory</Text>
          <Text dimColor>Decisions, lessons, gotchas and handoffs. Same as: ms-workspace memory</Text>
        </Box>
        {rows.length === 0 && <Text dimColor>No notes yet. Add the first one below.</Text>}
        <Box flexDirection="column">
          {rows.slice(0, room).map(n => (
            <Box key={n.name} flexDirection="row" gap={1}>
              <Button key={`forget:${n.name}`} label="✕" onPress={() => {}} />
              <Text color="cyan">{n.type.padEnd(8)}</Text>
              <Text>{n.title}</Text>
              {n.batch !== '' && <Text dimColor>[{n.batch}]</Text>}
            </Box>
          ))}
        </Box>
        {rows.length > room && <Text dimColor>{rows.length - room} more: /dynamia-memory-panel needs a taller pane, or ms-workspace memory list</Text>}
        <Box flexDirection="column">
          <Text bold>Add a note</Text>
          <Select key="note-type" label="type" options={TYPES.map(t => ({ value: t, label: t }))} value={d.type} onSelect={() => {}} />
          <Input key="note" label="note" placeholder="Why we chose X over Y" value={d.text} onSubmit={() => {}} submitLabel="add" />
          <Button key="note-add" label="Add" variant="primary" onPress={() => {}} />
        </Box>
        {note !== '' && <Text color="yellow">{note}</Text>}
      </Box>
    )
  })
}
