---
name: ms-code-tunnel
description: Launches @dynamia-tools/remote-code-viewer --tunnel in the background against the current repo, kills any previous tunnel to avoid zombies, waits for the Cloudflare tunnel URL and returns it as a clickable link in the chat. Use when the user asks to open/launch the remote viewer, view the repo remotely, or share a tunnel to the current code.
---

# ms-code-tunnel

Starts the remote code viewer (`@dynamia-tools/remote-code-viewer --tunnel`)
for the current repo in the background and returns the Cloudflare tunnel URL
as a clickable link in the chat (never leave it only in logs).

## Steps

1. **Pick the target directory**: the repo the session is working on (the
   current working directory unless the user says otherwise).

2. **Run the bundled script** with that directory:
   ```bash
   bash ~/.claude/skills/ms-code-tunnel/scripts/run-tunnel.sh "<repo-dir>"
   ```
   The script:
   - Kills any previous viewer (by saved PID, plus `pkill -f` as a safety net).
   - Starts `npx @dynamia-tools/remote-code-viewer --tunnel` fully detached.
   - Waits up to ~60s (`REMOTE_VIEWER_TIMEOUT`) for a `https://*.trycloudflare.com` URL.
   - Prints **only the URL** to stdout on success, or the full log to stderr on failure/timeout.

   Do not use `run_in_background`: the script returns as soon as it has the URL.

3. **Report to the user**:
   - On success, show the URL as a markdown link, e.g.
     `🔗 Tunnel active: [https://x.trycloudflare.com](https://x.trycloudflare.com)`
   - On failure, show the relevant log verbatim and never invent a URL.

## Notes

- Log: `~/.cache/remote-viewer/tunnel.log`; active PID: `~/.cache/remote-viewer/tunnel.pid`.
- Only one instance is kept alive: each run kills the previous one.
- Never run the `npx ...` command directly; the script prevents orphan processes.
