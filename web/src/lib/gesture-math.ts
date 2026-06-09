// Pure helpers for the video gesture layer. Kept side-effect-free so they
// can be unit-tested without touching the DOM.

export type GestureAxis = "horizontal" | "vertical"
export type GestureKind = "seek" | "volume" | "brightness" | "speed" | null

export interface TouchPoint {
    x: number
    y: number
    time: number
}

/** Minimum total movement (px) before we commit to an axis. */
export const AXIS_LOCK_PX = 10

/** Minimum hold time (ms) to trigger long-press 2x. */
export const LONG_PRESS_MS = 500

/** Maximum tap movement (px) to still count as a tap, not a drag. */
export const TAP_SLOP_PX = 10

/** Time within which a second tap counts as a double-tap. */
export const DOUBLE_TAP_MS = 280

/** Seek seconds covered by a full-screen-width horizontal drag. */
export const SEEK_FULL_WIDTH_SECONDS = 90

/** Double-tap seek step in seconds (Bilibili default). */
export const DOUBLE_TAP_SEEK_SECONDS = 10

/** Returns the dominant axis once movement crosses `AXIS_LOCK_PX`, else null. */
export function detectAxis(dx: number, dy: number): GestureAxis | null {
    const ax = Math.abs(dx)
    const ay = Math.abs(dy)
    if (Math.max(ax, ay) < AXIS_LOCK_PX) return null
    return ax > ay ? "horizontal" : "vertical"
}

/**
 * Map vertical drag to a 0..1 delta. Drag UP is positive (increase), drag
 * DOWN is negative. Sensitivity is normalized to container height so the
 * gesture feels the same on small and large screens.
 */
export function verticalDragDelta(dy: number, containerHeight: number): number {
    if (containerHeight <= 0) return 0
    // 1× container height = ±1.0 delta
    return clamp(-dy / containerHeight, -1, 1)
}

/**
 * Map horizontal drag (in px) + container width to a seek delta in seconds.
 * Drag right = forward.
 */
export function horizontalDragSeconds(dx: number, containerWidth: number): number {
    if (containerWidth <= 0) return 0
    const ratio = dx / containerWidth
    return ratio * SEEK_FULL_WIDTH_SECONDS
}

export function clamp(value: number, min: number, max: number): number {
    return Math.min(max, Math.max(min, value))
}

/** Format seconds as `m:ss` or `h:mm:ss`. */
export function formatTime(seconds: number): string {
    if (!Number.isFinite(seconds) || seconds < 0) seconds = 0
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = Math.floor(seconds % 60)
    if (h > 0) {
        return `${h}:${pad(m)}:${pad(s)}`
    }
    return `${m}:${pad(s)}`
}

/** Format a signed seek delta with leading sign. */
export function formatDelta(seconds: number): string {
    const sign = seconds >= 0 ? "+" : "−"
    return `${sign}${formatTime(Math.abs(seconds))}`
}

function pad(n: number): string {
    return n < 10 ? `0${n}` : String(n)
}
