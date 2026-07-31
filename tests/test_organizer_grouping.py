from __future__ import annotations

from pathlib import Path

from mm.music.grouping import music_album_key_from_path
from mm.organizer.filename import ParsedMediaFile
from mm.server.organizer_music_groups import album_item_from_tracks, music_album_groups
from mm.server.organizer_schemas import OrganizerItem


def _track(path: str) -> OrganizerItem:
    return OrganizerItem(path=path, media_type="track", title="x")


def test_multidisc_album_groups_as_one_across_roman_and_cd_folders():
    base = "/m/Artist/Album"
    items = [
        _track(f"{base}/Disc I/01. a.flac"),
        _track(f"{base}/Disc II/01. b.flac"),
        _track(f"{base}/CD1/02. c.flac"),
        _track(f"{base}/CD2/02. d.flac"),
    ]
    groups = music_album_groups(items)
    assert len(groups) == 1
    assert len(next(iter(groups.values()))) == 4


def test_music_album_key_ignores_disc_folder():
    base = Path("/m/Artist/Album")
    assert music_album_key_from_path(base / "Disc I" / "01.flac") == music_album_key_from_path(
        base / "Disc II" / "01.flac"
    )
    assert music_album_key_from_path(base / "CD1" / "01.flac") == music_album_key_from_path(
        base / "01.flac"
    )


def test_multidisc_album_item_targets_shared_album_root():
    album = Path("/m/Artist/Album")
    item = album_item_from_tracks(
        [
            ParsedMediaFile(
                path=album / "Disc I" / "01.flac",
                media_type="track",
                title="One",
            ),
            ParsedMediaFile(
                path=album / "Disc II" / "02.flac",
                media_type="track",
                title="Two",
            ),
        ]
    )

    assert item.path.parent == album


def test_separate_albums_stay_separate():
    items = [
        _track("/m/Artist/Album A/01.flac"),
        _track("/m/Artist/Album B/01.flac"),
    ]
    assert len(music_album_groups(items)) == 2
