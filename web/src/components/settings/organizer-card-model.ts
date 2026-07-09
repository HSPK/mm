import type { OrganizerSourceStatus } from "@/api/organizer"

export const credentialFields: Record<string, string[]> = {
    tmdb: ["api_key", "access_token"],
    omdb: ["api_key"],
    tvdb: ["api_key", "pin"],
    musicbrainz: ["user_agent", "oauth_client_id", "oauth_client_secret"],
    itunes: [],
    netease: [],
    qqmusic: [],
}

export const languageOptions = [
    { value: "zh-CN", label: "简体中文 (zh-CN)" },
    { value: "zh-TW", label: "繁體中文 (zh-TW)" },
    { value: "en-US", label: "English (en-US)" },
    { value: "ja-JP", label: "日本語 (ja-JP)" },
    { value: "ko-KR", label: "한국어 (ko-KR)" },
]

export const lyricsSourceOptions = [
    { value: "lrclib", label: "LRCLIB" },
    { value: "netease", label: "网易云" },
    { value: "qq", label: "QQ Music" },
    { value: "all", label: "All sources" },
]

export function formatSourceName(name: string) {
    const labels: Record<string, string> = {
        tmdb: "TMDb",
        omdb: "OMDb",
        tvdb: "TVDb",
        musicbrainz: "MusicBrainz",
        itunes: "iTunes",
        netease: "网易云",
        qqmusic: "QQ Music",
    }
    return labels[name] ?? name
}

export function scraperOptionsForKind(
    sources: OrganizerSourceStatus[],
    kind: "movies" | "tv" | "music",
) {
    const allowed = kind === "music"
        ? new Set(["musicbrainz", "itunes", "netease", "qqmusic"])
        : new Set(["tmdb", "omdb"])
    const options = sources.filter((source) => source.enabled && source.implemented && allowed.has(source.name))
    if (options.length > 0) return options
    return sources.filter((source) => source.implemented && allowed.has(source.name))
}

export function defaultScraperFallback(kind: "movies" | "tv" | "music") {
    return kind === "music" ? "musicbrainz" : "tmdb"
}
