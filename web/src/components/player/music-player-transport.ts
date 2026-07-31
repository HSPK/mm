export function seekAudio(
    audio: Pick<HTMLAudioElement, "currentTime" | "duration">,
    requestedTime: number,
) {
    const target = Number.isFinite(requestedTime) ? Math.max(0, requestedTime) : 0
    const duration = Number.isFinite(audio.duration) && audio.duration > 0
        ? audio.duration
        : null
    const position = duration == null ? target : Math.min(target, duration)
    audio.currentTime = position
    return position
}
