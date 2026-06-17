from __future__ import annotations

from mm.server.smart_albums import _build_static_album


def test_static_smart_album_keeps_empty_color_as_string():
    album = _build_static_album(
        {
            "key": "all",
            "title": "All Media",
            "icon": "images",
            "color": "",
            "filters": {},
        },
        {"total": 1, "type_dist": {}, "trash_count": 0},
    )

    assert album["color"] == ""
