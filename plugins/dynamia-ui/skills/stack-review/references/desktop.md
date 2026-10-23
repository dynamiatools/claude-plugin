# Desktop targets

| Situation | Pick | Why | Watch out for |
|---|---|---|---|
| Web app that also needs files, tray, offline, system access; size matters | **Tauri 2** | Uses the OS webview (minimal apps can be under 1 MB); frontend is any web stack; logic in Rust, with Swift and Kotlin for plugins | Different webview per OS, so test each; Rust skills for native logic |
| Need Chromium everywhere, Node APIs, mature ecosystem, auto-update tooling | **Electron** | Same browser engine on every OS, huge ecosystem | Large installers and memory use; you must track Chromium security updates |
| Just a web app on the desktop | **PWA install** | Zero packaging | Few OS integrations |
| Heavy native UI or performance | Native (WinUI, SwiftUI/AppKit, Qt/GTK) or Flutter desktop | Best fit | Separate codebases (except Flutter, Qt) |
| Java shop, internal tools | JavaFX or the web app in a browser | Fits the team | Poor fit for modern web UX |

Deployment checklist: code signing and notarization (macOS), installers per OS, auto-update channel, crash reporting, security (no remote code in a privileged context, a strict content security policy, minimal native permissions).
