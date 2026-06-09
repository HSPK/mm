# MM — iOS & macOS app

SwiftUI client for the MM media server. Shares one Swift source tree across
iOS 17+ and macOS 14+.

## Build prerequisites

- macOS 14+ with **Xcode 15+**
- [xcodegen](https://github.com/yonaskolb/XcodeGen) — `brew install xcodegen`
- A reachable MM server (the FastAPI app — see the root `README.md`)

## Generate the Xcode project

```bash
cd ios
xcodegen generate
open MM.xcodeproj
```

`project.yml` is the single source of truth. Don't edit `MM.xcodeproj`
directly — regenerate it instead.

## Configure the server URL

The app defaults to `http://localhost:8000/api`. To override:

1. In Xcode, **Edit Scheme → Run → Arguments → Environment Variables**
2. Add `MM_API_BASE_URL` = your server URL (e.g. `https://photos.example.com/api`)

You can also tap the URL field on the login screen to change it at runtime;
it's persisted to `UserDefaults`.

## Build targets

- **MM-iOS** — iPhone + iPad
- **MM-macOS** — native macOS app (sandbox-enabled, network client entitlement)

Both targets share **all** Swift sources under `MM/`. Use
`#if os(iOS)` / `#if os(macOS)` only where strictly necessary
(`MMApp.swift` and `MediaDetailView.swift` already do this for
window-management and toolbar differences).

## Project layout

```
ios/
├── project.yml           xcodegen config
├── README.md             this file
└── MM/
    ├── App/              entry point + root view
    ├── Models/           Codable structs matching FastAPI
    ├── Networking/       APIClient + repositories + Keychain
    ├── Stores/           @Observable app state
    ├── Views/            SwiftUI screens + components
    └── Lib/              Config, URL builders, helpers
```

## What's wired in this MVP

- Login → token stored in Keychain
- Paginated photo grid (LazyVGrid, infinite scroll)
- Full-screen photo / video viewer with swipe nav
- Share / Open original via system share sheet
- Settings: API base URL, logout, current user info

## What's not (yet)

- Albums + Smart Albums
- Metadata editing (rating, tags, EXIF edit)
- Trash, batch operations
- B站-style touch gestures (the web client has them, native uses standard AVKit
  controls for now)

These are wired on the server side and on the web client; porting them is a
matter of adding the repository methods, models, and views. Each web `api/*`
module maps 1:1 to a Swift `Networking/*Repository.swift` file.

## Releasing

1. Bump `MARKETING_VERSION` and `CURRENT_PROJECT_VERSION` in `project.yml`
2. `xcodegen generate`
3. In Xcode → **Product → Archive**
4. Upload via Organizer to TestFlight / App Store / Mac App Store

You'll need an Apple Developer account and to set `DEVELOPMENT_TEAM` to your
team ID in `project.yml` (the build setting can also be set per-scheme).

## License

Inherits the project root's PolyForm Noncommercial 1.0.0 license.
