# Import and Organize

MM separates two workflows:

- **Indexing**: read existing files and record metadata.
- **Importing**: copy or move new files into the library folder.

## Import from a camera folder

```bash
mm import ~/DCIM
```

By default MM copies files. Add `--move` only when you want the source files
removed after a successful import.

```bash
mm import ~/DCIM --move
```

## Configure the destination layout

The import template controls where new files go inside the library.

```bash
mm config import_template "{year}/{year}-{month:02d}-{day:02d}/{hour:02d}{minute:02d}{second:02d}{ext}"
```

Common fields include date parts, camera name, media type, and file extension.

## Keep the database aligned with disk

If files are moved or deleted outside MM, run:

```bash
mm db sync ~/Photos
```

For a large library, increase workers:

```bash
mm db sync ~/Photos -j 8
```

## Find media by tag

```bash
mm search --tag landscape --tag nature
```
