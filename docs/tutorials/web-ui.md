# Web UI Guide

Start the server:

```bash
mm server
```

Then open `http://localhost:8000`.

## Library

The library view is the main place to browse media. It supports thumbnails,
infinite scrolling, date grouping, and detail panels.

## Albums and smart albums

MM can organize media by tags, cameras, years, festivals, and places. These
collections help you browse without manually building every album.

## Ratings and tags

Use tags and star ratings to keep track of favorites, projects, trips, and
cleanup work.

## Multiple libraries

Register existing libraries with:

```bash
mm db add /path/to/mm.db
```

For a server-backed library, register a PostgreSQL URL:

```bash
mm db add postgresql://user:pass@host:5432/mm
```

Switch libraries with:

```bash
mm db list
mm db set 2
```
