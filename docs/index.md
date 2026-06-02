# MM

Organize your media without giving up control.

MM is a local-first media library manager for photos, videos, and audio. It helps
you index existing folders, import new files safely, organize media with tags and
albums, and browse your library from a web UI.

## Start here

```bash
pipx install litemm
mm init ~/Photos
mm server
```

Open `http://localhost:8000` in your browser.

## What MM is good for

- Browsing a local media collection from a web interface.
- Importing photos and videos into predictable folders.
- Keeping original files untouched while indexing.
- Organizing media with tags, albums, ratings, dates, and places.
- Starting with SQLite and moving to PostgreSQL later if needed.

## Read the guides

- [Getting Started](tutorials/getting-started.md)
- [Import and Organize](tutorials/import-and-organize.md)
- [Web UI Guide](tutorials/web-ui.md)

Technical notes are available under [Architecture](architecture/overview.md) and
[Development](development/setup.md).

## License

MM is available under the PolyForm Noncommercial License 1.0.0. Commercial use
requires separate permission.
