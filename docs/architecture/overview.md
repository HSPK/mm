# Design Overview

This section is for technical readers who want to understand how MM is built.
Most users can start with the tutorials instead.

## Goals

MM is designed around a few constraints:

- Keep the default setup small and local.
- Never modify original media files during indexing.
- Keep CLI workflows scriptable.
- Serve the web UI from the Python package.
- Allow SQLite for portability and PostgreSQL for server deployments.

## Main components

```text
CLI / Web UI
    |
FastAPI server and command workflows
    |
Media scanner · importer · metadata extractor · thumbnails · tags · geocoding
    |
DB client namespaces
    |
SQLite or PostgreSQL
```

## Data flow

1. The scanner walks media folders and computes file metadata.
2. The metadata extractor reads EXIF, video, audio, image, and GPS fields.
3. The database stores media rows, metadata rows, tags, albums, smart albums, and
   library configuration.
4. The server reads the same database and streams media or thumbnails to the web UI.

## Storage model

MM stores references to local media files and uses the database as an index. This
keeps imports, sync, repair, and cleanup operations explicit rather than hidden
behind background daemons.

## Database backends

SQLite is the default because it is portable and requires no server. PostgreSQL
URLs are supported for deployments where a central database is preferred.
