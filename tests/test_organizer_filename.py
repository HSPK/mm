from __future__ import annotations

from pathlib import Path

from mm.organizer.filename import _fix_mojibake_text, clean_music_title, parse_media_filename


def test_parse_movie_filename():
    parsed = parse_media_filename(Path("Inception.2010.1080p.BluRay.x264-GRP.mkv"))

    assert parsed is not None
    assert parsed.media_type == "movie"
    assert parsed.title == "Inception"
    assert parsed.year == 2010


def test_parse_movie_title_that_starts_with_year():
    parsed = parse_media_filename(Path("2001 - A Space Odyssey (1968) 1080p AAC.mkv"))

    assert parsed is not None
    assert parsed.media_type == "movie"
    assert parsed.title == "2001 A Space Odyssey"
    assert parsed.year == 1968


def test_parse_tv_episode_filename():
    parsed = parse_media_filename(Path("The.Last.of.Us.S01E02.2160p.WEB-DL.mkv"))

    assert parsed is not None
    assert parsed.media_type == "tv"
    assert parsed.title == "The Last of Us"
    assert parsed.season == 1
    assert parsed.episode == 2


def test_parse_tv_episode_falls_back_to_parent_title():
    parsed = parse_media_filename(Path("Severance/S02E01.mkv"))

    assert parsed is not None
    assert parsed.media_type == "tv"
    assert parsed.title == "Severance"
    assert parsed.season == 2
    assert parsed.episode == 1


def test_parse_tv_episode_prefers_show_folder_over_episode_title():
    parsed = parse_media_filename(Path("Severance/Season 02/Hello Ms Cobel S02E01.mkv"))

    assert parsed is not None
    assert parsed.media_type == "tv"
    assert parsed.title == "Severance"
    assert parsed.season == 2
    assert parsed.episode == 1


def test_parse_tv_episode_prefers_parent_show_folder():
    parsed = parse_media_filename(Path("Severance/Hello Ms Cobel S02E01.mkv"))

    assert parsed is not None
    assert parsed.media_type == "tv"
    assert parsed.title == "Severance"
    assert parsed.season == 2
    assert parsed.episode == 1


def test_ignore_non_video():
    assert parse_media_filename(Path("poster.jpg")) is None


def test_ignore_macos_appledouble_sidecar():
    assert parse_media_filename(Path("._2001 - A Space Odyssey.mkv")) is None


def test_parse_audio_track_from_artist_album_folders():
    parsed = parse_media_filename(Path("Radiohead/OK Computer/01 - Airbag.flac"))

    assert parsed is not None
    assert parsed.media_type == "track"
    assert parsed.artist == "Radiohead"
    assert parsed.album == "OK Computer"
    assert parsed.title == "Airbag"
    assert parsed.track == 1


def test_parse_audio_track_from_full_release_name():
    parsed = parse_media_filename(Path("Daft Punk - Discovery - 02 - Aerodynamic.mp3"))

    assert parsed is not None
    assert parsed.media_type == "track"
    assert parsed.artist == "Daft Punk"
    assert parsed.album == "Discovery"
    assert parsed.title == "Aerodynamic"
    assert parsed.track == 2


def test_parse_audio_album_folder_artist_album_year_quality_suffix():
    parsed = parse_media_filename(
        Path("Coldplay - Everyday Life (2019) [FLAC 24-96]/01 - Sunrise.flac")
    )

    assert parsed is not None
    assert parsed.media_type == "track"
    assert parsed.artist == "Coldplay"
    assert parsed.album == "Everyday Life"
    assert parsed.year == 2019
    assert parsed.title == "Sunrise"
    assert parsed.track == 1


def test_parse_audio_artist_release_folder_with_outer_artist_folder():
    parsed = parse_media_filename(
        Path("Coldplay/Coldplay - Everyday Life (2019) [FLAC 24-96]/01 Sunrise.flac")
    )

    assert parsed is not None
    assert parsed.artist == "Coldplay"
    assert parsed.album == "Everyday Life"
    assert parsed.year == 2019
    assert parsed.track == 1
    assert parsed.title == "Sunrise"


def test_parse_audio_track_strips_redundant_artist_prefix_from_album_folder():
    parsed = parse_media_filename(
        Path(
            "Taylor Swift - Lover (2019) [FLAC 24-44]/"
            "01. Taylor Swift - I Forgot That You Existed.flac"
        )
    )

    assert parsed is not None
    assert parsed.artist == "Taylor Swift"
    assert parsed.album == "Lover"
    assert parsed.year == 2019
    assert parsed.track == 1
    assert parsed.title == "I Forgot That You Existed"


def test_parse_audio_uses_album_artist_for_compilation_album():
    parsed = parse_media_filename(Path("Various Artists/Pop Mix/01. Artist A - Big Song.flac"))

    assert parsed is not None
    assert parsed.artist == "Artist A"
    assert parsed.album_artist == "Various Artists"
    assert parsed.album == "Pop Mix"
    assert parsed.title == "Big Song"
    assert parsed.track == 1


def test_parse_audio_separates_track_credit_from_primary_album_artist():
    parsed = parse_media_filename(
        Path("Music/2010 - 跨时代/02. 周杰伦&浪花兄弟 - 免费教学录影带.flac")
    )

    assert parsed is not None
    assert parsed.artist == "周杰伦, 浪花兄弟"
    assert parsed.album_artist == "周杰伦"
    assert parsed.album == "跨时代"
    assert parsed.year == 2010
    assert parsed.title == "免费教学录影带"
    assert parsed.track == 2


def test_parse_audio_ignores_numeric_artist_tags(monkeypatch):
    import mm.organizer.filename as filename

    monkeypatch.setattr(
        filename,
        "_audio_tags",
        lambda _path: {
            "title": "守時",
            "artist": "2",
            "album_artist": "2",
            "album": "自便",
        },
    )

    parsed = parse_media_filename(Path("王菲/EP's/[1997.05] 自便/01. 守時.mp3"))

    assert parsed is not None
    assert parsed.artist == "王菲"
    assert parsed.album_artist == "王菲"


def test_parse_audio_canonicalizes_common_chinese_artist_aliases(monkeypatch):
    import mm.organizer.filename as filename

    monkeypatch.setattr(
        filename,
        "_audio_tags",
        lambda _path: {
            "title": "Song",
            "artist": "G.E.M.",
            "album_artist": "Wang Leehom",
            "album": "Album",
        },
    )

    parsed = parse_media_filename(Path("Music/Album/01 Song.mp3"))

    assert parsed is not None
    assert parsed.artist == "邓紫棋"
    assert parsed.album_artist == "王力宏"


def test_parse_audio_track_preserves_decimal_dot_title():
    parsed = parse_media_filename(
        Path("Coldplay/2003 - A Rush Of B-Sides To Your Head/17. 1.36.flac")
    )

    assert parsed is not None
    assert parsed.track == 17
    assert parsed.title == "1.36"


def test_parse_audio_album_folder_with_reissue_label_suffix():
    parsed = parse_media_filename(
        Path(
            "Michael Jackson - Forever, Michael (1975) "
            "[1994, Motown 530 280-2] FLAC 88/01 - We're Almost There.flac"
        )
    )

    assert parsed is not None
    assert parsed.artist == "Michael Jackson"
    assert parsed.album == "Forever, Michael"
    assert parsed.year == 1975


def test_parse_audio_artist_year_album_folder():
    parsed = parse_media_filename(
        Path("ColdPlay/2021 - Music Of The Spheres/01 - Higher Power.flac")
    )

    assert parsed is not None
    assert parsed.artist == "ColdPlay"
    assert parsed.album == "Music Of The Spheres"
    assert parsed.year == 2021
    assert parsed.title == "Higher Power"


def test_parse_audio_dated_album_cd_folder_template():
    parsed = parse_media_filename(
        Path(
            "Jay Chou/[2005-01-21] 周杰伦--周杰伦2004无与伦比演唱会 Live CD/"
            "CD1/01.-.以父之名.-.周杰伦2004无与伦比演唱会Live CD CD1.-.周杰伦.mp3"
        )
    )

    assert parsed is not None
    assert parsed.artist == "周杰伦"
    assert parsed.album == "周杰伦2004无与伦比演唱会 Live CD"
    assert parsed.year == 2005
    assert parsed.disc == 1
    assert parsed.track == 1
    assert parsed.title == "以父之名"


def test_parse_audio_dated_album_simple_cd_folder_template():
    parsed = parse_media_filename(
        Path(
            "Jay Chou/[2011-01-25] Jay Chou 周杰倫 超時代演唱會 The Era World Tours Concert Live/"
            "cd1/1.龍戰騎士.mp3"
        )
    )

    assert parsed is not None
    assert parsed.artist == "周杰伦"
    assert parsed.album_artist == "周杰伦"
    assert parsed.album == "Jay Chou 周杰倫 超時代演唱會 The Era World Tours Concert Live"
    assert parsed.year == 2011
    assert parsed.disc == 1
    assert parsed.track == 1
    assert parsed.title == "龍戰騎士"


def test_audio_fallback_groups_cd_folder_under_album_parent():
    parsed = parse_media_filename(Path("Artist/Album/cd2/01.Unknown.mp3"))

    assert parsed is not None
    assert parsed.album == "Album"
    assert parsed.disc == 2
    assert parsed.track == 1
    assert parsed.title == "Unknown"
    assert parsed.parse_template is None


def test_parse_audio_fallback_without_template_match_still_returns_track():
    parsed = parse_media_filename(Path("Odd/Unmatched/File Name Without Track Number.mp3"))

    assert parsed is not None
    assert parsed.media_type == "track"
    assert parsed.title == "File Name Without Track Number"
    assert parsed.parse_template is None
    assert parsed.confidence == 0.1


def test_fix_big5_mojibake_tags():
    assert _fix_mojibake_text("Às¾ÔÃM¤h") == "龍戰騎士"
    assert _fix_mojibake_text("©PªN\xadÛ") == "周杰倫"


def test_clean_music_title_removes_live_and_disc_suffixes():
    assert clean_music_title("2004无与伦比演唱会 [Live] [Disc 1]") == "2004无与伦比演唱会"
    assert clean_music_title("超时代演唱会CD1") == "超时代演唱会"


def test_parse_audio_skips_category_folder_and_reads_cjk_artist():
    parsed = parse_media_filename(Path("王菲/EP's/[1993.12] 如風/01. 如風.mp3"))

    assert parsed is not None
    assert parsed.artist == "王菲"
    assert parsed.year == 1993


def test_parse_audio_roman_numeral_disc_folder_with_category():
    parsed = parse_media_filename(
        Path("孙燕姿/Other Albums/[2010.01.29] My Story/Disc I/12. 我不难过.mp3")
    )

    assert parsed is not None
    assert parsed.artist == "孙燕姿"
    assert parsed.disc == 1
    assert parsed.track == 12
    assert parsed.year == 2010


def test_clean_music_title_strips_roman_disc_suffix():
    assert (
        clean_music_title("My Story (2010 Special Edition) [Disc I]")
        == "My Story (2010 Special Edition)"
    )


def test_parse_audio_skips_russian_category_folder():
    parsed = parse_media_filename(Path("王力宏/Синглы/2011 - 火力全開/01.火力全開.mp3"))

    assert parsed is not None
    assert parsed.artist == "王力宏"
    assert parsed.year == 2011


def test_parse_audio_year_prefixed_album_direct():
    parsed = parse_media_filename(Path("王力宏/1999 - 不可能錯過你/07.不降落的滑翔翼.mp3"))

    assert parsed is not None
    assert parsed.artist == "王力宏"
    assert parsed.album == "不可能錯過你"
    assert parsed.year == 1999
    assert parsed.track == 7
