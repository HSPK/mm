import type { OrganizerItem } from "@/api/organizer"
import { config } from "@/lib/config"
import type { MediaRow } from "./organize-model"
import { basename, commonFolder, uniqueText } from "./organize-model"

export function rowMetadata(row: MediaRow) {
    const files = row.files
    return {
        title: row.title,
        originalTitle: firstText(files.map((file) => file.metadata_original_title)),
        year: row.year,
        premiered: firstText(files.map((file) => file.metadata_premiered)),
        certification: firstText(files.map((file) => file.metadata_certification)),
        runtime: firstNumber(files.map((file) => file.metadata_runtime)),
        genres: uniqueText(files.flatMap((file) => file.metadata_genres ?? [])),
        styles: uniqueText(files.flatMap((file) => file.metadata_styles ?? [])),
        composers: uniqueText(files.flatMap((file) => file.metadata_composers ?? [])),
        status: firstText(files.map((file) => file.metadata_status)),
        countries: uniqueText(files.flatMap((file) => file.metadata_countries ?? [])),
        tagline: firstText(files.map((file) => file.metadata_tagline)),
        plot: firstText(files.map((file) => file.metadata_plot)),
        lyrics: firstText(files.map((file) => file.metadata_lyrics)),
        syncedLyrics: firstText(files.map((file) => file.metadata_synced_lyrics)),
        tags: uniqueText(files.flatMap((file) => file.metadata_tags ?? [])),
        ids: mergeIds(files.map((file) => file.metadata_ids ?? {})),
        rating: row.rating,
        ratingSource: firstText(files.map((file) => file.metadata_rating_source)) || row.candidate?.source || "",
        studios: uniqueText(files.flatMap((file) => file.metadata_studios ?? [])),
        cast: uniqueText(files.flatMap((file) => file.metadata_cast ?? [])),
        path: commonFolder(files.map((file) => file.path)),
    }
}

export function musicArtists(row: MediaRow) {
    return uniqueText([
        row.candidate?.artist,
        ...row.files.map((file) => file.artist),
    ].filter(Boolean) as string[])
}

export function musicDiscText(row: MediaRow) {
    const discs = uniqueText(
        row.files
            .map((file) => file.disc)
            .filter((disc): disc is number => disc != null)
            .map((disc) => `Disc ${disc}`),
    )
    return discs.join(", ")
}

export function rowRelatedFiles(row: MediaRow) {
    const seen = new Set<string>()
    const result: NonNullable<OrganizerItem["related_files"]> = []
    for (const file of row.files.flatMap((item) => item.related_files ?? [])) {
        if (seen.has(file.path)) continue
        seen.add(file.path)
        result.push(file)
    }
    if (result.length === 0) {
        return row.files.map((file) => ({
            kind: file.media_type === "track" ? "audio" : "video",
            path: file.path,
            name: basename(file.path),
            extension: file.path.includes(".") ? `.${file.path.split(".").pop()}` : "",
            size: null,
        }))
    }
    return result.sort((a, b) => fileKindRank(a.kind) - fileKindRank(b.kind) || a.name.localeCompare(b.name))
}

export function rowArtworkAssets(row: MediaRow) {
    const seen = new Set<string>()
    const assets: NonNullable<OrganizerItem["artwork"]> = []
    for (const file of row.files) {
        for (const asset of file.artwork ?? []) {
            if (!artworkBelongsToRow(asset, row)) continue
            if (seen.has(asset.path)) continue
            seen.add(asset.path)
            assets.push({ ...asset, playback_id: file.playback_id })
        }
    }
    return assets
}

export function dimensionsText(asset?: { width?: number | null, height?: number | null }) {
    return asset?.width && asset?.height ? `${asset.width}x${asset.height}` : "Detected"
}

export function artworkAspectRatio(asset: { kind?: string, width?: number | null, height?: number | null }) {
    if (asset.width && asset.height) return `${asset.width} / ${asset.height}`
    if (asset.kind === "poster") return "2 / 3"
    if (asset.kind === "banner") return "5 / 1"
    return "16 / 9"
}

export function formatBytes(value: number) {
    if (value < 1024) return `${value} B`
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
    if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`
    return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`
}

export function formatDuration(seconds?: number | null) {
    if (!seconds) return ""
    const total = Math.round(seconds)
    const hours = Math.floor(total / 3600)
    const minutes = Math.floor((total % 3600) / 60)
    const secs = total % 60
    if (hours > 0) return `${hours}h ${minutes}m ${secs}s`
    if (minutes > 0) return `${minutes}m ${secs}s`
    return `${secs}s`
}

export function bitrateText(value?: number | null) {
    if (!value) return "-"
    if (value >= 1_000_000) return `${Math.round(value / 1000)} kbps`
    if (value >= 1000) return `${Math.round(value / 1000)} kbps`
    return `${value} bps`
}

export function resolutionText(mediaInfo: OrganizerItem["media_info"] | null) {
    if (!mediaInfo?.width || !mediaInfo.height) return ""
    const ratio = mediaInfo.aspect_ratio ? ` (${mediaInfo.aspect_ratio})` : ""
    return `${mediaInfo.width}x${mediaInfo.height}${ratio}`
}

export function artworkImageSrc(asset: { path: string; playback_id?: string | null }) {
    if (/^https?:\/\//i.test(asset.path)) return asset.path
    if (!asset.playback_id) return ""
    return `${config.apiBaseUrl}/organizer/artwork/image/item/${encodeURIComponent(asset.playback_id)}`
}

function artworkBelongsToRow(asset: NonNullable<OrganizerItem["artwork"]>[number], row: MediaRow) {
    if (row.kind !== "tv") return true
    const seasonMatch = asset.label.toLowerCase().match(/season[ ._-]?(\d{1,3})/)
    if (row.season != null) {
        return seasonMatch ? Number(seasonMatch[1]) === row.season : false
    }
    return !seasonMatch
}

function fileKindRank(kind: string) {
    if (kind === "video" || kind === "audio") return 0
    if (kind === "metadata") return 1
    if (kind === "subtitle") return 2
    if (["poster", "fanart", "banner", "image"].includes(kind)) return 3
    return 4
}

function firstText(values: Array<string | null | undefined>) {
    return values.find((value) => value?.trim())?.trim() ?? ""
}

function firstNumber(values: Array<number | null | undefined>) {
    return values.find((value) => typeof value === "number") ?? null
}

function mergeIds(values: Array<Record<string, string>>) {
    return values.reduce<Record<string, string>>((acc, ids) => ({ ...acc, ...ids }), {})
}
