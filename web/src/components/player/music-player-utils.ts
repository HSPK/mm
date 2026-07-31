import { config } from "@/lib/config"
import type { PlayerTrack, RepeatMode } from "@/stores/player"

export interface LyricLine {
    time: number
    text: string
}

export interface AudioInfoResponse {
    duration?: number | null
}

export function parseLyrics(track: PlayerTrack | null) {
    const synced = parseSyncedLyrics(track?.syncedLyrics)
    const plainSource = synced.length > 0 ? "" : track?.lyrics || track?.syncedLyrics || ""
    const plain = plainSource.split(/\r?\n/).map((line) => line.trim())
    while (plain[0] === "") plain.shift()
    while (plain[plain.length - 1] === "") plain.pop()
    return { synced, plain }
}

export function parseSyncedLyrics(value?: string) {
    if (!value) return []
    const lines: LyricLine[] = []
    const offset = Number(value.match(/^\[offset:([+-]?\d+)\]$/im)?.[1] ?? 0) / 1000
    for (const row of value.split(/\r?\n/)) {
        const matches = [...row.matchAll(/\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]/g)]
        if (matches.length === 0) continue
        const text = row.replace(/\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]/g, "").trim()
        for (const match of matches) {
            const minutes = Number(match[1])
            const seconds = Number(match[2])
            if (seconds >= 60) continue
            const fraction = match[3] ? Number(match[3].padEnd(3, "0").slice(0, 3)) / 1000 : 0
            lines.push({ time: Math.max(0, minutes * 60 + seconds + fraction + offset), text })
        }
    }
    return lines.sort((a, b) => a.time - b.time)
}

export function activeLyricLine(lines: LyricLine[], currentTime: number) {
    const target = currentTime + 0.15
    let low = 0
    let high = lines.length - 1
    let active = -1
    while (low <= high) {
        const middle = Math.floor((low + high) / 2)
        if (lines[middle].time <= target) {
            active = middle
            low = middle + 1
        } else {
            high = middle - 1
        }
    }
    return active
}

export function repeatLabel(repeatMode: RepeatMode) {
    if (repeatMode === "one") return "Repeat one"
    if (repeatMode === "all") return "Repeat all"
    return "Repeat off"
}

export function validDuration(duration: number) {
    return Number.isFinite(duration) && duration > 0 ? duration : null
}

export function isKeyboardControlTarget(target: EventTarget | null) {
    return target instanceof HTMLElement
        && !!target.closest('button, input, textarea, select, [contenteditable="true"]')
}

export function formatTime(seconds: number) {
    if (!Number.isFinite(seconds) || seconds <= 0) return "0:00"
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor(seconds / 60) % 60
    const secs = Math.floor(seconds % 60)
    if (hours > 0) return `${hours}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`
    return `${mins}:${String(secs).padStart(2, "0")}`
}

export function organizerFileUrl(playbackId: string, signedUrl?: string) {
    if (signedUrl && typeof window !== "undefined") {
        const apiOrigin = new URL(config.apiBaseUrl, window.location.href).origin
        return new URL(signedUrl, apiOrigin).href
    }
    const params = new URLSearchParams({ playback_id: playbackId })
    return `${config.apiBaseUrl}/player/audio?${params.toString()}`
}

export function usesCrossOriginApi() {
    if (typeof window === "undefined") return false
    return new URL(config.apiBaseUrl, window.location.href).origin !== window.location.origin
}
