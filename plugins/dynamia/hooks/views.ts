export type Note = { type: string; batch: string; title: string; name: string }

// A line of `ms-workspace memory list`: "type batch title  (name)"; anything else (like "(no notes)") is dropped.
export function parseNotes(stdout: string): Note[] {
  const notes: Note[] = []
  for (const line of stdout.split('\n')) {
    const m = /^(\S+)\s+(\S+)\s+(.*?)\s+\(([^()\s]+)\)$/.exec(line.trim())
    if (m) notes.push({ type: m[1]!, batch: m[2] === '-' ? '' : m[2]!, title: m[3]!, name: m[4]! })
  }

  return notes
}

export function logArgv(root: string, limit: number): string[] {
  return [`${root}/bin/ms-workspace`, 'log', '-n', String(limit)]
}

export function notesArgv(root: string): string[] {
  return [`${root}/bin/ms-workspace`, 'memory', 'list', '-n', '200']
}

export function forgetArgv(root: string, name: string): string[] {
  return [`${root}/bin/ms-workspace`, 'memory', 'forget', name]
}

export function addNoteArgv(root: string, type: string, text: string): string[] {
  return [`${root}/bin/ms-workspace`, 'memory', 'add', '--type', type, text]
}
