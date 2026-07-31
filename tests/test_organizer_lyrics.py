from __future__ import annotations

from mm.organizer import lyrics


def test_netease_lyrics_select_matching_chinese_title(monkeypatch):
    calls = []

    def search(track, artist, album, *, limit):
        calls.append((track, artist, album, limit))
        return [
            {
                "trackName": "我要的幸福",
                "artistName": "孙燕姿",
                "albumName": "我要的幸福",
                "syncedLyrics": "[00:01.00]wrong",
            },
            {
                "trackName": "累赘",
                "artistName": "孙燕姿",
                "albumName": "我要的幸福",
                "syncedLyrics": "[00:01.00]correct",
            },
        ]

    monkeypatch.setattr(lyrics, "search_netease_lyrics", search)

    result = lyrics.lyrics_from_source("netease", "累赘", "孙燕姿", "我要的幸福")

    assert result is not None
    assert result["syncedLyrics"] == "[00:01.00]correct"
    assert calls == [("累赘", "孙燕姿", "", 5)]


def test_netease_lyrics_reject_wrong_song(monkeypatch):
    monkeypatch.setattr(
        lyrics,
        "search_netease_lyrics",
        lambda *args, **kwargs: [
            {
                "trackName": "我要的幸福",
                "artistName": "孙燕姿",
                "syncedLyrics": "[00:01.00]wrong",
            }
        ],
    )

    assert lyrics.lyrics_from_source("netease", "累赘", "孙燕姿", "我要的幸福") is None


def test_netease_lyrics_matches_canonical_chinese_artist(monkeypatch):
    monkeypatch.setattr(
        lyrics,
        "search_netease_lyrics",
        lambda *args, **kwargs: [
            {
                "trackName": "岩石里的花",
                "artistName": "G.E.M.邓紫棋",
                "albumName": "睡皇后",
                "syncedLyrics": "[00:01.00]花",
            }
        ],
    )

    result = lyrics.lyrics_from_source("netease", "岩石里的花", "邓紫棋", "睡皇后")

    assert result is not None
    assert result["syncedLyrics"] == "[00:01.00]花"


def test_kugou_lyrics_are_available_as_matching_fallback(monkeypatch):
    monkeypatch.setattr(
        lyrics,
        "search_kugou_lyrics",
        lambda *args, **kwargs: [
            {
                "trackName": "你会不会",
                "artistName": "梁静茹",
                "syncedLyrics": "[00:01.00]歌词",
            }
        ],
    )

    result = lyrics.lyrics_from_source("kugou", "你会不会", "梁静茹", "情歌没有告诉你")

    assert result is not None
    assert result["syncedLyrics"] == "[00:01.00]歌词"
