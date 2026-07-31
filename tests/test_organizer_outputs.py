from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from mm.config import OrganizerTemplates
from mm.db.models import OrganizerMediaModel, OrganizerRenameLogModel
from mm.db.sync_client import DBClient
from mm.organizer.artwork import plan_artwork
from mm.organizer.filename import parse_media_filename
from mm.organizer.metadata_policy import local_track_candidate
from mm.organizer.nfo import build_nfo, write_nfo
from mm.organizer.rename import RenameOperation, apply_rename_plan, plan_renames
from mm.organizer.scrape_writer import (
    _prefer_local_title,
    album_track_metadata_by_path,
    write_album_metadata,
    write_external_track_metadata,
    write_standard_metadata,
)
from mm.organizer.scrapers import ScrapeCandidate
from mm.organizer.templates import render_media_path
from mm.server.organizer_metadata import OrganizerScanContext, _read_local_metadata
from mm.server.organizer_persistence import persist_scan_items
from mm.server.organizer_rename_jobs import (
    refresh_after_rename,
    rename_complete_message,
    rename_complete_title,
    rename_log_entries,
    undo_rename_batch,
)
from mm.server.routers.organizer import _item_from_parsed, _light_item_from_parsed


def must_parse(path: Path):
    parsed = parse_media_filename(path)
    assert parsed is not None
    return parsed


def test_plan_movie_rename(tmp_path: Path):
    src = tmp_path / "Inception.2010.1080p.mkv"
    src.write_text("")
    parsed = must_parse(src)

    plan = plan_renames([parsed], root=tmp_path, templates=OrganizerTemplates())

    assert len(plan.operations) == 1
    op = plan.operations[0]
    assert op.status == "ready"
    assert op.target == tmp_path / "Inception (2010)" / "Inception (2010).mkv"


def test_movie_rename_includes_sidecars(tmp_path: Path):
    src = tmp_path / "Inception.2010.1080p.mkv"
    src.write_text("video")
    src.with_suffix(".nfo").write_text("nfo")
    (tmp_path / "Inception.2010.1080p.en.srt").write_text("subs")
    (tmp_path / "poster.jpg").write_text("poster")
    parsed = must_parse(src)

    plan = plan_renames([parsed], root=tmp_path, templates=OrganizerTemplates())

    targets = {operation.target.relative_to(tmp_path) for operation in plan.operations}
    assert targets == {
        Path("Inception (2010)/Inception (2010).mkv"),
        Path("Inception (2010)/Inception (2010).nfo"),
        Path("Inception (2010)/Inception (2010).en.srt"),
        Path("Inception (2010)/poster.jpg"),
    }

    assert apply_rename_plan(plan) == 4
    assert (tmp_path / "Inception (2010)" / "Inception (2010).mkv").read_text() == "video"
    assert (tmp_path / "Inception (2010)" / "Inception (2010).nfo").read_text() == "nfo"
    assert (tmp_path / "Inception (2010)" / "Inception (2010).en.srt").read_text() == "subs"
    assert (tmp_path / "Inception (2010)" / "poster.jpg").read_text() == "poster"


def test_tv_rename_includes_episode_show_and_season_sidecars(tmp_path: Path):
    show = tmp_path / "Severance"
    season = show / "Season 02"
    season.mkdir(parents=True)
    src = season / "Hello Ms Cobel S02E01.mkv"
    src.write_text("episode")
    src.with_suffix(".nfo").write_text("episode nfo")
    (season / "Hello Ms Cobel S02E01.en.srt").write_text("subs")
    (show / "tvshow.nfo").write_text("show nfo")
    (show / "season02-poster.jpg").write_text("season poster")
    parsed = must_parse(src)

    out = tmp_path / "organized"
    plan = plan_renames([parsed], root=out, templates=OrganizerTemplates())
    targets = {operation.target.relative_to(out) for operation in plan.operations}

    assert targets == {
        Path("Severance/Season 02/Severance - S02E01.mkv"),
        Path("Severance/Season 02/Severance - S02E01.nfo"),
        Path("Severance/Season 02/Severance - S02E01.en.srt"),
        Path("Severance/tvshow.nfo"),
        Path("Severance/season02-poster.jpg"),
    }
    assert apply_rename_plan(plan) == 5
    assert (out / "Severance" / "Season 02" / "Severance - S02E01.mkv").read_text() == "episode"
    assert (out / "Severance" / "Season 02" / "Severance - S02E01.nfo").read_text() == "episode nfo"
    assert (out / "Severance" / "Season 02" / "Severance - S02E01.en.srt").read_text() == "subs"
    assert (out / "Severance" / "tvshow.nfo").read_text() == "show nfo"
    assert (out / "Severance" / "season02-poster.jpg").read_text() == "season poster"
    assert not show.exists()


def test_apply_track_rename(tmp_path: Path):
    src = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.flac"
    src.parent.mkdir(parents=True)
    src.write_text("audio")
    parsed = must_parse(src)

    out = tmp_path / "organized"
    plan = plan_renames([parsed], root=out, templates=OrganizerTemplates())
    assert apply_rename_plan(plan) == 1

    assert (out / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.flac").read_text() == "audio"
    assert not src.exists()


def test_track_template_supports_disk_folder_alias():
    parsed = must_parse(Path("Radiohead/1997 - OK Computer/CD2/01 - Airbag.flac"))

    rendered = render_media_path(parsed, OrganizerTemplates())

    assert rendered.relative_path == Path("Radiohead/1997 - OK Computer/CD2/01 - Airbag.flac")


def test_rename_uses_provided_album_artist_for_featured_track_artists(tmp_path: Path):
    album = tmp_path / "Music" / "2010 - 跨时代"
    album.mkdir(parents=True)
    first = album / "01. 周杰伦 - 烟花易冷.flac"
    featured = album / "02. 周杰伦&浪花兄弟 - 免费教学录影带.flac"
    first.write_text("one")
    featured.write_text("two")
    parsed = [
        must_parse(first),
        must_parse(featured),
    ]
    parsed = [replace(item, artist="周杰伦") for item in parsed]

    plan = plan_renames(parsed, root=tmp_path / "out", templates=OrganizerTemplates())

    targets = {operation.target.relative_to(tmp_path / "out") for operation in plan.operations}
    assert targets == {
        Path("周杰伦/2010 - 跨时代/01 - 烟花易冷.flac"),
        Path("周杰伦/2010 - 跨时代/02 - 免费教学录影带.flac"),
    }


def test_apply_album_rename_dedupes_sidecars_and_removes_empty_folders(tmp_path: Path):
    album = tmp_path / "Radiohead" / "1997 - OK Computer"
    album.mkdir(parents=True)
    first = album / "01 - Airbag.flac"
    second = album / "02 - Paranoid Android.flac"
    first.write_text("one")
    second.write_text("two")
    (album / "album.nfo").write_text("album")
    (album / "folder.jpg").write_text("cover")
    (album / "OK Computer.cue").write_text("cue")
    tech_info = album / "tech.info"
    tech_info.mkdir()
    (tech_info / "spectrum.txt").write_text("info")

    parsed = [must_parse(first), must_parse(second)]
    out = tmp_path / "organized"
    plan = plan_renames(parsed, root=out, templates=OrganizerTemplates())

    targets = [operation.target.relative_to(out) for operation in plan.actionable]
    assert targets.count(Path("Radiohead/1997 - OK Computer/album.nfo")) == 1
    assert targets.count(Path("Radiohead/1997 - OK Computer/folder.jpg")) == 1
    assert targets.count(Path("Radiohead/1997 - OK Computer/OK Computer.cue")) == 1
    assert targets.count(Path("Radiohead/1997 - OK Computer/tech.info")) == 1

    assert apply_rename_plan(plan) == 6
    assert (out / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.flac").read_text() == "one"
    assert (
        out / "Radiohead" / "1997 - OK Computer" / "02 - Paranoid Android.flac"
    ).read_text() == "two"
    assert (out / "Radiohead" / "1997 - OK Computer" / "album.nfo").read_text() == "album"
    assert (out / "Radiohead" / "1997 - OK Computer" / "folder.jpg").read_text() == "cover"
    assert (out / "Radiohead" / "1997 - OK Computer" / "OK Computer.cue").read_text() == "cue"
    assert (
        out / "Radiohead" / "1997 - OK Computer" / "tech.info" / "spectrum.txt"
    ).read_text() == "info"
    assert not album.exists()


def test_refresh_after_rename_replaces_stale_target_row(tmp_path: Path, db: DBClient):
    source = tmp_path / "Coldplay" / "A Head Full Of Dreams" / "01. A Head Full Of Dreams.flac"
    target = (
        tmp_path / "Coldplay" / "2015 - A Head Full Of Dreams" / "01. A Head Full Of Dreams.flac"
    )
    source.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    source.write_text("audio")
    target.write_text("stale")
    context = OrganizerScanContext.create()
    source_item = _light_item_from_parsed(must_parse(source), context)
    target_item = _light_item_from_parsed(must_parse(target), context)
    db._run(persist_scan_items(db._client, [source_item, target_item], mark_missing=False))
    source_row = db._run(db._client.objects.get(OrganizerMediaModel, path=str(source.resolve())))

    db._run(
        refresh_after_rename(
            db._client,
            [must_parse(source)],
            [RenameOperation(source.resolve(), target.resolve(), "track", "ready")],
        )
    )

    rows = db._run(
        db._client.objects.fetchall(
            OrganizerMediaModel.select().where(
                OrganizerMediaModel.path.in_([str(source.resolve()), str(target.resolve())])
            )
        )
    )
    assert [(row.id, row.path) for row in rows] == [(source_row.id, str(target.resolve()))]


def test_rename_log_entries_count_full_batch(db: DBClient):
    batch_id = "batch-many"
    for index in range(30):
        db._run(
            db._client.objects.create(
                OrganizerRenameLogModel,
                batch_id=batch_id,
                source=f"/src/{index:02d}.flac",
                target=f"/dst/{index:02d}.flac",
                media_type="track",
                status="applied",
            )
        )

    entries = db._run(rename_log_entries(db._client, limit=1))

    assert len(entries) == 1
    assert entries[0].batch_id == batch_id
    assert entries[0].count == 30
    assert entries[0].status == "applied"


def test_undo_rename_batch_restores_db_and_removes_empty_target_dirs(tmp_path: Path, db: DBClient):
    source = tmp_path / "Radiohead" / "OK Computer" / "01 - Airbag.flac"
    target = tmp_path / "organized" / "Radiohead" / "OK Computer" / "01 - Airbag.flac"
    target.parent.mkdir(parents=True)
    target.write_text("audio")
    item = _light_item_from_parsed(must_parse(target), OrganizerScanContext.create())
    db._run(persist_scan_items(db._client, [item], mark_missing=False))
    db._run(
        db._client.objects.create(
            OrganizerRenameLogModel,
            batch_id="undo-batch",
            source=str(source.resolve()),
            target=str(target.resolve()),
            media_type="track",
            status="applied",
        )
    )

    result = db._run(undo_rename_batch(db._client, "undo-batch"))

    assert result.affected == 1
    assert source.read_text() == "audio"
    assert not target.exists()
    assert not target.parent.exists()
    rows = db._run(
        db._client.objects.fetchall(
            OrganizerMediaModel.select().where(
                OrganizerMediaModel.path.in_([str(source.resolve()), str(target.resolve())])
            )
        )
    )
    assert [(row.path, row.media_type) for row in rows] == [(str(source.resolve()), "track")]


def test_rename_complete_messages_are_user_facing():
    assert rename_complete_title(0) == "Nothing to rename"
    assert rename_complete_message(0) == "All selected files already match the target names."
    assert rename_complete_message(1) == "Renamed 1 file."
    assert rename_complete_message(2) == "Renamed 2 files."


def test_music_item_uses_track_nfo_for_display_fields(tmp_path: Path):
    src = (
        tmp_path
        / "Taylor Swift - Lover (2019) [FLAC 24-44]"
        / "01. Taylor Swift - I Forgot That You Existed.flac"
    )
    src.parent.mkdir(parents=True)
    src.write_text("audio")
    (src.parent / "02. Cruel Summer.flac").write_text("audio")
    src.with_suffix(".nfo").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<song>
  <title>I Forgot That You Existed</title>
  <artist>Taylor Swift</artist>
  <album>Lover</album>
  <year>2019</year>
</song>
""",
        encoding="utf-8",
    )

    item = _item_from_parsed(must_parse(src))

    assert item.title == "I Forgot That You Existed"
    assert item.artist == "Taylor Swift"
    assert item.album == "Lover"
    assert item.year == 2019
    assert item.metadata_title == "I Forgot That You Existed"
    assert "02. Cruel Summer.flac" not in {file.name for file in item.related_files}


def test_music_item_strips_artist_prefix_from_track_nfo_title(tmp_path: Path):
    src = (
        tmp_path
        / "Taylor Swift - Lover (2019)"
        / "01. Taylor Swift - I Forgot That You Existed.flac"
    )
    src.parent.mkdir(parents=True)
    src.write_text("audio")
    src.with_suffix(".nfo").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<song>
  <title>Taylor Swift I Forgot That You Existed</title>
  <artist>Taylor Swift</artist>
  <album>Lover</album>
</song>
""",
        encoding="utf-8",
    )

    item = _item_from_parsed(must_parse(src))

    assert item.title == "I Forgot That You Existed"
    assert item.metadata_title == "I Forgot That You Existed"


def test_music_item_prefers_album_nfo_album_over_track_nfo_album(tmp_path: Path):
    src = tmp_path / "Coldplay" / "2003 - A Rush Of B-Sides To Your Head" / "03. Such A Rush.flac"
    src.parent.mkdir(parents=True)
    src.write_text("audio")
    (src.parent / "album.nfo").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<album>
  <title>A Rush of B-Sides to Your Head</title>
  <artist>Coldplay</artist>
  <year>2003</year>
</album>
""",
        encoding="utf-8",
    )
    src.with_suffix(".nfo").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<song>
  <title>Such A Rush</title>
  <artist>Coldplay</artist>
  <album>A Rush of Blood to the Head</album>
  <year>2002</year>
</song>
""",
        encoding="utf-8",
    )

    item = _item_from_parsed(must_parse(src))

    assert item.title == "Such A Rush"
    assert item.album == "A Rush of B-Sides to Your Head"
    assert item.year == 2003


def test_music_item_uses_cjk_track_nfo_title_when_album_is_cjk(tmp_path: Path):
    album = tmp_path / "Jay Chou" / "Ye Hui Mei"
    album.mkdir(parents=True)
    src = album / "01. Jay Chou - In the name of the father.mp3"
    src.write_text("audio")
    (album / "album.nfo").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<album>
  <title>叶惠美</title>
  <artist>周杰伦</artist>
  <year>2003</year>
</album>
""",
        encoding="utf-8",
    )
    src.with_suffix(".nfo").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<song>
  <title>以父之名</title>
  <artist>周杰伦</artist>
  <album>叶惠美</album>
  <year>2003</year>
</song>
""",
        encoding="utf-8",
    )

    item = _item_from_parsed(must_parse(src))

    assert item.title == "以父之名"
    assert item.metadata_title == "以父之名"
    assert item.album == "叶惠美"


def test_music_item_uses_album_nfo_when_album_tag_differs(tmp_path: Path):
    album = tmp_path / "Jay Chou" / "Loking For Jay Chou"
    album.mkdir(parents=True)
    src = album / "01 - Hidden Track.mp3"
    src.write_text("audio")
    (album / "album.nfo").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<album>
  <title>寻找周杰伦</title>
  <artist>周杰伦</artist>
  <year>2003</year>
</album>
""",
        encoding="utf-8",
    )
    parsed = must_parse(src)

    item = _item_from_parsed(parsed)
    light_item = _light_item_from_parsed(parsed)

    assert item.title == "Hidden Track"
    assert item.album == "寻找周杰伦"
    assert item.artist == "周杰伦"
    assert item.year == 2003
    assert item.metadata_title is None
    assert light_item.album == "寻找周杰伦"
    assert light_item.artist == "周杰伦"
    assert light_item.year == 2003


def test_scrape_does_not_write_local_only_music_nfo(tmp_path: Path):
    album = tmp_path / "Jay Chou" / "Loking For Jay Chou"
    album.mkdir(parents=True)
    src = album / "01 - Hidden Track.mp3"
    src.write_text("audio")
    parsed = must_parse(src)

    assert write_album_metadata(parsed, None, overwrite=True) == 0
    result = write_standard_metadata(parsed, None, overwrite=True)

    assert result.written == 0
    assert result.targets == []
    assert not (album / "album.nfo").exists()
    assert not src.with_suffix(".nfo").exists()


def test_local_track_candidate_uses_filename_title(tmp_path: Path):
    src = tmp_path / "01. 零缺点.mp3"
    src.write_text("audio")
    parsed = must_parse(src)
    album = ScrapeCandidate(
        source="netease",
        source_id="a",
        media_type="album",
        title="Album",
        artist="Artist",
        year=2000,
        genres=["pop"],
    )

    candidate = local_track_candidate(album, parsed)

    assert candidate is not None
    assert candidate.media_type == "track"
    assert candidate.title == "零缺点"
    assert candidate.track == 1
    assert candidate.genres == ["pop"]  # album context is preserved
    assert candidate.source == "local"
    assert candidate.source_id == ""
    assert candidate.external_ids == {}
    # No album match => no local-only NFO (preserves the un-scraped policy).
    assert local_track_candidate(None, parsed) is None


def test_overwrite_resets_stale_track_nfo_to_filename(tmp_path: Path):
    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    src = album / "01. 零缺点.mp3"
    src.write_text("audio")
    nfo = src.with_suffix(".nfo")
    nfo.write_text("<musicvideo><title>Opening (Live)</title></musicvideo>")
    parsed = must_parse(src)
    album_candidate = ScrapeCandidate(
        source="netease", source_id="a", media_type="album", title="Album", artist="Artist"
    )

    written = write_external_track_metadata(
        parsed, local_track_candidate(album_candidate, parsed), overwrite=True
    )

    assert written == 1
    text = nfo.read_text()
    assert "<title>零缺点</title>" in text
    assert "Opening (Live)" not in text
    assert "<uniqueid" not in text


def test_music_nfo_roundtrips_localized_names_and_canonical_ids(tmp_path: Path):
    src = tmp_path / "01 Silence.mp3"
    src.write_text("audio")
    parsed = must_parse(src)
    candidate = ScrapeCandidate(
        source="musicbrainz",
        source_id="recording-mbid",
        media_type="track",
        title="安静",
        original_title="Silence",
        artist="周杰伦",
        album_artist="周杰伦",
        album="范特西",
        external_ids={
            "musicbrainz_recording": "recording-mbid",
            "musicbrainz_release_group": "release-group-mbid",
            "musicbrainz_artist": "artist-mbid",
        },
        title_variants={"en": "Silence", "zh-CN": "安静"},
        artist_variants={"en": "Jay Chou", "zh-CN": "周杰伦"},
        album_artist_variants={"en": "Jay Chou", "zh-CN": "周杰伦"},
        album_variants={"en": "Fantasy", "zh-CN": "范特西"},
    )
    document = build_nfo(parsed, candidate)
    write_nfo(document)

    metadata = _read_local_metadata(src, "track", OrganizerScanContext.create())

    assert metadata.title == "安静"
    assert metadata.original_title == "Silence"
    assert metadata.title_variants == {"en": "Silence", "zh-CN": "安静"}
    assert metadata.artist_variants == {"en": "Jay Chou", "zh-CN": "周杰伦"}
    assert metadata.album_artist == "周杰伦"
    assert metadata.album_artist_variants == {
        "en": "Jay Chou",
        "zh-CN": "周杰伦",
    }
    assert metadata.album_variants == {"en": "Fantasy", "zh-CN": "范特西"}
    assert metadata.ids["musicbrainz_recording"] == "recording-mbid"
    assert metadata.ids["musicbrainz_release_group"] == "release-group-mbid"


def test_preserved_local_title_updates_matching_language_variant(tmp_path: Path):
    parsed = must_parse(tmp_path / "01 Song Live.mp3")
    candidate = ScrapeCandidate(
        source="musicbrainz",
        source_id="recording",
        media_type="track",
        title="Song",
        title_variants={"en": "Song", "zh-CN": "歌曲"},
    )

    preserved = _prefer_local_title(parsed, candidate)

    assert preserved.title == parsed.title
    assert preserved.title_variants["en"] == parsed.title
    assert preserved.title_variants["zh-CN"] == "歌曲"


def test_album_tracklist_metadata_number_matches_when_album_confirmed(tmp_path: Path):
    # One track matches by name (confirming the album), so the remaining
    # romanized track is safely number-matched.
    album = tmp_path / "Jay Chou" / "Initial J"
    album.mkdir(parents=True)
    first = album / "01 可爱女人.mp3"  # CJK exact match confirms the album
    second = album / "02 Hei Se You Mo.mp3"  # romanized -> number-matched
    first.write_text("audio")
    second.write_text("audio")
    parsed = [must_parse(first), must_parse(second)]
    candidates = [
        ScrapeCandidate(
            source="netease", source_id="1", media_type="track", title="可爱女人", track=1
        ),
        ScrapeCandidate(
            source="netease", source_id="2", media_type="track", title="黑色幽默", track=2
        ),
    ]

    mapped = album_track_metadata_by_path(parsed, candidates)

    assert mapped[first].title == "可爱女人"
    assert mapped[second].title == "黑色幽默"


def test_album_tracklist_metadata_never_matches_cjk_file_to_latin_candidate(tmp_path: Path):
    # Even when the album is confirmed by an English track, a Chinese file must
    # not be force-matched to an English candidate by track number.
    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    english = album / "01 Leave Me Alone.mp3"
    chinese = album / "02 零缺点.mp3"
    english.write_text("audio")
    chinese.write_text("audio")
    parsed = [must_parse(english), must_parse(chinese)]
    candidates = [
        ScrapeCandidate(
            source="mb", source_id="1", media_type="track", title="Leave Me Alone", track=1
        ),
        ScrapeCandidate(
            source="mb", source_id="2", media_type="track", title="Opening (Live)", track=2
        ),
    ]

    mapped = album_track_metadata_by_path(parsed, candidates)

    assert mapped[english].title == "Leave Me Alone"
    assert chinese not in mapped  # never forced onto the English candidate


def test_album_tracklist_metadata_rejects_unconfirmed_album(tmp_path: Path):
    # Chinese files vs an all-English tracklist (wrong album/edition or a
    # different disc split): no track matches by name, so nothing is
    # force-matched by number and the files keep their own titles.
    album = tmp_path / "孙燕姿" / "Live"
    album.mkdir(parents=True)
    first = album / "01. 零缺点.mp3"
    second = album / "02. 真的.mp3"
    first.write_text("audio")
    second.write_text("audio")
    parsed = [must_parse(first), must_parse(second)]
    candidates = [
        ScrapeCandidate(
            source="mb", source_id="1", media_type="track", title="Opening (Live)", track=1
        ),
        ScrapeCandidate(
            source="mb",
            source_id="2",
            media_type="track",
            title="Silent All These Years (Live)",
            track=2,
        ),
    ]

    assert album_track_metadata_by_path(parsed, candidates) == {}


def test_album_tracklist_metadata_matches_by_filename_for_multidisc(tmp_path: Path):
    # Disc 2 tracks whose numbering/order disagree with the online release must
    # still get the right titles by matching the song name from the filename,
    # not by the positional fallback (which would swap Gamma/Delta here).
    album = tmp_path / "Artist" / "Album"
    (album / "CD1").mkdir(parents=True)
    (album / "CD2").mkdir(parents=True)
    d1t1 = album / "CD1" / "01 Alpha.mp3"
    d1t2 = album / "CD1" / "02 Beta.mp3"
    d2t1 = album / "CD2" / "01 Gamma.mp3"
    d2t2 = album / "CD2" / "02 Delta.mp3"
    for file in (d1t1, d1t2, d2t1, d2t2):
        file.write_text("audio")
    parsed = [must_parse(file) for file in (d1t1, d1t2, d2t1, d2t2)]
    # Online release flattens onto a single disc and lists Delta before Gamma.
    candidates = [
        ScrapeCandidate(
            source="mb", source_id="1", media_type="track", title="Alpha", disc=1, track=1
        ),
        ScrapeCandidate(
            source="mb", source_id="2", media_type="track", title="Beta", disc=1, track=2
        ),
        ScrapeCandidate(
            source="mb", source_id="3", media_type="track", title="Delta", disc=1, track=3
        ),
        ScrapeCandidate(
            source="mb", source_id="4", media_type="track", title="Gamma", disc=1, track=4
        ),
    ]

    mapped = album_track_metadata_by_path(parsed, candidates)

    assert mapped[d1t1].title == "Alpha"
    assert mapped[d1t2].title == "Beta"
    assert mapped[d2t1].title == "Gamma"
    assert mapped[d2t2].title == "Delta"


def test_album_tracklist_metadata_rejects_number_match_when_titles_differ(tmp_path: Path):
    # Same script (CJK), clearly different songs at the same track numbers: the
    # number/positional match must be rejected so a wrong album can't force an
    # obviously-different name onto the file.
    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    first = album / "01 春天.mp3"
    second = album / "02 夏天.mp3"
    first.write_text("audio")
    second.write_text("audio")
    parsed = [must_parse(first), must_parse(second)]
    candidates = [
        ScrapeCandidate(
            source="mb", source_id="1", media_type="track", title="秋天", disc=1, track=1
        ),
        ScrapeCandidate(
            source="mb", source_id="2", media_type="track", title="冬天", disc=1, track=2
        ),
    ]

    assert album_track_metadata_by_path(parsed, candidates) == {}


def test_album_tracklist_metadata_matches_bracketed_title_variant(tmp_path: Path):
    # Edition/version qualifiers shouldn't block a clearly-correct match.
    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    track = album / "01 Fearless (Taylor's Version).mp3"
    track.write_text("audio")
    parsed = [must_parse(track)]
    candidates = [
        ScrapeCandidate(
            source="mb", source_id="1", media_type="track", title="Fearless", disc=1, track=1
        ),
    ]

    mapped = album_track_metadata_by_path(parsed, candidates)
    assert mapped[track].title == "Fearless"


def test_album_tracklist_metadata_matches_traditional_and_simplified(tmp_path: Path):
    # A traditional-script filename matches its simplified metadata (same song),
    # so the track is enriched from the candidate, but the title stays sourced
    # from the local filename (its traditional surface form).
    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    track = album / "01 龍的傳人.mp3"
    track.write_text("audio")
    parsed = [must_parse(track)]
    candidates = [
        ScrapeCandidate(
            source="mb", source_id="1", media_type="track", title="龙的传人", disc=1, track=1
        ),
    ]

    mapped = album_track_metadata_by_path(parsed, candidates)
    assert track in mapped  # recognized as the same song and enriched
    assert mapped[track].title == "龍的傳人"  # title stays from the local filename


def test_rename_conflict(tmp_path: Path):
    src = tmp_path / "Inception.2010.mkv"
    src.write_text("")
    target = tmp_path / "Inception (2010)" / "Inception (2010).mkv"
    target.parent.mkdir()
    target.write_text("existing")

    plan = plan_renames([must_parse(src)], root=tmp_path, templates=OrganizerTemplates())

    assert plan.operations[0].status == "conflict"
    with pytest.raises(ValueError):
        apply_rename_plan(plan)


def test_build_movie_nfo_with_candidate(tmp_path: Path):
    src = tmp_path / "Inception.2010.mkv"
    src.write_text("")
    parsed = must_parse(src)
    candidate = ScrapeCandidate(
        source="tmdb",
        source_id="27205",
        media_type="movie",
        title="Inception",
        year=2010,
        overview="A thief steals corporate secrets through dream-sharing technology.",
        tagline="Your mind is the scene of the crime.",
        poster_url="https://example.test/poster.jpg",
        confidence=1,
    )

    doc = build_nfo(parsed, candidate)

    assert doc.target == src.with_suffix(".nfo")
    assert "<movie>" in doc.xml
    assert '<uniqueid type="tmdb" default="true">27205</uniqueid>' in doc.xml
    assert "<tagline>Your mind is the scene of the crime.</tagline>" in doc.xml
    write_nfo(doc)
    assert src.with_suffix(".nfo").exists()


def test_organizer_item_reads_nfo_year_and_rating(tmp_path: Path):
    src = tmp_path / "2001 - A Space Odyssey.mkv"
    src.write_text("")
    src.with_suffix(".nfo").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<movie>
  <title>2001: A Space Odyssey</title>
  <year>1968</year>
  <ratings>
    <rating name="imdb" default="true"><value>8.3</value></rating>
  </ratings>
</movie>
""",
        encoding="utf-8",
    )

    item = _item_from_parsed(must_parse(src))

    assert item.metadata is True
    assert item.metadata_title == "2001: A Space Odyssey"
    assert item.metadata_year == 1968
    assert item.metadata_rating == 8.3
    assert item.metadata_rating_source == "imdb"


def test_organizer_item_reads_single_adjacent_movie_nfo(tmp_path: Path):
    src = tmp_path / "2001 - A Space Odyssey.mkv"
    src.write_text("")
    (tmp_path / "metadata.nfo").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<movie>
  <title>2001: A Space Odyssey</title>
  <originaltitle>2001</originaltitle>
  <year>1968</year>
  <premiered>1968-04-02</premiered>
  <mpaa>G</mpaa>
  <runtime>149</runtime>
  <genre>Science Fiction, Adventure</genre>
  <country>United States</country>
  <tagline>An epic drama of adventure and exploration.</tagline>
  <plot>Humanity finds a mysterious monolith.</plot>
  <tag>space</tag>
  <uniqueid type="imdb">tt0062622</uniqueid>
  <studio>Metro-Goldwyn-Mayer</studio>
  <actor><name>Keir Dullea</name></actor>
</movie>
""",
        encoding="utf-8",
    )
    Image.new("RGB", (100, 150), "black").save(tmp_path / "poster.jpg")
    (tmp_path / "._2001 - A Space Odyssey-poster.jpg").write_bytes(b"appledouble")
    (tmp_path / "2001 - A Space Odyssey.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHi")

    item = _item_from_parsed(must_parse(src))

    assert item.metadata is True
    assert item.metadata_title == "2001: A Space Odyssey"
    assert item.metadata_original_title == "2001"
    assert item.metadata_year == 1968
    assert item.metadata_premiered == "1968-04-02"
    assert item.metadata_certification == "G"
    assert item.metadata_runtime == 149
    assert item.metadata_genres == ["Science Fiction", "Adventure"]
    assert item.metadata_countries == ["United States"]
    assert item.metadata_tagline == "An epic drama of adventure and exploration."
    assert item.metadata_plot == "Humanity finds a mysterious monolith."
    assert item.metadata_tags == ["space"]
    assert item.metadata_ids == {"imdb": "tt0062622"}
    assert item.metadata_studios == ["Metro-Goldwyn-Mayer"]
    assert item.metadata_cast == ["Keir Dullea"]
    assert item.images is True
    assert item.artwork[0].kind == "poster"
    assert item.artwork[0].width == 100
    assert item.artwork[0].height == 150
    assert all(not asset.label.startswith("._") for asset in item.artwork)
    related_names = {file.name for file in item.related_files}
    assert "metadata.nfo" in related_names
    assert "poster.jpg" in related_names
    assert "2001 - A Space Odyssey.srt" in related_names


def test_organizer_item_reads_tv_showtitle_separately(tmp_path: Path):
    src = tmp_path / "Severance" / "Season 02" / "Hello Ms Cobel S02E01.mkv"
    src.parent.mkdir(parents=True)
    src.write_text("")
    (tmp_path / "Severance" / "tvshow.nfo").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<tvshow>
  <title>Severance</title>
  <year>2022</year>
  <rating>8.7</rating>
  <studio>Apple TV+</studio>
</tvshow>
""",
        encoding="utf-8",
    )
    src.with_suffix(".nfo").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<episodedetails>
  <title>Hello, Ms. Cobel</title>
  <showtitle>Severance</showtitle>
  <season>2</season>
  <episode>1</episode>
  <aired>2025-01-17</aired>
  <rating>8.1</rating>
</episodedetails>
""",
        encoding="utf-8",
    )

    item = _item_from_parsed(must_parse(src))

    assert item.metadata_title == "Hello, Ms. Cobel"
    assert item.metadata_show_title == "Severance"
    assert item.metadata_year == 2025
    assert item.metadata_rating == 8.1
    assert item.metadata_studios == ["Apple TV+"]


def test_organizer_item_detects_sidecar_lyrics(tmp_path: Path):
    src = tmp_path / "Radiohead" / "OK Computer" / "01 - Airbag.flac"
    src.parent.mkdir(parents=True)
    src.write_text("audio")
    src.with_suffix(".lrc").write_text("[00:00.00]Airbag")

    item = _item_from_parsed(must_parse(src))

    assert item.lyrics is True
    assert item.metadata_synced_lyrics == "[00:00.00]Airbag"
    assert any(file.kind == "lyrics" for file in item.related_files)


def test_plan_artwork_targets_folder_for_tracks(tmp_path: Path):
    src = tmp_path / "Radiohead" / "OK Computer" / "01 - Airbag.flac"
    src.parent.mkdir(parents=True)
    src.write_text("")
    parsed = must_parse(src)
    candidate = ScrapeCandidate(
        source="itunes",
        source_id="1",
        media_type="track",
        title="Airbag",
        artist="Radiohead",
        album="OK Computer",
        poster_url="https://example.test/folder.jpg",
    )

    plan = plan_artwork(parsed, candidate)

    assert plan.status == "ready"
    assert plan.target == src.parent / "folder.jpg"
