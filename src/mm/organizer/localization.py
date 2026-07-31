from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

_CHINESE_ARTIST_ALIASES = {
    "fayewong": "王菲",
    "fishleong": "梁静茹",
    "gem": "邓紫棋",
    "gem邓紫棋": "邓紫棋",
    "jaychou": "周杰伦",
    "jjlin": "林俊杰",
    "leehomwang": "王力宏",
    "sunyanzi": "孙燕姿",
    "wangleehom": "王力宏",
}
_CHINESE_CANONICAL_ARTISTS = frozenset(_CHINESE_ARTIST_ALIASES.values())


def localized_variants(
    value: str,
    aliases: Any = None,
    *,
    language: str = "und",
) -> dict[str, str]:
    variants: dict[str, str] = {}
    if value.strip():
        variants[normalize_language(language)] = value.strip()
    if isinstance(aliases, list):
        ordered = sorted(
            (alias for alias in aliases if isinstance(alias, dict)),
            key=lambda alias: bool(alias.get("primary")),
        )
        for alias in ordered:
            name = str(alias.get("name") or "").strip()
            if not name:
                continue
            locale = normalize_language(str(alias.get("locale") or "und"))
            if locale == "und" and "und" in variants:
                continue
            variants[locale] = name
    return variants


def select_localized_name(
    variants: dict[str, str] | None,
    language: str,
    fallback: str,
) -> str:
    if not variants:
        return fallback
    normalized = {
        normalize_language(locale): value.strip()
        for locale, value in variants.items()
        if value and value.strip()
    }
    target = normalize_language(language)
    for locale in language_fallbacks(language):
        if normalized.get(locale):
            value = normalized[locale]
            return _convert_chinese(value, target) if target.startswith("zh") else value
    if target.startswith("zh-") or target == "zh":
        chinese = next(
            (
                value
                for locale, value in normalized.items()
                if locale == "zh" or locale.startswith("zh-")
            ),
            None,
        )
        if chinese:
            return _convert_chinese(chinese, target)
    return normalized.get("und") or fallback or next(iter(normalized.values()), "")


def merge_localized_variants(
    *variants: dict[str, str] | None,
) -> dict[str, str]:
    merged: dict[str, str] = {}
    for values in variants:
        if values:
            merged.update(
                {normalize_language(locale): value for locale, value in values.items() if value}
            )
    return merged


def language_fallbacks(language: str) -> tuple[str, ...]:
    normalized = normalize_language(language)
    if normalized == "zh-cn":
        return "zh-cn", "zh-hans", "zh"
    if normalized in {"zh-tw", "zh-hk", "zh-mo"}:
        return normalized, "zh-hant", "zh"
    if "-" in normalized:
        return normalized, normalized.split("-", 1)[0]
    return (normalized,)


def normalize_language(language: str) -> str:
    return language.strip().replace("_", "-").lower() or "und"


def canonicalize_music_artist(value: str | None) -> str | None:
    if not value:
        return value
    parts = [
        part.strip()
        for part in re.split(r"\s*(?:,|，|、|&|\+)\s*", value)
        if part.strip()
    ]
    canonical = [
        _CHINESE_ARTIST_ALIASES.get(_artist_key(part), part)
        for part in parts
    ]
    return ", ".join(canonical) if canonical else value


def is_known_chinese_artist(value: str | None) -> bool:
    canonical = canonicalize_music_artist(value)
    return bool(canonical and canonical in _CHINESE_CANONICAL_ARTISTS)


def _artist_key(value: str) -> str:
    return "".join(
        character
        for character in value.casefold()
        if character.isalnum()
    )


@lru_cache(maxsize=2)
def _opencc(config: str):  # noqa: ANN202 - optional dependency type
    try:
        from opencc import OpenCC
    except ImportError:
        return None
    return OpenCC(config)


def _convert_chinese(value: str, language: str) -> str:
    if language == "zh":
        return value
    config = "t2s" if language in {"zh-cn", "zh-hans"} else "s2t"
    converter = _opencc(config)
    return converter.convert(value) if converter else value
