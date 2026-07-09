"""Movie and TV scraper adapters."""

from __future__ import annotations

from typing import Any

from mm.config import ScraperSourceConfig
from mm.organizer.scraper_core import (
    HttpJsonClient,
    ScrapeCandidate,
    ScrapeQuery,
    confidence,
    float_or_none,
    int_or_none,
    year_from_date,
)


class TmdbScraper:
    name = "tmdb"

    def __init__(self, source: ScraperSourceConfig, *, language: str, timeout: float) -> None:
        self.source = source
        self.language = source.language or language
        self.client = HttpJsonClient(timeout)

    def _auth(self) -> tuple[dict[str, object], dict[str, str]] | None:
        credential_params: dict[str, object] = {}
        headers: dict[str, str] = {"Accept": "application/json"}
        access_token = self.source.credentials.get("access_token", "").strip()
        api_key = self.source.credentials.get("api_key", "").strip()
        if access_token:
            headers["Authorization"] = "******"
        elif api_key:
            credential_params["api_key"] = api_key
        else:
            return None
        return credential_params, headers

    def search(self, query: ScrapeQuery, *, limit: int = 5) -> list[ScrapeCandidate]:
        if query.media_type not in {"movie", "tv"}:
            return []
        auth = self._auth()
        if not auth:
            return []
        credential_params, headers = auth
        kind = "movie" if query.media_type == "movie" else "tv"
        params: dict[str, object] = {
            **credential_params,
            "query": query.title,
            "language": self.language,
            "include_adult": "false",
            "page": 1,
        }
        if query.year:
            params["primary_release_year" if kind == "movie" else "first_air_date_year"] = (
                query.year
            )
        data = self.client.get(f"{self.source.base_url.rstrip('/')}/search/{kind}", params, headers)
        raw_results = data.get("results", [])
        if not isinstance(raw_results, list):
            return []
        return [
            self._candidate(item, query, kind)
            for item in raw_results[:limit]
            if isinstance(item, dict) and item.get("id")
        ]

    def _candidate(self, item: dict[str, Any], query: ScrapeQuery, kind: str) -> ScrapeCandidate:
        title = str(item.get("title" if kind == "movie" else "name") or "")
        original = str(item.get("original_title" if kind == "movie" else "original_name") or "")
        date = str(item.get("release_date" if kind == "movie" else "first_air_date") or "")
        year = year_from_date(date)
        poster_path = str(item.get("poster_path") or "")
        return ScrapeCandidate(
            source=self.name,
            source_id=str(item["id"]),
            media_type="movie" if kind == "movie" else "tv",
            title=title,
            original_title=original,
            year=year,
            overview=str(item.get("overview") or ""),
            poster_url=f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "",
            rating=float_or_none(item.get("vote_average")),
            confidence=confidence(query.title, title, query.year, year),
        )

    def details(
        self,
        candidate: ScrapeCandidate,
        query: ScrapeQuery | None = None,
    ) -> ScrapeCandidate:
        if candidate.media_type not in {"movie", "tv"}:
            return candidate
        auth = self._auth()
        if not auth:
            return candidate
        credential_params, headers = auth
        kind = "movie" if candidate.media_type == "movie" else "tv"
        data = self.client.get(
            f"{self.source.base_url.rstrip('/')}/{kind}/{candidate.source_id}",
            {
                **credential_params,
                "language": self.language,
                "append_to_response": (
                    "credits,videos,images,release_dates,external_ids"
                    if kind == "movie"
                    else "credits,videos,images,content_ratings,external_ids"
                ),
                "include_image_language": f"{self.language[:2]},en,null",
            },
            headers,
        )
        season_data: dict[str, Any] | None = None
        episode_data: dict[str, Any] | None = None
        if kind == "tv" and query and query.season is not None:
            season_data = self.client.get(
                f"{self.source.base_url.rstrip('/')}/tv/{candidate.source_id}/season/{query.season}",
                {**credential_params, "language": self.language},
                headers,
            )
            if query.episode is not None:
                episode_data = self.client.get(
                    (
                        f"{self.source.base_url.rstrip('/')}/tv/{candidate.source_id}"
                        f"/season/{query.season}/episode/{query.episode}"
                    ),
                    {
                        **credential_params,
                        "language": self.language,
                        "append_to_response": "credits,external_ids",
                    },
                    headers,
                )
        return _tmdb_details_candidate(data, candidate, kind, query, season_data, episode_data)


class OmdbScraper:
    name = "omdb"

    def __init__(self, source: ScraperSourceConfig, *, timeout: float) -> None:
        self.source = source
        self.client = HttpJsonClient(timeout)

    def search(self, query: ScrapeQuery, *, limit: int = 5) -> list[ScrapeCandidate]:
        if query.media_type not in {"movie", "tv"}:
            return []
        api_key = self.source.credentials.get("api_key", "").strip()
        if not api_key:
            return []
        data = self.client.get(
            self.source.base_url,
            {
                "apikey": api_key,
                "s": query.title,
                "type": "movie" if query.media_type == "movie" else "series",
                "y": query.year,
                "r": "json",
            },
        )
        raw_results = data.get("Search", [])
        if not isinstance(raw_results, list):
            return []
        candidates: list[ScrapeCandidate] = []
        for item in raw_results[:limit]:
            if not isinstance(item, dict) or not item.get("imdbID"):
                continue
            year = year_from_date(str(item.get("Year") or ""))
            title = str(item.get("Title") or "")
            candidates.append(
                ScrapeCandidate(
                    source=self.name,
                    source_id=str(item["imdbID"]),
                    media_type="movie" if item.get("Type") == "movie" else "tv",
                    title=title,
                    year=year,
                    poster_url="" if item.get("Poster") == "N/A" else str(item.get("Poster") or ""),
                    confidence=confidence(query.title, title, query.year, year),
                )
            )
        return candidates


def _tmdb_details_candidate(
    item: dict[str, Any],
    candidate: ScrapeCandidate,
    kind: str,
    query: ScrapeQuery | None = None,
    season_item: dict[str, Any] | None = None,
    episode_item: dict[str, Any] | None = None,
) -> ScrapeCandidate:
    show_title = str(item.get("name") or candidate.title) if kind == "tv" else ""
    title = str(item.get("title" if kind == "movie" else "name") or candidate.title)
    original = str(
        item.get("original_title" if kind == "movie" else "original_name")
        or candidate.original_title
    )
    date = str(item.get("release_date" if kind == "movie" else "first_air_date") or "")
    if kind == "tv" and episode_item:
        title = str(episode_item.get("name") or title)
        date = str(episode_item.get("air_date") or date)
    images = item.get("images") if isinstance(item.get("images"), dict) else {}
    poster = _tmdb_image_url(str(item.get("poster_path") or ""), size="w780")
    backdrop = _tmdb_image_url(str(item.get("backdrop_path") or ""), size="original")
    season_poster = (
        _tmdb_image_url(str(season_item.get("poster_path") or ""), size="w780")
        if season_item
        else ""
    )
    poster_url = season_poster or poster or _image_from_list(images.get("posters"), size="w780")
    return ScrapeCandidate(
        source=candidate.source,
        source_id=candidate.source_id,
        media_type=candidate.media_type,
        title=title,
        original_title=original,
        show_title=show_title,
        artist=candidate.artist,
        album=candidate.album,
        year=year_from_date(date) or candidate.year,
        overview=str(
            (episode_item or {}).get("overview") or item.get("overview") or candidate.overview
        ),
        poster_url=poster_url or candidate.poster_url,
        backdrop_url=backdrop or _image_from_list(images.get("backdrops"), size="original"),
        logo_url=_image_from_list(images.get("logos"), size="w500"),
        trailer_url=_trailer_url(item.get("videos")),
        release_date=date,
        certification=_certification(item, kind),
        runtime=_runtime(episode_item or item),
        status=str(item.get("status") or ""),
        original_language=str(item.get("original_language") or ""),
        genres=_names(item.get("genres")),
        countries=_country_names(item.get("production_countries")),
        studios=_names(item.get("production_companies")),
        external_ids=_external_ids(
            (episode_item or item).get("external_ids") or item.get("external_ids")
        ),
        cast=_cast((episode_item or item).get("credits") or item.get("credits")),
        crew=_crew((episode_item or item).get("credits") or item.get("credits")),
        rating=float_or_none((episode_item or item).get("vote_average")) or candidate.rating,
        confidence=candidate.confidence,
    )


def _tmdb_image_url(path: str, *, size: str = "w500") -> str:
    return f"https://image.tmdb.org/t/p/{size}{path}" if path else ""


def _image_from_list(value: Any, *, size: str) -> str:
    if not isinstance(value, list):
        return ""
    for item in value:
        if isinstance(item, dict) and item.get("file_path"):
            return _tmdb_image_url(str(item["file_path"]), size=size)
    return ""


def _trailer_url(value: Any) -> str:
    results = value.get("results") if isinstance(value, dict) else None
    if not isinstance(results, list):
        return ""
    for item in results:
        if (
            isinstance(item, dict)
            and item.get("site") == "YouTube"
            and item.get("key")
            and item.get("type") in {"Trailer", "Teaser"}
        ):
            return f"https://www.youtube.com/watch?v={item['key']}"
    return ""


def _certification(item: dict[str, Any], kind: str) -> str:
    key = "release_dates" if kind == "movie" else "content_ratings"
    raw = item.get(key)
    results = raw.get("results") if isinstance(raw, dict) else None
    if not isinstance(results, list):
        return ""
    preferred = ["US", "GB", "CN", "JP", "KR"]
    sorted_results = sorted(
        (entry for entry in results if isinstance(entry, dict)),
        key=lambda entry: (
            preferred.index(entry.get("iso_3166_1")) if entry.get("iso_3166_1") in preferred else 99
        ),
    )
    for entry in sorted_results:
        if kind == "tv":
            rating = str(entry.get("rating") or "")
            if rating:
                return rating
        releases = entry.get("release_dates")
        if isinstance(releases, list):
            for release in releases:
                if isinstance(release, dict) and release.get("certification"):
                    return str(release["certification"])
    return ""


def _runtime(item: dict[str, Any]) -> int | None:
    if item.get("runtime"):
        return int_or_none(item.get("runtime"))
    episode_run_time = item.get("episode_run_time")
    if isinstance(episode_run_time, list) and episode_run_time:
        return int_or_none(episode_run_time[0])
    return None


def _names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item.get("name")) for item in value if isinstance(item, dict) and item.get("name")]


def _country_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        str(item.get("name") or item.get("iso_3166_1"))
        for item in value
        if isinstance(item, dict) and (item.get("name") or item.get("iso_3166_1"))
    ]


def _external_ids(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, label in (
        ("imdb_id", "imdb"),
        ("tvdb_id", "tvdb"),
        ("wikidata_id", "wikidata"),
        ("facebook_id", "facebook"),
        ("instagram_id", "instagram"),
        ("twitter_id", "twitter"),
    ):
        raw = value.get(key)
        if raw:
            result[label] = str(raw)
    return result


def _cast(value: Any) -> list[dict[str, str]]:
    cast = value.get("cast") if isinstance(value, dict) else None
    if not isinstance(cast, list):
        return []
    return [
        {"name": str(item.get("name") or ""), "role": str(item.get("character") or "")}
        for item in cast[:20]
        if isinstance(item, dict) and item.get("name")
    ]


def _crew(value: Any) -> list[dict[str, str]]:
    crew = value.get("crew") if isinstance(value, dict) else None
    if not isinstance(crew, list):
        return []
    wanted = {"Director", "Writer", "Screenplay", "Producer", "Executive Producer", "Creator"}
    return [
        {"name": str(item.get("name") or ""), "job": str(item.get("job") or "")}
        for item in crew
        if isinstance(item, dict) and item.get("name") and item.get("job") in wanted
    ][:30]
