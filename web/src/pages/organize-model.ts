import type {
    OrganizerCandidate,
    OrganizerItem,
    OrganizerMatchResult,
} from "@/api/organizer"
import type {
    MediaRow,
    OrganizerKind,
    OrganizerKindSession,
    ScrapeTarget,
    StatusValue,
} from "./organize-types"
import { tvSeriesTitle } from "./organize-tv"

export type {
    MediaRow,
    MetadataEditValues,
    OrganizerKind,
    OrganizerKindSession,
    OrganizerSessionState,
    ScrapeApplyOptions,
    ScrapeTarget,
    StatusValue,
} from "./organize-types"

export {
    ORGANIZER_SESSION_KEY,
    emptyKindSession,
    loadSession,
    persistedViewState,
} from "./organize-session"

export {
    actionKey,
    selectedCandidateMap,
    toggleKey,
    visibleRangeKeys,
} from "./organize-selection"

export {
    errorMessage,
    hasScraperCredentialStatus,
    languageDisplayName,
    pollOrganizerJob,
    scrapeEmptyMessage,
    scrapeFieldChips,
    scrapeResultMessage,
    scraperDisplayName,
    scraperForKind,
    scraperOptionsForKind,
} from "./organize-scrape"

export function buildRows(
    items: OrganizerItem[],
    matches: OrganizerMatchResult[],
    selectedCandidates: Record<string, OrganizerCandidate>,
    kind: OrganizerKind,
    expandedKeys: string[],
): MediaRow[] {
    const matchesByPath = new Map(matches.map((result) => [result.item.path, result.candidates]))
    const expanded = new Set(expandedKeys)
    if (kind === "tv") return buildTvRows(items, matchesByPath, selectedCandidates, expanded)
    if (kind === "music") return buildMusicRows(items, matchesByPath, selectedCandidates)

    const grouped = new Map<string, OrganizerItem[]>()
    for (const item of items.filter((entry) => itemBelongsToKind(entry, kind))) {
        const key = rowKey(item, kind)
        grouped.set(key, [...(grouped.get(key) ?? []), item])
    }
    return Array.from(grouped.entries())
        .map(([key, files]) => rowFromFiles(key, kind, files, matchesByPath, selectedCandidates))
        .sort((a, b) => a.title.localeCompare(b.title))
}

export function mergeMatches(
    session: OrganizerKindSession,
    results: OrganizerMatchResult[],
): OrganizerKindSession {
    const matches = new Map(session.matches.map((result) => [result.item.path, result]))
    const selectedCandidates = { ...session.selectedCandidates }
    for (const result of results) {
        matches.set(result.item.path, result)
        if (!selectedCandidates[result.item.path] && result.candidates[0]) {
            selectedCandidates[result.item.path] = result.candidates[0]
        }
    }
    return {
        ...session,
        matches: Array.from(matches.values()),
        selectedCandidates,
        renamePlan: null,
        renamePlanKey: null,
    }
}

export function scrapeItemsForRows(
    kind: OrganizerKind,
    rows: MediaRow[],
    actionItems: OrganizerItem[],
    fallbackItems: OrganizerItem[],
) {
    if (kind !== "music") {
        return rows.length > 0
            ? rows.flatMap((row) => row.files)
            : actionItems.length > 0 ? actionItems : fallbackItems
    }
    const sourceRows = rows.length > 0
        ? rows.filter((row) => row.depth === 0)
        : buildMusicRows(fallbackItems, new Map(), {})
    return sourceRows.flatMap((row) => searchItemsForRow(row, row.title, row.year, firstMusicArtist(row)))
}

export function scrapeTargetRows(kind: OrganizerKind, rows: MediaRow[], target: ScrapeTarget) {
    if (target === "current") return rows
    const sourceRows = kind === "music" ? rows.filter((row) => row.depth === 0) : rows
    if (target === "missing") {
        return sourceRows.filter((row) => (
            row.metadata !== "yes" || (kind === "music" && row.lyrics !== "yes")
        ))
    }
    if (target === "missing-metadata") {
        return sourceRows.filter((row) => row.metadata !== "yes")
    }
    if (kind !== "music") return []
    return sourceRows.filter((row) => row.lyrics !== "yes")
}

export function searchItemsForRow(
    row: MediaRow,
    query: string,
    year: number | null,
    artist: string,
): OrganizerItem[] {
    const first = row.files[0]
    if (!first) return []
    if (row.kind === "music") {
        return [{
            ...first,
            media_type: "album",
            title: query,
            album: query,
            artist: artist || first.artist,
            year,
        }]
    }
    return row.files.map((item) => ({ ...item, title: query, year }))
}

export function firstMusicArtist(row: MediaRow | null) {
    return row?.files.find((file) => file.artist)?.artist || ""
}

export function candidateKey(candidate: OrganizerCandidate) {
    return `${candidate.source}:${candidate.source_id}`
}

export function candidateInfoLine(candidate: OrganizerCandidate) {
    return [
        candidate.artist,
        candidate.album,
        candidate.release_date || candidate.year,
        candidate.genres.slice(0, 2).join(", "),
        candidate.runtime ? `${candidate.runtime} min` : "",
    ].filter(Boolean).join(" · ")
}

export function activeRowInfoLine(row: MediaRow | null) {
    if (!row) return ""
    const discs = uniqueText(row.files.map((file) => file.disc != null ? `CD${file.disc}` : "").filter(Boolean))
    const tracks = row.files
        .map((file) => file.track)
        .filter((track): track is number => track != null)
        .sort((a, b) => a - b)
    const trackText = tracks.length === 1
        ? `Track ${tracks[0]}`
        : tracks.length > 1
            ? `Tracks ${tracks[0]}-${tracks[tracks.length - 1]}`
            : ""
    return [discs.join(", "), trackText, row.files[0]?.path ? basename(row.files[0].path) : ""]
        .filter(Boolean)
        .join(" · ")
}

export function cleanTrackTitle(file: OrganizerItem) {
    return stripRedundantArtistPrefix(file.metadata_title || file.title || basename(file.path), file.artist)
}

export function itemBelongsToKind(item: OrganizerItem, kind: OrganizerKind) {
    if (kind === "movies") return item.media_type === "movie"
    if (kind === "tv") return item.media_type === "tv"
    return item.media_type === "track" || item.media_type === "album"
}

export function ratingText(rating: number | null | undefined) {
    return typeof rating === "number" ? rating.toFixed(1) : "-"
}

export function parseYear(value: string) {
    const year = Number.parseInt(value.trim(), 10)
    return Number.isFinite(year) && year >= 1800 && year <= 2200 ? year : null
}

export function parseRating(value: string) {
    const rating = Number.parseFloat(value.trim())
    return Number.isFinite(rating) ? rating : null
}

export function parseRuntime(value: string) {
    const runtime = Number.parseInt(value.trim(), 10)
    return Number.isFinite(runtime) && runtime >= 0 ? runtime : null
}

export function splitList(value: string) {
    return value.split(/[,/]/).map((item) => item.trim()).filter(Boolean)
}

export function basename(path: string) {
    return path.split(/[\\/]/).pop() ?? path
}

export function dirname(path: string) {
    return path.split(/[\\/]/).slice(0, -1).join("/") || "/"
}

export function commonFolder(paths: string[]) {
    if (paths.length === 0) return ""
    const splitPaths = paths.map((path) => dirname(path).split(/[\\/]/).filter(Boolean))
    const first = splitPaths[0]
    const common: string[] = []
    for (let index = 0; index < first.length; index += 1) {
        const part = first[index]
        if (splitPaths.every((items) => items[index] === part)) common.push(part)
        else break
    }
    const prefix = paths[0].startsWith("/") ? "/" : ""
    return `${prefix}${common.join("/")}` || dirname(paths[0])
}

function buildMusicRows(
    items: OrganizerItem[],
    matchesByPath: Map<string, OrganizerCandidate[]>,
    selectedCandidates: Record<string, OrganizerCandidate>,
) {
    const albums = new Map<string, OrganizerItem[]>()
    for (const item of items.filter((entry) => itemBelongsToKind(entry, "music"))) {
        const key = rowKey(item, "music")
        albums.set(key, [...(albums.get(key) ?? []), item])
    }

    const rows: MediaRow[] = []
    for (const [key, files] of Array.from(albums.entries()).sort((a, b) => musicSort(a[1], b[1]))) {
        rows.push(rowFromFiles(key, "music", files, matchesByPath, selectedCandidates, {
            subtitle: musicAlbumSubtitle(files),
            expandable: false,
            expanded: false,
        }))
    }
    return rows
}

function buildTvRows(
    items: OrganizerItem[],
    matchesByPath: Map<string, OrganizerCandidate[]>,
    selectedCandidates: Record<string, OrganizerCandidate>,
    expanded: Set<string>,
) {
    const shows = new Map<string, OrganizerItem[]>()
    for (const item of items.filter((entry) => itemBelongsToKind(entry, "tv"))) {
        const key = rowKey(item, "tv")
        shows.set(key, [...(shows.get(key) ?? []), item])
    }

    const rows: MediaRow[] = []
    for (const [key, files] of Array.from(shows.entries()).sort((a, b) => a[1][0].title.localeCompare(b[1][0].title))) {
        const seasons = groupBySeason(files)
        const showRow = rowFromFiles(key, "tv", files, matchesByPath, selectedCandidates, {
            subtitle: tvShowSubtitle(files, seasons.size),
            expandable: seasons.size > 0,
            expanded: expanded.has(key),
        })
        rows.push(showRow)
        if (!expanded.has(key)) continue
        for (const [season, seasonFiles] of Array.from(seasons.entries()).sort((a, b) => a[0] - b[0])) {
            rows.push(rowFromFiles(
                `${key}:season:${season}`,
                "tv",
                seasonFiles,
                matchesByPath,
                selectedCandidates,
                {
                    title: seasonLabel(season),
                    subtitle: `${showRow.title} - ${seasonFiles.length} episode${seasonFiles.length > 1 ? "s" : ""}`,
                    depth: 1,
                    season,
                },
            ))
        }
    }
    return rows
}

export function rowFromFiles(
    key: string,
    kind: OrganizerKind,
    files: OrganizerItem[],
    matchesByPath: Map<string, OrganizerCandidate[]>,
    selectedCandidates: Record<string, OrganizerCandidate>,
    overrides: Partial<Pick<MediaRow, "title" | "subtitle" | "depth" | "expandable" | "expanded" | "season" | "track">> = {},
): MediaRow {
    const candidates = uniqueCandidates(files.flatMap((file) => matchesByPath.get(file.path) ?? []))
    const candidate = firstCandidate(files, selectedCandidates, matchesByPath)
    return {
        key,
        kind,
        title: overrides.title ?? rowDisplayTitle(files, kind),
        subtitle: overrides.subtitle ?? rowSubtitle(files, kind, candidate),
        depth: overrides.depth ?? 0,
        expandable: overrides.expandable ?? false,
        expanded: overrides.expanded ?? false,
        season: overrides.season,
        track: overrides.track,
        year: firstMetadataYear(files) ?? candidate?.year ?? null,
        rating: firstMetadataRating(files) ?? candidate?.rating ?? null,
        ratingSource: firstMetadataRatingSource(files) ?? candidate?.source ?? "",
        isNew: files.some((file) => file.is_new),
        metadata: aggregateStatus(files, "metadata"),
        images: aggregateStatus(files, "images"),
        subtitles: kind === "music" ? "na" : aggregateStatus(files, "subtitles"),
        lyrics: kind === "music" ? aggregateStatus(files, "lyrics") : "na",
        files,
        candidate,
        candidates,
    }
}

function rowKey(item: OrganizerItem, kind: OrganizerKind) {
    if (kind === "movies") return `movie:${item.path}`
    if (kind === "tv") return `tv:${tvSeriesTitle(item).toLowerCase()}`
    return `music:${musicAlbumDirectory(item.path).toLowerCase()}`
}

function musicAlbumDirectory(path: string) {
    const parts = path.split(/[\\/]/)
    parts.pop()
    if (parts.length > 0 && /^cd\s*\d+$/i.test(parts[parts.length - 1] ?? "")) {
        parts.pop()
    }
    return parts.join("/")
}

function rowTitle(item: OrganizerItem, kind: OrganizerKind) {
    if (kind === "music") return item.album || item.title || "Unknown Album"
    return item.title || "Untitled"
}

function firstMetadataTitle(files: OrganizerItem[]) {
    return files.find((file) => file.metadata_title?.trim())?.metadata_title?.trim() ?? null
}

function firstMetadataShowTitle(files: OrganizerItem[]) {
    return files.find((file) => file.metadata_show_title?.trim())?.metadata_show_title?.trim() ?? null
}

function rowDisplayTitle(files: OrganizerItem[], kind: OrganizerKind) {
    if (kind === "tv") return firstMetadataShowTitle(files) ?? tvSeriesTitle(files[0])
    if (kind === "music") return rowTitle(files[0], kind)
    return firstMetadataTitle(files) ?? rowTitle(files[0], kind)
}

function firstMetadataYear(files: OrganizerItem[]) {
    return files.find((file) => file.metadata_year != null)?.metadata_year
        ?? files.find((file) => file.year != null)?.year
        ?? null
}

function firstMetadataRating(files: OrganizerItem[]) {
    return files.find((file) => file.metadata_rating != null)?.metadata_rating ?? null
}

function firstMetadataRatingSource(files: OrganizerItem[]) {
    return files.find((file) => file.metadata_rating_source?.trim())?.metadata_rating_source?.trim() ?? null
}

function rowSubtitle(files: OrganizerItem[], kind: OrganizerKind, candidate?: OrganizerCandidate | null) {
    const metadata = metadataSubtitle(files)
    if (metadata) return metadata
    if (kind === "music") {
        return [
            candidate?.artist || files[0]?.artist,
            candidate?.album || files[0]?.album,
        ].filter(Boolean).join(" - ")
    }
    if (kind === "tv") return `${files.length} episode${files.length > 1 ? "s" : ""}`
    return basename(files[0]?.path ?? "")
}

function tvShowSubtitle(files: OrganizerItem[], seasonCount: number) {
    const metadata = metadataSubtitle(files)
    const countText = `${seasonCount} season${seasonCount > 1 ? "s" : ""} - ${files.length} episode${files.length > 1 ? "s" : ""}`
    return metadata ? `${metadata} - ${countText}` : countText
}

function musicAlbumSubtitle(files: OrganizerItem[]) {
    const artist = firstText(files.map((file) => file.artist))
    const count = `${files.length} track${files.length > 1 ? "s" : ""}`
    return artist ? `${artist} - ${count}` : count
}

function musicSort(a: OrganizerItem[], b: OrganizerItem[]) {
    const artistA = firstText(a.map((file) => file.artist)).toLowerCase()
    const artistB = firstText(b.map((file) => file.artist)).toLowerCase()
    const albumA = firstText(a.map((file) => file.album || file.title)).toLowerCase()
    const albumB = firstText(b.map((file) => file.album || file.title)).toLowerCase()
    return artistA.localeCompare(artistB) || albumA.localeCompare(albumB)
}

function metadataSubtitle(files: OrganizerItem[]) {
    const studios = uniqueText(files.flatMap((file) => file.metadata_studios ?? [])).slice(0, 2)
    const cast = uniqueText(files.flatMap((file) => file.metadata_cast ?? [])).slice(0, 3)
    if (studios.length && cast.length) return `${studios.join(", ")} - ${cast.join(", ")}`
    if (studios.length) return studios.join(", ")
    if (cast.length) return cast.join(", ")
    return ""
}

function groupBySeason(files: OrganizerItem[]) {
    const groups = new Map<number, OrganizerItem[]>()
    for (const file of files) {
        const season = file.season ?? 0
        groups.set(season, [...(groups.get(season) ?? []), file])
    }
    return groups
}

function seasonLabel(season: number) {
    return season === 0 ? "Specials" : `Season ${String(season).padStart(2, "0")}`
}

function aggregateStatus(files: OrganizerItem[], field: "metadata" | "images" | "subtitles" | "lyrics"): StatusValue {
    const count = files.filter((file) => Boolean(file[field])).length
    if (count === 0) return "no"
    if (count === files.length) return "yes"
    return "partial"
}

function firstCandidate(
    files: OrganizerItem[],
    selectedCandidates: Record<string, OrganizerCandidate>,
    matchesByPath: Map<string, OrganizerCandidate[]>,
) {
    for (const file of files) {
        const selected = selectedCandidates[file.path]
        if (selected) return selected
    }
    for (const file of files) {
        const candidate = matchesByPath.get(file.path)?.[0]
        if (candidate) return candidate
    }
    return null
}

export function uniqueCandidates(candidates: OrganizerCandidate[]) {
    const map = new Map<string, OrganizerCandidate>()
    for (const candidate of candidates) map.set(candidateKey(candidate), candidate)
    return Array.from(map.values())
}

function firstText(values: Array<string | null | undefined>) {
    return values.find((value) => value?.trim())?.trim() ?? ""
}

export function uniqueText(values: string[]) {
    const seen = new Set<string>()
    const result: string[] = []
    for (const value of values) {
        const text = value.trim()
        const key = text.toLowerCase()
        if (!text || seen.has(key)) continue
        seen.add(key)
        result.push(text)
    }
    return result
}

function stripRedundantArtistPrefix(title: string, artist?: string | null) {
    const normalizedArtist = artist?.trim()
    if (!normalizedArtist) return title
    const escaped = normalizedArtist.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    return title.replace(new RegExp(`^${escaped}(?:\\s*[-–—:]\\s*|\\s+)(.+)$`, "i"), "$1").trim()
}
