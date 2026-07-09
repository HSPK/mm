from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from mm.config import OrganizerTemplates
from mm.db.models import OrganizerMediaModel
from mm.db.sync_client import DBClient
from mm.organizer.artwork import plan_artwork
from mm.organizer.filename import parse_media_filename
from mm.organizer.nfo import build_nfo, write_nfo
from mm.organizer.rename import RenameOperation, apply_rename_plan, plan_renames
from mm.organizer.scrape_writer import (
    album_track_metadata_by_path,
    write_album_metadata,
    write_external_track_metadata,
    write_standard_metadata,
)
from mm.organizer.scrapers import ScrapeCandidate
from mm.server.routers.organizer import _item_from_parsed, _light_item_from_parsed
from mm.server.organizer_metadata import OrganizerScanContext
from mm.server.organizer_persistence import persist_scan_items
from mm.server.organizer_rename_jobs import refresh_after_rename


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
    src = tmp_path / "Radiohead" / "OK Computer" / "01 - Airbag.flac"
    src.parent.mkdir(parents=True)
    src.write_text("audio")
    parsed = must_parse(src)

    out = tmp_path / "organized"
    plan = plan_renames([parsed], root=out, templates=OrganizerTemplates())
    assert apply_rename_plan(plan) == 1

    assert (out / "Radiohead" / "OK Computer" / "01 - Airbag.flac").read_text() == "audio"
    assert not src.exists()


def test_apply_album_rename_dedupes_sidecars_and_removes_empty_folders(tmp_path: Path):
    album = tmp_path / "Radiohead" / "OK Computer"
    album.mkdir(parents=True)
    first = album / "01 - Airbag.flac"
    second = album / "02 - Paranoid Android.flac"
    first.write_text("one")
    second.write_text("two")
    (album / "album.nfo").write_text("album")
    (album / "folder.jpg").write_text("cover")
    (album / "OK Computer.cue").write_text("cue")

    parsed = [must_parse(first), must_parse(second)]
    out = tmp_path / "organized"
    plan = plan_renames(parsed, root=out, templates=OrganizerTemplates())

    targets = [operation.target.relative_to(out) for operation in plan.actionable]
    assert targets.count(Path("Radiohead/OK Computer/album.nfo")) == 1
    assert targets.count(Path("Radiohead/OK Computer/folder.jpg")) == 1
    assert targets.count(Path("Radiohead/OK Computer/OK Computer.cue")) == 1

    assert apply_rename_plan(plan) == 5
    assert (out / "Radiohead" / "OK Computer" / "01 - Airbag.flac").read_text() == "one"
    assert (out / "Radiohead" / "OK Computer" / "02 - Paranoid Android.flac").read_text() == "two"
    assert (out / "Radiohead" / "OK Computer" / "album.nfo").read_text() == "album"
    assert (out / "Radiohead" / "OK Computer" / "folder.jpg").read_text() == "cover"
    assert (out / "Radiohead" / "OK Computer" / "OK Computer.cue").read_text() == "cue"
    assert not album.exists()


def test_refresh_after_rename_replaces_stale_target_row(tmp_path: Path, db: DBClient):
    source = tmp_path / "Coldplay" / "A Head Full Of Dreams" / "01. A Head Full Of Dreams.flac"
    target = tmp_path / "Coldplay" / "2015 - A Head Full Of Dreams" / "01. A Head Full Of Dreams.flac"
    source.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    source.write_text("audio")
    target.write_text("stale")
    context = OrganizerScanContext.create()
    source_item = _light_item_from_parsed(must_parse(source), context)
    target_item = _light_item_from_parsed(must_parse(target), context)
    db._run(persist_scan_items(db._client, [source_item, target_item], mark_missing=False))
    source_row = db._run(db._client.objects.get(OrganizerMediaModel, path=str(source.resolve())))

    db._run(refresh_after_rename(
        db._client,
        [must_parse(source)],
        [RenameOperation(source.resolve(), target.resolve(), "track", "ready")],
    ))

    rows = db._run(db._client.objects.fetchall(
        OrganizerMediaModel.select().where(
            OrganizerMediaModel.path.in_([str(source.resolve()), str(target.resolve())])
        )
    ))
    assert [(row.id, row.path) for row in rows] == [(source_row.id, str(target.resolve()))]


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


def test_album_tracklist_metadata_maps_by_track_number(tmp_path: Path):
    album = tmp_path / "Jay Chou" / "Initial J"
    album.mkdir(parents=True)
    first = album / "01 Ke Ai Nu Ren.mp3"
    second = album / "02 Hei Se You Mo.mp3"
    first.write_text("audio")
    second.write_text("audio")
    parsed = [must_parse(first), must_parse(second)]
    candidates = [
        ScrapeCandidate(
            source="netease",
            source_id="1",
            media_type="track",
            title="可爱女人",
            artist="周杰伦",
            album="Initial J",
            year=2005,
            track=1,
        ),
        ScrapeCandidate(
            source="netease",
            source_id="2",
            media_type="track",
            title="黑色幽默",
            artist="周杰伦",
            album="Initial J",
            year=2005,
            track=2,
        ),
    ]

    mapped = album_track_metadata_by_path(parsed, candidates)
    written = sum(
        write_external_track_metadata(item, mapped.get(item.path), overwrite=False)
        for item in parsed
    )

    assert written == 2
    assert "<title>可爱女人</title>" in first.with_suffix(".nfo").read_text()
    assert "<title>黑色幽默</title>" in second.with_suffix(".nfo").read_text()


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
        poster_url="https://example.test/poster.jpg",
        confidence=1,
    )

    doc = build_nfo(parsed, candidate)

    assert doc.target == src.with_suffix(".nfo")
    assert "<movie>" in doc.xml
    assert "<uniqueid type=\"tmdb\" default=\"true\">27205</uniqueid>" in doc.xml
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
