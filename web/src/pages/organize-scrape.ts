import axios from "axios"
import type { OrganizerConfig } from "@/api/organizer"
import { jobsRepo } from "@/api/jobs"
import { notify } from "@/stores/notifications"
import type { OrganizerKind, ScrapeTarget } from "./organize-types"

export async function pollOrganizerJob(jobId: string, notificationId: number) {
    while (true) {
        const job = await jobsRepo.job(jobId)
        notify.update(notificationId, {
            kind: job.status === "error" ? "error" : job.status === "done" ? "success" : "task",
            status: job.status === "error" ? "error" : job.status === "done" ? "done" : "active",
            jobId: job.id,
            title: job.title,
            message: job.message,
            detail: job.detail,
            progress: job.progress,
        })
        if (["done", "error", "canceled"].includes(job.status)) return job
        await new Promise((resolve) => window.setTimeout(resolve, 900))
    }
}

export function errorMessage(error: unknown) {
    if (axios.isAxiosError<{ detail?: string }>(error)) {
        return error.response?.data?.detail ?? error.message
    }
    return error instanceof Error ? error.message : "Unknown error"
}

export function scraperOptionsForKind(config: OrganizerConfig | null, kind: OrganizerKind) {
    const allowed = kind === "music"
        ? new Set(["musicbrainz", "itunes", "netease", "qqmusic"])
        : new Set(["tmdb", "omdb"])
    return config?.sources
        .filter((source) => source.enabled && source.implemented && allowed.has(source.name))
        .map((source) => source.name) ?? []
}

export function scraperForKind(kind: OrganizerKind, current: string, options: string[]) {
    return options.includes(current) ? current : defaultScraperForKind(kind)
}

export function scraperDisplayName(source: string) {
    const normalized = source.toLowerCase()
    if (normalized === "tmdb") return "themoviedb.org"
    if (normalized === "musicbrainz") return "MusicBrainz"
    if (normalized === "itunes") return "iTunes"
    if (normalized === "netease") return "网易云"
    if (normalized === "qqmusic") return "QQ Music"
    if (normalized === "omdb") return "OMDb"
    return source || "Auto scraper"
}

export function scrapeFieldChips(kind: OrganizerKind) {
    if (kind === "music") {
        return ["Artist", "Album", "Tracks", "Release date", "Label", "Catalog no.", "Barcode", "Cover"]
    }
    return ["Title", "Original title", "Year", "Rating", "Plot", "Genres", "Studio", "Actors", "Poster", "Fanart", "Banner"]
}

export function languageDisplayName(language: string) {
    const labels: Record<string, string> = {
        "zh-CN": "Chinese (Simplified)",
        "zh-TW": "Chinese (Traditional)",
        "en-US": "English (United States)",
        "ja-JP": "Japanese",
        "ko-KR": "Korean",
    }
    return labels[language] ?? language
}

export function hasScraperCredentialStatus(statuses: OrganizerConfig["sources"], source: string) {
    const status = statuses.find((item) => item.name === source)
    if (!status) return false
    if (["itunes", "netease", "qqmusic"].includes(source)) return true
    return status.has_credentials
}

export function scrapeEmptyMessage(target: ScrapeTarget, kind: OrganizerKind) {
    if (target === "missing") {
        return kind === "music"
            ? "All visible music rows already have metadata and lyrics."
            : "All visible rows already have metadata."
    }
    if (target === "missing-metadata") return "All visible rows already have metadata."
    if (target === "missing-lyrics") {
        return kind === "music"
            ? "All visible music rows already have lyrics."
            : "Lyrics scraping is only available for music."
    }
    return "Select media or sync sources before scraping."
}

export function scrapeResultMessage(job: Awaited<ReturnType<typeof jobsRepo.job>>) {
    const metadata = numberResult(job.result.metadata)
    const artwork = numberResult(job.result.artwork)
    const failures = Array.isArray(job.result.failures) ? job.result.failures.length : 0
    if (metadata == null && artwork == null && failures === 0) return job.message
    const parts = [
        metadata != null ? `${metadata} metadata` : "",
        artwork != null ? `${artwork} artwork` : "",
        failures > 0 ? `${failures} failed` : "",
    ].filter(Boolean)
    return parts.length > 0 ? `Scrape result: ${parts.join(", ")}` : job.message
}

function defaultScraperForKind(kind: OrganizerKind) {
    return kind === "music" ? "musicbrainz" : "tmdb"
}

function numberResult(value: unknown) {
    return typeof value === "number" && Number.isFinite(value) ? value : null
}
