# MM

MM is a local-first media library manager for photos, videos, and audio. It helps
you scan existing folders, import new files safely, organize media with tags and
albums, and browse everything from a web UI.

[Homepage and docs](https://hspk.github.io/mm/) · [PyPI](https://pypi.org/project/litemm/) · [Issues](https://github.com/HSPK/mm/issues)

[![PyPI](https://img.shields.io/pypi/v/litemm)](https://pypi.org/project/litemm/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue)](LICENSE)

## What you can do with MM

- Browse your local media collection in a web UI.
- Import photos and videos into predictable folders.
- Keep your original files untouched while indexing.
- Search and organize media with tags, albums, ratings, places, and dates.
- Start locally and move to a server-backed setup later if you need it.

## Install

Install the recommended media tools first:

macOS:

```bash
brew install exiftool ffmpeg
```

Ubuntu / Debian:

```bash
sudo apt install libimage-exiftool-perl ffmpeg
```

Then install MM:

```bash
pipx install litemm
```

## First run

Create a library for your media folder:

```bash
mm init ~/Photos
```

Start the web UI:

```bash
mm server
```

Open `http://localhost:8000` in your browser.

## Import new media

Copy new media into the library:

```bash
mm import ~/Downloads/Camera
```

If files changed on disk and MM should update its index:

```bash
mm db sync ~/Photos
```

## Learn more

The full documentation site includes:

- [Getting Started](https://hspk.github.io/mm/tutorials/getting-started/)
- [Import and Organize](https://hspk.github.io/mm/tutorials/import-and-organize/)
- [Web UI Guide](https://hspk.github.io/mm/tutorials/web-ui/)
- [Architecture notes](https://hspk.github.io/mm/architecture/overview/)
- [Developer setup](https://hspk.github.io/mm/development/setup/)

## Native iOS / macOS app

A SwiftUI client targeting iOS 17+ and macOS 14+ lives under [`ios/`](./ios).
It's a separate Swift codebase that talks to this server over HTTP and
shares no code with the web frontend (by design — native UI). See
[ios/README.md](./ios/README.md) for build instructions.

## License

MM is available under the [PolyForm Noncommercial License 1.0.0](LICENSE).
Commercial use requires separate permission.
