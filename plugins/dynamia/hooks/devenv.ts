import type { DevVar } from '../types'

export type Listing = { repos: string[]; vars: DevVar[] }

// What `ms-workspace dev-env list --json` printed, or null when it was not that (an error text, a missing workspace).
export function parseListing(stdout: string): Listing | null {
  try {
    const data = JSON.parse(stdout) as Partial<Listing>
    if (!Array.isArray(data.repos) || !Array.isArray(data.vars)) return null

    return { repos: data.repos, vars: data.vars }
  } catch {
    return null
  }
}

// `NAME=value [repo]` as typed after /dev-env; the repo is the last word when it is a known repo.
export function parseAdd(args: string, repos: readonly string[]): { name: string; value: string; repo: string } | null {
  const eq = args.indexOf('=')
  if (eq < 1) return null
  const name = args.slice(0, eq).trim()
  let value = args.slice(eq + 1).trim()
  let repo = ''
  const last = value.split(/\s+/).pop() ?? ''
  if (last && repos.includes(last) && value.includes(' ')) {
    repo = last
    value = value.slice(0, value.length - last.length).trim()
  }

  return { name, value, repo }
}

export function addArgv(root: string, d: { name: string; value: string; repo: string }): string[] {
  return [`${root}/bin/ms-workspace`, 'dev-env', 'add', `${d.name}=${d.value}`, ...(d.repo ? ['--repo', d.repo] : [])]
}

export function rmArgv(root: string, name: string, scope: string): string[] {
  return [`${root}/bin/ms-workspace`, 'dev-env', 'rm', name, ...(scope && scope !== 'all' ? ['--repo', scope] : [])]
}

export function listArgv(root: string): string[] {
  return [`${root}/bin/ms-workspace`, 'dev-env', 'list', '--json']
}
