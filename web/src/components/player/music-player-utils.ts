import { browserTokenStorage } from "@/lib/token-storage"
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
    const plain = plainSource.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
    return { synced, plain }
}

export function parseSyncedLyrics(value?: string) {
    if (!value) return []
    const lines: LyricLine[] = []
    for (const row of value.split(/\r?\n/)) {
        const matches = [...row.matchAll(/\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]/g)]
        if (matches.length === 0) continue
        const text = row.replace(/\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]/g, "").trim()
        for (const match of matches) {
            const minutes = Number(match[1])
            const seconds = Number(match[2])
            const fraction = match[3] ? Number(match[3].padEnd(3, "0").slice(0, 3)) / 1000 : 0
            lines.push({ time: minutes * 60 + seconds + fraction, text })
        }
    }
    return lines.sort((a, b) => a.time - b.time)
}

export function activeLyricLine(lines: LyricLine[], currentTime: number) {
    let active = -1
    for (let index = 0; index < lines.length; index += 1) {
        if (lines[index].time <= currentTime + 0.15) active = index
        else break
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

export function organizerFileUrl(playbackId: string) {
    const params = new URLSearchParams({ playback_id: playbackId })
    const token = browserTokenStorage.get()
    if (token) params.set("token", token)
    return `${config.apiBaseUrl}/player/audio?${params.toString()}`
}
