const durations = new Map<string, number>()
const MAX_DURATIONS = 512

export function cachedMusicDuration(playbackId?: string | null) {
    if (!playbackId) return undefined
    return durations.get(playbackId)
}

export function cacheMusicDuration(playbackId: string | null | undefined, duration: number) {
    if (!playbackId || !Number.isFinite(duration) || duration <= 0) return
    durations.delete(playbackId)
    durations.set(playbackId, duration)
    while (durations.size > MAX_DURATIONS) {
        const oldest = durations.keys().next().value
        if (oldest === undefined) break
        durations.delete(oldest)
    }
}

export function clearMusicMediaCache() {
    durations.clear()
}
