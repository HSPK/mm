"""Parse movie/TV/music release filenames into scrape queries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from mm.config import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|2100)\b")
_EPISODE_RE = re.compile(
    r"(?P<prefix>.*?)(?:^|[\s._\-\[\(])S(?P<season>\d{1,2})E(?P<episode>\d{1,3})(?:E(?P<episode_end>\d{1,3}))?",
    re.IGNORECASE,
)
_ALT_EPISODE_RE = re.compile(
    r"(?P<prefix>.*?)(?:^|[\s._\-\[\(])(?P<season>\d{1,2})x(?P<episode>\d{1,3})",
    re.IGNORECASE,
)
_BRACKET_RE = re.compile(r"[\[\(（【].*?[\]\)）】]")
_SEASON_DIR_RE = re.compile(r"^(?:s(?:eason)?|series)\s*\d{1,3}$", re.IGNORECASE)
_CHINESE_SEASON_DIR_RE = re.compile(r"^第\s*\d{1,3}\s*季$")

_NOISE_TOKENS = {
    "2160p",
    "1080p",
    "720p",
    "480p",
    "uhd",
    "hdr",
    "dv",
    "webrip",
    "web-dl",
    "webdl",
    "bluray",
    "brrip",
    "hdtv",
    "x264",
    "x265",
    "h264",
    "h265",
    "hevc",
    "avc",
    "aac",
    "dts",
    "truehd",
    "atmos",
    "proper",
    "repack",
    "extended",
    "remastered",
}

_GENERIC_TV_DIRS = {
    "download",
    "downloads",
    "episode",
    "episodes",
    "season",
    "seasons",
    "series",
    "show",
    "shows",
    "tv",
    "tv series",
    "tv show",
    "tv shows",
    "video",
    "videos",
}


@dataclass(frozen=True)
class ParsedMediaFile:
    path: Path
    media_type: str
    title: str
    artist: str | None = None
    album: str | None = None
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    episode_end: int | None = None
    disc: int | None = None
    track: int | None = None
    parse_template: str | None = None
    parse_relative_path: str | None = None
    confidence: float = 0.0

    @property
    def is_video(self) -> bool:
        return self.path.suffix.lower() in VIDEO_EXTENSIONS

    @property
    def is_audio(self) -> bool:
        return self.path.suffix.lower() in AUDIO_EXTENSIONS


def parse_media_filename(path: str | Path) -> ParsedMediaFile | None:
    file_path = Path(path)
    if file_path.name.startswith("._"):
        return None
    ext = file_path.suffix.lower()
    if ext in AUDIO_EXTENSIONS:
        return _parse_audio_filename(file_path)
    if ext not in VIDEO_EXTENSIONS:
        return None

    stem = _strip_noise(file_path.stem)
    episode_match = _EPISODE_RE.search(stem) or _ALT_EPISODE_RE.search(stem)
    if episode_match:
        title = _tv_title_from_path(file_path) or _clean_title(episode_match.group("prefix"))
        if not title:
            return None
        return ParsedMediaFile(
            path=file_path,
            media_type="tv",
            title=title,
            season=int(episode_match.group("season")),
            episode=int(episode_match.group("episode")),
            episode_end=(
                int(episode_match.group("episode_end"))
                if episode_match.groupdict().get("episode_end")
                else None
            ),
            confidence=0.9,
        )

    year_match = _last_non_initial_year_match(stem)
    raw_year_match = _last_non_initial_year_match(file_path.stem)
    matched_year = year_match or raw_year_match
    year: int | None = int(matched_year.group(1)) if matched_year else None
    title_part = stem
    if year_match:
        title_part = stem[: year_match.start()]

    title = _clean_title(title_part) or _clean_title(file_path.stem)
    if not title:
        return None
    return ParsedMediaFile(
        path=file_path,
        media_type="movie",
        title=title,
        year=year,
        confidence=0.78 if year else 0.62,
    )


def _parse_audio_filename(file_path: Path) -> ParsedMediaFile | None:
    tags = _audio_tags(file_path)
    directory = _audio_directory_info(file_path)
    file_info = _audio_file_info(file_path.stem)
    artist = tags.get("artist") or file_info.artist or directory.artist
    title = strip_redundant_artist_prefix(
        tags.get("title") or file_info.title,
        artist,
    )
    album = clean_music_title(tags.get("album") or file_info.album or directory.album)
    year = tags.get("year") or directory.year
    disc = tags.get("disc") or directory.disc
    track = tags.get("track") or file_info.track
    return ParsedMediaFile(
        path=file_path,
        media_type="track",
        artist=artist,
        album=album,
        title=title or file_path.stem,
        year=year,
        disc=disc,
        track=track,
        confidence=0.95 if tags else 0.55 if album and track else 0.1,
    )


@dataclass(frozen=True)
class AudioFileInfo:
    title: str
    artist: str | None = None
    album: str | None = None
    track: int | None = None


def strip_redundant_artist_prefix(title: str, artist: str | None) -> str:
    if not artist:
        return title
    match = re.match(
        rf"^{re.escape(_clean_title(artist))}(?:\s*[-–—:]\s*|\s+)(?P<title>.+)$",
        title,
        re.IGNORECASE,
    )
    return _clean_track_title(match.group("title")) if match else title


@dataclass(frozen=True)
class AudioDirectoryInfo:
    artist: str | None
    album: str | None
    year: int | None
    disc: int | None


def _audio_directory_info(file_path: Path) -> AudioDirectoryInfo:
    disc = _disc_from_folder(file_path.parent.name)
    album_dir = file_path.parent.parent if disc is not None else file_path.parent
    parent = album_dir.parent.name
    artist, album, year = _release_folder_info(album_dir.name)
    if not artist:
        artist = _clean_artist(parent)
    return AudioDirectoryInfo(artist=artist, album=album, year=year, disc=disc)


def _release_folder_info(value: str) -> tuple[str | None, str | None, int | None]:
    clean = _clean_release_folder(value)
    dated_site = re.match(
        r"^\[(?P<year>19\d{2}|20\d{2}|2100)-\d{2}-\d{2}\]\s*"
        r"(?P<artist>.+?)\.-\.\[(?P<album>.+?)\]\..*$",
        value,
    )
    if dated_site:
        return (
            _clean_artist(dated_site.group("artist")),
            _clean_title(dated_site.group("album")),
            int(dated_site.group("year")),
        )
    dated = re.match(r"^\[(?P<year>19\d{2}|20\d{2}|2100)-\d{2}-\d{2}\]\s*(?P<album>.+)$", value)
    if dated:
        return None, clean_music_title(dated.group("album")), int(dated.group("year"))
    artist_album_year = re.match(
        r"^(?P<artist>.+?)\s+-\s+(?P<album>.+?)\s+\((?P<year>19\d{2}|20\d{2}|2100)\)",
        value,
    )
    if artist_album_year:
        return (
            _clean_artist(artist_album_year.group("artist")),
            clean_music_title(artist_album_year.group("album")),
            int(artist_album_year.group("year")),
        )
    dated = re.match(r"^\[(?P<year>19\d{2}|20\d{2}|2100)-\d{2}-\d{2}\]\s*(?P<album>.+)$", clean)
    if dated:
        return None, clean_music_title(dated.group("album")), int(dated.group("year"))
    artist_album_year = re.match(
        r"^(?P<artist>.+?)\s+-\s+(?P<album>.+?)\s+\((?P<year>19\d{2}|20\d{2}|2100)\)",
        clean,
    )
    if artist_album_year:
        return (
            _clean_artist(artist_album_year.group("artist")),
            clean_music_title(artist_album_year.group("album")),
            int(artist_album_year.group("year")),
        )
    year_album = re.match(r"^(?P<year>19\d{2}|20\d{2}|2100)\s*[-–—_. ]+\s*(?P<album>.+)$", clean)
    if year_album:
        return None, clean_music_title(year_album.group("album")), int(year_album.group("year"))
    if " - " in clean:
        artist, album = clean.split(" - ", 1)
        return _clean_artist(artist), clean_music_title(album), None
    return None, clean_music_title(clean), None


def _audio_tags(file_path: Path) -> dict[str, str | int | None]:
    try:
        from mutagen import File as MutagenFile
    except ImportError:
        return {}
    try:
        audio = MutagenFile(file_path, easy=True)
    except Exception:
        return {}
    if not audio:
        return {}
    return {
        "title": _first_tag(audio, "title"),
        "artist": _first_tag(audio, "artist") or _first_tag(audio, "albumartist"),
        "album": _first_tag(audio, "album"),
        "year": _year_from_tag(_first_tag(audio, "date") or _first_tag(audio, "year")),
        "disc": _number_from_slash_tag(_first_tag(audio, "discnumber")),
        "track": _number_from_slash_tag(_first_tag(audio, "tracknumber")),
    }


def _first_tag(audio: object, key: str) -> str | None:
    try:
        values = audio.get(key)  # type: ignore[attr-defined]
    except AttributeError:
        return None
    if not values:
        return None
    value = values[0] if isinstance(values, list) else values
    return _clean_title(_fix_mojibake_text(str(value))) if value else None


def _fix_mojibake_text(value: str) -> str:
    best = value
    best_score = _cjk_score(value)
    for encoding in ("big5", "cp950", "gbk", "gb18030"):
        try:
            decoded = value.encode("latin1").decode(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        score = _cjk_score(decoded)
        if score > best_score:
            best = decoded
            best_score = score
    return best


def _cjk_score(value: str) -> int:
    cjk = sum(1 for char in value if "\u3400" <= char <= "\u9fff")
    common = sum(1 for char in value if char in _COMMON_CJK_CHARS)
    suspicious = sum(1 for char in value if char in _SUSPICIOUS_MOJIBAKE_CHARS)
    return cjk * 10 + common * 5 - suspicious * 8


_COMMON_CJK_CHARS = set(
    "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年"
    "动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化"
    "高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天"
    "政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向"
    "道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革"
    "位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角"
    "期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热"
    "领七海口东导器压志世金增争济阶油思术极交受联认六共权收证改清己美再采转更单风切"
    "打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节"
    "话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布"
    "复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往酸历市"
    "克何除消构府称太准精值号率族维划选标写存候毛亲快效斯院查江型眼王按格养易置派层"
    "片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严龙飞"
)
_SUSPICIOUS_MOJIBAKE_CHARS = set("扂笚豌豐疆竭籟豝")


def _year_from_tag(value: str | None) -> int | None:
    if not value:
        return None
    match = _YEAR_RE.search(value)
    return int(match.group(1)) if match else None


def _number_from_slash_tag(value: str | None) -> int | None:
    if not value:
        return None
    return _int_or_none(value.split("/", 1)[0].strip())


def _clean_track_title(value: str) -> str:
    placeholder = "§DECIMALDOT§"
    text = re.sub(r"(?<=\d)\.(?=\d)", placeholder, value)
    return _clean_title(text).replace(placeholder, ".")


def clean_music_title(value: str | None) -> str | None:
    if not value:
        return None
    text = _clean_title(value)
    while True:
        next_text = re.sub(
            r"\s*[\[\(（【]\s*(?:live|disc\s*\d+|cd\s*\d+)\s*[\]\)）】]\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        if next_text == text:
            return re.sub(r"\s*(?:disc|cd)\s*\d+\s*$", "", text, flags=re.IGNORECASE).strip()
        text = next_text


def _audio_file_info(stem: str) -> AudioFileInfo:
    rich = re.match(
        r"^(?P<artist>.+?)\s+-\s+(?P<album>.+?)\s+-\s+(?P<track>\d{1,3})\s+-\s+(?P<title>.+)$",
        stem,
    )
    if rich:
        return AudioFileInfo(
            title=_clean_track_title(rich.group("title")),
            artist=_clean_artist(rich.group("artist")),
            album=clean_music_title(rich.group("album")),
            track=int(rich.group("track")),
        )
    track_match = re.match(r"^(?P<track>\d{1,3})\s*[-._ ]+\s*(?P<title>.+)$", stem)
    raw_title = track_match.group("title") if track_match else stem
    track = int(track_match.group("track")) if track_match else None
    title = _clean_track_title(_BRACKET_RE.sub(" ", raw_title))
    artist = None
    artist_title = re.match(r"^(?P<artist>.+?)\s+-\s+(?P<title>.+)$", raw_title)
    if artist_title:
        artist = _clean_artist(artist_title.group("artist"))
        title = _clean_track_title(artist_title.group("title"))
    if ".-." in raw_title:
        parts = [_clean_track_title(part) for part in raw_title.split(".-.") if part.strip()]
        if parts:
            title = parts[0]
        if len(parts) >= 3:
            artist = parts[-1]
    return AudioFileInfo(title=title, artist=artist, track=track)


def _fallback_track_and_title(stem: str) -> tuple[int | None, str]:
    match = re.match(r"^(?P<track>\d{1,3})\s*[-._ ]+\s*(?P<title>.+)$", stem)
    if not match:
        return None, _clean_track_title(_BRACKET_RE.sub(" ", stem))
    return int(match.group("track")), _clean_track_title(_BRACKET_RE.sub(" ", match.group("title")))


def _disc_from_folder(name: str) -> int | None:
    match = re.search(r"\bcd\s*(\d{1,3})\b", name, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _clean_artist(value: str) -> str | None:
    text = _clean_title(value)
    ignored = {"", ".", "..", "music", "downloads", "unknown"}
    return None if text.lower() in ignored else text


def _clean_release_folder(value: str) -> str:
    text = _BRACKET_RE.sub(" ", value)
    text = re.sub(
        r"\b(?:FLAC|MP3|AAC|ALAC|APE|WAV|DSD)\b(?:\s*\d{2,3}(?:[-.]\d{1,3})?)?",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", text).strip(" ._-")


def _int_or_none(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _last_non_initial_year_match(value: str) -> re.Match[str] | None:
    matches = [match for match in _YEAR_RE.finditer(value) if match.start() > 0]
    return matches[-1] if matches else None


def _tv_title_from_path(file_path: Path) -> str:
    parent = file_path.parent
    parent_title = _clean_title(parent.name)
    if not parent_title:
        return ""

    if _is_season_dir(parent_title):
        show_title = _clean_title(parent.parent.name)
        return show_title if show_title.lower() not in _GENERIC_TV_DIRS else ""

    return parent_title if parent_title.lower() not in _GENERIC_TV_DIRS else ""


def _is_season_dir(value: str) -> bool:
    return bool(_SEASON_DIR_RE.match(value) or _CHINESE_SEASON_DIR_RE.match(value))


def _strip_noise(value: str) -> str:
    value = _BRACKET_RE.sub(" ", value)
    parts = re.split(r"[.\s_\-]+", value)
    kept: list[str] = []
    for part in parts:
        lower = part.lower()
        if lower in _NOISE_TOKENS:
            break
        kept.append(part)
    return " ".join(kept)


def _clean_title(value: str) -> str:
    text = re.sub(r"[._]+", " ", value)
    text = re.sub(r"\s*-\s*$", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ._-")
    return text
