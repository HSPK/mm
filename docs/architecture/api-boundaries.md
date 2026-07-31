# API Boundary Rules

MM groups HTTP routes by the capability exposed to clients, not by the Python
module, database table, or ingestion process that currently supplies the data.

## Data plane and control plane

The data plane serves stable resources used by normal application screens:

```text
/api/media      Photos and general media
/api/videos     Video catalog
/api/music      Albums, artists, tracks, lyrics, and music artwork
/api/player     Playback sources, streams, and playback state
```

The control plane performs administrative or destructive workflows:

```text
/api/organizer  Scan, inspect, match, rename, and write metadata/artwork/lyrics
/api/import     Plan and apply imports
/api/jobs       Start, inspect, retry, and cancel background work
```

It is valid for `/api/music` to read rows originally created by Organizer.
Storage ownership does not determine public API ownership.

## Boundary criteria

A route belongs in a data-plane domain when all of the following are true:

- A normal browsing or playback screen calls it.
- It returns stable IDs and consumer-oriented DTOs.
- It is read-only or updates user state local to that domain.
- Its permission level matches the rest of the domain.

A route belongs in Organizer when any of the following are true:

- It accepts filesystem paths or scan roots.
- It discovers, repairs, matches, renames, or rewrites files.
- It writes NFO, artwork, lyrics, or external metadata.
- It starts or controls an ingestion workflow.

Read and write operations for the same underlying resource may intentionally
live in different domains. For example:

```text
GET  /api/music/tracks/{id}/lyrics   # consumer read
POST /api/organizer/lyrics/search    # organization workflow
POST /api/organizer/lyrics/apply     # filesystem write
```

## Dependency direction

Routers depend on domain services, and domain services depend on persistence:

```text
routers/music.py -> music_catalog.py -> OrganizerMediaModel
routers/organizer.py -> organizer workflows -> persistence/filesystem
```

Consumer routers must not import Organizer router functions. Frontend consumer
pages use `musicRepo`, `videoRepo`, or `mediaRepo`; only organization screens use
`organizerRepo`.

## Review checklist

Before adding an endpoint:

1. Identify the primary client and user capability.
2. Classify it as data-plane read, user-state update, or control-plane workflow.
3. Confirm every route in the proposed prefix has compatible permissions.
4. Return internal IDs; never place filesystem paths in consumer URLs or DTOs.
5. Ask whether renaming the backing module/table should change the URL. If yes,
   the route is coupled to implementation details.
6. Add a boundary test that verifies the intended prefix and rejects the wrong
   namespace.
7. Use cursor pagination when records may be inserted while clients paginate;
   offset pagination is acceptable only for bounded snapshot-backed catalogs.
