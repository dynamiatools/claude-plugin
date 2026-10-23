# Mobile targets

Decide with these questions: does it need heavy native features, 60 fps animation or platform-exact look? Does the team already build the web app? Is there one codebase or two?

| Situation | Pick | Why | Watch out for |
|---|---|---|---|
| Existing or new web app, needs store distribution and common device features (camera, files, push, geolocation) | **Capacitor** wrapping the Vue + Tailwind app | Web-first native runtime for iOS and Android; plugin API reaches native SDKs; web code stays standard | It is a webview: heavy animation and long lists need care; follow mobile UX rules in `dynamia-ui:ux-review` |
| Same, and you want ready-made mobile components | **Ionic Framework (Vue)** + Capacitor | Components that follow iOS and Android styles | Ties the look to Ionic; adapt tokens to your design system |
| Web app only, no store | **PWA** (see `dynamia-ui:offline-review`) | No review process, one deploy | iOS limits (install flow, storage eviction, push support varies) |
| One codebase, near-native feel, team can learn a new stack | Flutter or React Native | Own rendering or native views; good performance | New skills; web code is not reused |
| Best possible platform fit, device-heavy (AR, Bluetooth LE, background work, widgets) | Native: SwiftUI (iOS), Kotlin + Jetpack Compose (Android) | Full platform access | Two codebases and two teams |
| Desktop and mobile from web code, Rust acceptable | Tauri 2 (it also targets iOS and Android) | Small apps, OS webview | Mobile side is younger than Capacitor's: prototype the device features you need first |

Rules of thumb
- Start hybrid if the product is forms, lists, content and dashboards. Go native when the device is the product.
- Do not duplicate: one web codebase plus Capacitor beats a separate "mobile site".
- Plan store requirements early (privacy labels, review times, account deletion, signing).
- Whatever the choice, test on real devices and the oldest OS version you support.
