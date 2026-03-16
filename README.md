<div align="center">

# 📸 MM — Universal Organizer for Media

**A self-hosted, AI-powered media library manager for photos, videos, and audio.**

Scan, tag, search, deduplicate, and browse your media collection with a beautiful web UI.

[![GitHub Stars](https://img.shields.io/github/stars/HSPK/mm?style=for-the-badge&logo=github&color=f4c542)](https://github.com/HSPK/mm/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/HSPK/mm?style=for-the-badge&logo=github&color=blue)](https://github.com/HSPK/mm/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/HSPK/mm?style=for-the-badge&logo=github&color=orange)](https://github.com/HSPK/mm/issues)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/HSPK/mm?style=for-the-badge&logo=github)](https://github.com/HSPK/mm/commits)
[![GitHub License](https://img.shields.io/github/license/HSPK/mm?style=for-the-badge)](https://github.com/HSPK/mm/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)

---

[Features](#-features) · [Quick Start](#-quick-start) · [Installation](#-installation) · [Usage](#-usage) · [Web UI](#-web-ui) · [API](#-api) · [Contributing](#-contributing)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🔍 Smart Scanning
- Recursive media discovery with parallel processing
- SHA-256 hashing for integrity & deduplication
- EXIF, video, and audio metadata extraction
- Support for RAW, HEIC/HEIF, and 30+ formats

</td>
<td width="50%">

### 🤖 AI-Powered
- CLIP-based image embeddings (ViT-B-32)
- Natural language image search ("sunset over ocean")
- Zero-shot auto-tagging (~36 categories)
- Visual similarity search

</td>
</tr>
<tr>
<td>

### 🌍 Offline Geocoding
- Reverse geocoding from GPS EXIF data
- GeoNames cities15000 dataset (no API keys needed)
- Chinese province/city name support
- Chinese lunar & solar festival detection

</td>
<td>

### 🖼️ Beautiful Web UI
- Responsive gallery with justified layout
- Pinch-to-zoom thumbnail resizing
- Infinite scroll with date grouping
- Detail panel with full metadata & map

</td>
</tr>
<tr>
<td>

### 📁 Library Management
- Manual & smart albums (auto-generated)
- Star ratings, tags, batch operations
- Template-based file import & organization
- Multi-library support with runtime switching

</td>
<td>

### ⚡ Performance
- SQLite-backed (zero config, portable)
- WebP thumbnail caching (4 sizes) with ETag
- Async API server (FastAPI + Uvicorn)
- Background CLIP processing

</td>
</tr>
</table>

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Web UI (React)                        │
│         React 19 · TailwindCSS · Zustand · Vite              │
└──────────────────┬───────────────────────────────────────────┘
                   │ REST API
┌──────────────────▼───────────────────────────────────────────┐
│                    FastAPI Server                             │
│     Auth · Media · Albums · Smart Albums · Tags · Stats      │
└──────────────────┬───────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────┐
│                    Core Engines                               │
│  Scanner · Metadata · Embeddings · Tagger · Geocoding · ...  │
└──────────────────┬───────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────┐
│               SQLite (Peewee ORM / aiosqlite)                │
│         Media · Metadata · Tags · Embeddings · Albums        │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
# Install with uv (recommended)
uv pip install -e .

# Create a new library (interactive)
mm init ~/Photos

# Start the web server
mm server
# → Open http://localhost:8000
```

## 📦 Installation

### Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip
- **exiftool** — for EXIF metadata extraction
- **ffmpeg** / **ffprobe** — for video/audio metadata & thumbnails

```bash
# macOS
brew install exiftool ffmpeg

# Ubuntu / Debian
sudo apt install libimage-exiftool-perl ffmpeg
```

### Install mm

```bash
# Clone the repository
git clone https://github.com/HSPK/mm.git
cd mm

# Install with uv
uv pip install -e .

# (Optional) Install CLIP support for AI features
uv pip install -e ".[clip]"
```

### Build the Frontend

```bash
cd web
npm install
npm run build
cd ..
```

## 📖 Usage

### CLI Commands

| Command | Description |
|---|---|
| `mm init [dir]` | Create or open a media library (interactive setup) |
| `mm server [dir]` | Start the web UI server |
| `mm import <source>` | Import media files into the active library |
| `mm search` | Search by text, image, or tags (requires CLIP) |
| `mm dedup` | Find and remove duplicate media files by hash |
| `mm info <file>` | Show detailed file metadata |
| `mm config [key] [value]` | Get or set library config values |
| `mm geo update` | Offline reverse geocode GPS-tagged media |
| `mm db list` | List all registered databases |
| `mm db set <n>` | Switch the active database |
| `mm db add <path>` | Register an existing database file |
| `mm db rm <n>` | Unregister a database (optionally delete) |
| `mm db stats` | Show detailed library statistics |
| `mm db clean` | Remove entries for files no longer on disk |
| `mm db sync <dir>` | Clean stale entries and re-scan changed files |

### Library Setup

```bash
# Create a new library interactively
mm init ~/Photos

# View all config values
mm config

# Set the import template
mm config import_template "{year}/{year}-{month:02d}-{day:02d}/{original_name}{ext}"

# Sync database with disk (remove stale + re-scan)
mm db sync ~/Photos

# Parallel sync with 8 workers
mm db sync ~/Photos -j 8
```

### Searching

```bash
# Semantic search by text (requires CLIP)
mm search --text "sunset at the beach"

# Search by image similarity
mm search --image ~/Photos/reference.jpg --top-k 20

# Filter by tags
mm search --tag landscape --tag nature
```

### Deduplication

```bash
# Find and remove duplicate media files (by hash)
mm dedup
```

### Importing & Organizing

```bash
# Import from SD card (copies into library using configured template)
mm import ~/DCIM

# Move instead of copy
mm import ~/DCIM --move
```

### Web Server

```bash
# Start on default port (8000)
mm server

# Specify library directory
mm server ~/Photos

# Custom host and port
mm server -h 0.0.0.0 -p 9000

# Development mode with auto-reload
mm server --reload
```

## 🌐 Web UI

The web interface provides a full-featured media browser:

- **Library** — Browse all media with infinite scroll, date grouping, and adjustable thumbnail sizes
- **Albums** — Smart albums auto-generated by tag, camera, year, festival, and location
- **Search** — Quick filtering and semantic search
- **Detail View** — Full metadata, EXIF info, location, tags, and star ratings
- **Batch Operations** — Multi-select for bulk tagging, rating, and deletion
- **Settings** — Theme switching (light/dark), library management
- **Auth** — User accounts with token-based authentication

## 🔌 API

mm exposes a comprehensive REST API at `/api/`:

| Endpoint | Description |
|---|---|
| `/api/auth/*` | Authentication (login, setup, logout) |
| `/api/media` | Media CRUD, thumbnails, file streaming |
| `/api/batch/*` | Bulk operations (tags, ratings, delete) |
| `/api/albums/*` | Album management |
| `/api/smart-albums/*` | Smart album definitions & resolution |
| `/api/tags` | Tag CRUD with usage counts |
| `/api/stats` | Library statistics & timeline |
| `/api/library` | Multi-library switching |
| `/api/users` | User management (admin) |

Interactive API docs available at **`/docs`** (Swagger UI) when the server is running.

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Backend** | Python 3.10+, FastAPI, Peewee ORM, SQLite |
| **AI/ML** | OpenCLIP (ViT-B-32), PyTorch |
| **Frontend** | React 19, TypeScript, TailwindCSS, Vite |
| **State** | Zustand |
| **UI Kit** | shadcn/ui, Radix UI, Lucide Icons |
| **Media** | Pillow, pillow-heif, rawpy, exiftool, ffmpeg |
| **Geocoding** | GeoNames (offline), lunar-python |

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

```bash
# Clone and install in dev mode
git clone https://github.com/HSPK/mm.git
cd mm
uv pip install -e ".[clip]"

# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Start frontend dev server
cd web && npm install && npm run dev
```

Please open an issue first to discuss what you would like to change.

## 📄 License

This project is open source. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

**If you find mm useful, please consider giving it a ⭐!**

[![Star History Chart](https://api.star-history.com/svg?repos=HSPK/mm&type=Date)](https://star-history.com/#HSPK/mm&Date)

</div>