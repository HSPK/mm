import { FastForward, Lightbulb, Volume2, VolumeX } from "lucide-react"
import {
    useCallback,
    useEffect,
    useRef,
    useState,
    type TouchEvent as ReactTouchEvent,
} from "react"
import {
    useMediaRemote,
    useMediaState,
} from "@vidstack/react"
import {
    DOUBLE_TAP_MS,
    DOUBLE_TAP_SEEK_SECONDS,
    LONG_PRESS_MS,
    TAP_SLOP_PX,
    clamp,
    detectAxis,
    formatDelta,
    formatTime,
    horizontalDragSeconds,
    verticalDragDelta,
    type GestureAxis,
} from "@/lib/gesture-math"

interface VideoGesturesProps {
    /** When true, gestures are disabled (e.g. lock mode is on). */
    disabled?: boolean
    /** Default playback speed to restore after a long-press 2× ends. */
    defaultRate?: number
    /** Speed applied while a long-press is active. */
    boostRate?: number
    /** Receives the current brightness multiplier (1 = normal). */
    onBrightnessChange?: (brightness: number) => void
}

type ActiveGesture =
    | { kind: "speed" }
    | { kind: "volume"; value: number }
    | { kind: "brightness"; value: number }
    | { kind: "seek"; from: number; to: number; delta: number }
    | null

/**
 * Bilibili-style touch gestures layered over a vidstack player:
 *  - Long-press anywhere → boostRate (2×); release restores defaultRate
 *  - Right-half vertical drag → volume
 *  - Left-half vertical drag → brightness (CSS filter on the player wrapper)
 *  - Horizontal drag → seek preview; commit on release
 *  - Double-tap left/right halves → seek ∓10s
 *  - Single tap → toggle play/pause
 *
 * Must be mounted INSIDE a vidstack MediaPlayer so the remote hooks resolve.
 */
export function VideoGestures({
    disabled,
    defaultRate = 1,
    boostRate = 2,
    onBrightnessChange,
}: VideoGesturesProps) {
    const remote = useMediaRemote()
    const duration = useMediaState("duration")
    const currentTime = useMediaState("currentTime")
    const volume = useMediaState("volume")

    const layerRef = useRef<HTMLDivElement>(null)
    const touchRef = useRef<{ x: number; y: number; time: number; rect: DOMRect } | null>(null)
    const axisRef = useRef<GestureAxis | null>(null)
    const startVolumeRef = useRef(1)
    const startBrightnessRef = useRef(1)
    const startTimeRef = useRef(0)
    const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const longPressActiveRef = useRef(false)
    const lastTapRef = useRef<{ x: number; y: number; time: number } | null>(null)
    const brightnessRef = useRef(1)

    const [active, setActive] = useState<ActiveGesture>(null)

    const clearLongPress = useCallback(() => {
        if (longPressTimerRef.current) {
            clearTimeout(longPressTimerRef.current)
            longPressTimerRef.current = null
        }
        if (longPressActiveRef.current) {
            longPressActiveRef.current = false
            remote.changePlaybackRate(defaultRate)
        }
    }, [defaultRate, remote])

    const applyBrightness = useCallback((value: number) => {
        const clamped = clamp(value, 0.3, 1.5)
        brightnessRef.current = clamped
        onBrightnessChange?.(clamped)
    }, [onBrightnessChange])

    const handleTouchStart = (e: ReactTouchEvent<HTMLDivElement>) => {
        if (disabled || e.touches.length !== 1) return
        const layer = layerRef.current
        if (!layer) return
        const t = e.touches[0]
        const rect = layer.getBoundingClientRect()
        touchRef.current = { x: t.clientX, y: t.clientY, time: Date.now(), rect }
        axisRef.current = null
        startVolumeRef.current = volume ?? 1
        startBrightnessRef.current = brightnessRef.current
        startTimeRef.current = currentTime ?? 0

        longPressActiveRef.current = false
        longPressTimerRef.current = setTimeout(() => {
            if (!touchRef.current || axisRef.current) return
            longPressActiveRef.current = true
            remote.changePlaybackRate(boostRate)
            setActive({ kind: "speed" })
        }, LONG_PRESS_MS)
    }

    const handleTouchMove = (e: ReactTouchEvent<HTMLDivElement>) => {
        const start = touchRef.current
        if (!start || disabled) return
        const t = e.touches[0]
        const dx = t.clientX - start.x
        const dy = t.clientY - start.y

        // If we've moved past the tap-slop and not yet in long-press mode,
        // cancel the long-press timer so we can pick up the drag instead.
        if (!longPressActiveRef.current && (Math.abs(dx) > TAP_SLOP_PX || Math.abs(dy) > TAP_SLOP_PX)) {
            if (longPressTimerRef.current) {
                clearTimeout(longPressTimerRef.current)
                longPressTimerRef.current = null
            }
        }
        if (longPressActiveRef.current) return

        if (!axisRef.current) {
            const axis = detectAxis(dx, dy)
            if (!axis) return
            axisRef.current = axis
        }

        if (axisRef.current === "horizontal") {
            const dur = duration && Number.isFinite(duration) ? duration : 0
            if (dur <= 0) return
            const dSeconds = horizontalDragSeconds(dx, start.rect.width)
            const to = clamp(startTimeRef.current + dSeconds, 0, dur)
            setActive({ kind: "seek", from: startTimeRef.current, to, delta: to - startTimeRef.current })
            return
        }

        // vertical
        const delta = verticalDragDelta(dy, start.rect.height)
        const startedLeft = start.x - start.rect.left < start.rect.width / 2
        if (startedLeft) {
            const next = clamp(startBrightnessRef.current + delta, 0.3, 1.5)
            applyBrightness(next)
            setActive({ kind: "brightness", value: next })
        } else {
            const next = clamp(startVolumeRef.current + delta, 0, 1)
            remote.changeVolume(next)
            setActive({ kind: "volume", value: next })
        }
    }

    const handleTouchEnd = (e: ReactTouchEvent<HTMLDivElement>) => {
        const start = touchRef.current
        touchRef.current = null

        // Long-press finished → restore rate
        if (longPressActiveRef.current) {
            clearLongPress()
            setActive(null)
            return
        }
        if (longPressTimerRef.current) {
            clearTimeout(longPressTimerRef.current)
            longPressTimerRef.current = null
        }

        if (!start) return

        const touch = e.changedTouches[0]
        const dx = touch.clientX - start.x
        const dy = touch.clientY - start.y
        const moved = Math.abs(dx) > TAP_SLOP_PX || Math.abs(dy) > TAP_SLOP_PX

        // Commit a seek if we were in seek mode
        if (active?.kind === "seek") {
            remote.seek(active.to)
        }

        if (active) {
            setActive(null)
            axisRef.current = null
            return
        }

        if (!moved && !disabled) {
            // Single tap → toggle play/pause; check for double-tap first
            const now = Date.now()
            const lastTap = lastTapRef.current
            if (lastTap && now - lastTap.time < DOUBLE_TAP_MS) {
                // Double tap → seek ±10s based on which half was tapped
                const startedRight = start.x - start.rect.left > start.rect.width / 2
                const dur = duration && Number.isFinite(duration) ? duration : 0
                const target = clamp(
                    (currentTime ?? 0) + (startedRight ? DOUBLE_TAP_SEEK_SECONDS : -DOUBLE_TAP_SEEK_SECONDS),
                    0,
                    dur || Number.POSITIVE_INFINITY,
                )
                remote.seek(target)
                setActive({ kind: "seek", from: currentTime ?? 0, to: target, delta: target - (currentTime ?? 0) })
                window.setTimeout(() => setActive(null), 450)
                lastTapRef.current = null
                return
            }
            lastTapRef.current = { x: touch.clientX, y: touch.clientY, time: now }
            remote.togglePaused()
        }

        axisRef.current = null
    }

    const handleTouchCancel = () => {
        touchRef.current = null
        axisRef.current = null
        if (longPressTimerRef.current) {
            clearTimeout(longPressTimerRef.current)
            longPressTimerRef.current = null
        }
        if (longPressActiveRef.current) clearLongPress()
        setActive(null)
    }

    useEffect(() => {
        return () => {
            if (longPressTimerRef.current) clearTimeout(longPressTimerRef.current)
        }
    }, [])

    return (
        <div
            ref={layerRef}
            className="absolute inset-0 z-20 select-none touch-none"
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            onTouchCancel={handleTouchCancel}
            aria-hidden
        >
            {active && <GestureOverlay state={active} duration={duration ?? 0} />}
        </div>
    )
}

function GestureOverlay({ state, duration }: { state: NonNullable<ActiveGesture>; duration: number }) {
    const wrapClass = "pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-black/70 backdrop-blur-md text-white shadow-2xl"

    if (state.kind === "speed") {
        return (
            <div className={`${wrapClass} flex items-center gap-2 px-5 py-3`}>
                <FastForward className="h-5 w-5 fill-current" />
                <span className="text-lg font-bold tracking-tight">2× speed</span>
            </div>
        )
    }

    if (state.kind === "seek") {
        return (
            <div className={`${wrapClass} flex flex-col items-center gap-1 px-6 py-3 min-w-[10rem]`}>
                <span className="text-xs font-medium text-white/70 tabular-nums">
                    {formatDelta(state.delta)}
                </span>
                <span className="text-2xl font-semibold tabular-nums">
                    {formatTime(state.to)}
                </span>
                <span className="text-[10px] uppercase tracking-widest text-white/40 tabular-nums">
                    / {formatTime(duration)}
                </span>
            </div>
        )
    }

    if (state.kind === "volume") {
        const pct = Math.round(state.value * 100)
        const Icon = state.value <= 0 ? VolumeX : Volume2
        return <SideBar icon={Icon} value={pct} side="right" />
    }

    // brightness
    const pct = Math.round(((state.value - 0.3) / (1.5 - 0.3)) * 100)
    return <SideBar icon={Lightbulb} value={pct} side="left" />
}

function SideBar({
    icon: Icon,
    value,
    side,
}: {
    icon: typeof Volume2
    value: number
    side: "left" | "right"
}) {
    const positionClass = side === "left" ? "left-6" : "right-6"
    return (
        <div className={`pointer-events-none absolute top-1/2 ${positionClass} -translate-y-1/2 flex flex-col items-center gap-3 rounded-full bg-black/65 backdrop-blur-md p-3 text-white shadow-2xl`}>
            <Icon className="h-5 w-5" />
            <div className="h-32 w-1.5 rounded-full bg-white/15 overflow-hidden">
                <div
                    className="absolute bottom-0 left-0 right-0 origin-bottom rounded-full bg-white transition-transform duration-100"
                    style={{
                        transform: `scaleY(${clamp(value, 0, 100) / 100})`,
                        position: "relative",
                        width: "100%",
                        height: "100%",
                    }}
                />
            </div>
            <span className="text-[11px] font-semibold tabular-nums">{Math.round(value)}%</span>
        </div>
    )
}
