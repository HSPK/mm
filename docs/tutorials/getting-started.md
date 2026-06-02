# Getting Started

This guide is for people who want to organize a local photo or video folder and
open it in the MM web UI.

## 1. Install media tools

MM can index files without these tools, but they are recommended for complete
metadata and thumbnails.

=== "macOS"

    ```bash
    brew install exiftool ffmpeg
    ```

=== "Ubuntu / Debian"

    ```bash
    sudo apt install libimage-exiftool-perl ffmpeg
    ```

## 2. Install MM

```bash
pipx install litemm
```

If you do not use `pipx`, install with your preferred Python package manager.

## 3. Create a library

Choose the folder that contains your media. MM creates a small database for the
library and keeps your original files untouched.

```bash
mm init ~/Photos
```

## 4. Open the web UI

```bash
mm server
```

Open `http://localhost:8000` in your browser.

## 5. Add new media later

Use `mm import` when you want MM to copy new files into the library using the
configured folder template.

```bash
mm import ~/Downloads/Camera
```

Use `mm db sync` when files already changed on disk and the database should catch
up.

```bash
mm db sync ~/Photos
```
