import { memo, useCallback, useEffect, useLayoutEffect, useRef, useState, type FormEvent, type MutableRefObject } from "react"
import { ListMusic, Maximize2, Pause, Play, Repeat, Repeat1, Shuffle, SkipBack, SkipForward, Volume2, X } from "lucide-react"
import type { PlayerQueueItem, PlayerTrack, RepeatMode } from "@/stores/player"
import { AuthImage } from "@/components/auth-image"
import type { TrackResourceStatus } from "./use-enriched-player-track"
import { cn } from "@/lib/utils"
import { PlayerButton } from "./music-player-button"
import { formatTime, parseLyrics, repeatLabel } from "./music-player-utils"

const QUEUE_ROW_HEIGHT = 60
const QUEUE_OVERSCAN = 6

export function FullscreenPlayer({
    track,
    queue,
    index,
    currentTime,
    duration,
    isPlaying,
    shuffle,
    repeatMode,
    lyrics,
    lyricsStatus,
    onRetryLyrics,
    activeLyricIndex,
    showQueue,
    onShowQueueChange,
    onClose,
    onSeek,
    onPlayQueueItem,
    onToggle,
    onPrevious,
    onNext,
    onShuffle,
    onRepeat,
}: {
    track: PlayerTrack
    queue: PlayerQueueItem[]
    index: number
    currentTime: number
    duration: number
    isPlaying: boolean
    shuffle: boolean
    repeatMode: RepeatMode
    lyrics: ReturnType<typeof parseLyrics>
    lyricsStatus: TrackResourceStatus
    onRetryLyrics: () => void
    activeLyricIndex: number
    showQueue: boolean
    onShowQueueChange: (show: boolean) => void
    onClose: () => void
    onSeek: (time: number) => void
    onPlayQueueItem: (index: number) => void
    onToggle: () => void
    onPrevious: () => void
    onNext: () => void
    onShuffle: () => void
    onRepeat: () => void
}) {
    return (
        <div className="fixed inset-0 z-[200] bg-background text-foreground">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-background to-secondary/45" />
            <div className="relative flex h-full flex-col overflow-hidden">
                <div className="group absolute right-0 top-0 z-10 flex h-24 w-24 items-start justify-end p-4 sm:p-6">
                    <button
                        type="button"
                        onClick={onClose}
                        className="flex h-10 w-10 items-center justify-center rounded-full bg-card text-muted-foreground opacity-0 shadow-sm transition-opacity group-hover:opacity-100 focus-visible:opacity-100 hover:text-foreground"
                        aria-label="Close full player"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>
                <div className="group absolute bottom-0 right-0 z-10 flex h-28 w-28 items-end justify-end p-4 sm:p-6">
                    <button
                        type="button"
                        onClick={() => onShowQueueChange(!showQueue)}
                        className={cn(
                            "flex h-10 w-10 items-center justify-center rounded-full bg-card text-muted-foreground opacity-0 shadow-sm transition-opacity group-hover:opacity-100 focus-visible:opacity-100 hover:text-foreground",
                            showQueue && "text-primary",
                        )}
                        aria-label={showQueue ? "Hide up next" : "Show up next"}
                        title={showQueue ? "Hide up next" : "Show up next"}
                    >
                        <ListMusic className="h-5 w-5" />
                    </button>
                </div>

                <div className={cn(
                    "grid min-h-0 flex-1 gap-5 overflow-y-auto px-4 py-5 lg:overflow-hidden lg:px-6",
                    showQueue
                        ? "lg:grid-cols-[minmax(20rem,0.95fr)_minmax(24rem,1fr)_minmax(18rem,0.8fr)]"
                        : "lg:grid-cols-[minmax(20rem,0.9fr)_minmax(24rem,1.1fr)]",
                )}>
                    <section className="flex min-h-0 flex-col justify-center">
                        <Cover track={track} className="mx-auto aspect-square w-full max-w-sm rounded-[2rem] shadow-2xl shadow-black/15" />
                        <div className="mx-auto mt-6 w-full max-w-md text-center">
                            <h2 className="text-3xl font-bold tracking-tight">{track.title}</h2>
                            <p className="mt-2 text-lg text-muted-foreground">{track.artist}</p>
                            <p className="mt-1 text-sm text-muted-foreground">{track.album}{track.year ? ` · ${track.year}` : ""}</p>
                        </div>
                        <div className="mx-auto mt-4 w-full max-w-sm">
                            <ProgressBar currentTime={currentTime} duration={duration} onSeek={onSeek} />
                            <div className="mt-5 flex items-center justify-center gap-3">
                                <PlayerButton onClick={onShuffle} label="Shuffle" active={shuffle}>
                                    <Shuffle className="h-4 w-4" />
                                </PlayerButton>
                                <PlayerButton onClick={onPrevious} label="Previous" large>
                                    <SkipBack className="h-5 w-5" />
                                </PlayerButton>
                                <PlayerButton onClick={onToggle} label={isPlaying ? "Pause" : "Play"} primary large>
                                    {isPlaying ? <Pause className="h-7 w-7" /> : <Play className="ml-1 h-7 w-7" />}
                                </PlayerButton>
                                <PlayerButton onClick={onNext} label="Next" large>
                                    <SkipForward className="h-5 w-5" />
                                </PlayerButton>
                                <PlayerButton onClick={onRepeat} label={repeatLabel(repeatMode)} active={repeatMode !== "off"}>
                                    {repeatMode === "one" ? <Repeat1 className="h-4 w-4" /> : <Repeat className="h-4 w-4" />}
                                </PlayerButton>
                            </div>
                        </div>
                    </section>

                    <section className="min-h-0 overflow-hidden">
                        <LyricsPanel
                            key={`${track.id}:${lyrics.synced.length}:${lyrics.plain.length}`}
                            lyrics={lyrics}
                            status={lyricsStatus}
                            onRetry={onRetryLyrics}
                            activeIndex={activeLyricIndex}
                            onSeek={onSeek}
                        />
                    </section>

                    {showQueue && (
                        <section className="min-h-0 px-5 py-3 lg:overflow-hidden">
                            <div className="mb-2 flex items-center gap-2">
                                <ListMusic className="h-5 w-5 text-primary" />
                                <h3 className="text-xl font-bold">Up Next</h3>
                            </div>
                            <QueuePanel
                                queue={queue}
                                index={index}
                                onPlayQueueItem={onPlayQueueItem}
                            />
                        </section>
                    )}
                </div>
            </div>
        </div>
    )
}

const QueuePanel = memo(function QueuePanel({
    queue,
    index,
    onPlayQueueItem,
}: {
    queue: PlayerQueueItem[]
    index: number
    onPlayQueueItem: (index: number) => void
}) {
    const containerRef = useRef<HTMLDivElement | null>(null)
    const [viewport, setViewport] = useState({ start: 0, count: 20 })
    const updateViewport = useCallback(() => {
        const container = containerRef.current
        if (!container) return
        const visible = Math.ceil(container.clientHeight / QUEUE_ROW_HEIGHT)
        const start = Math.max(
            0,
            Math.floor(container.scrollTop / QUEUE_ROW_HEIGHT) - QUEUE_OVERSCAN,
        )
        setViewport({ start, count: visible + QUEUE_OVERSCAN * 2 })
    }, [])

    useLayoutEffect(() => {
        const container = containerRef.current
        if (!container || index < 0) return
        const top = index * QUEUE_ROW_HEIGHT
        const bottom = top + QUEUE_ROW_HEIGHT
        if (top < container.scrollTop || bottom > container.scrollTop + container.clientHeight) {
            container.scrollTop = Math.max(
                0,
                top - container.clientHeight / 2 + QUEUE_ROW_HEIGHT / 2,
            )
        }
        updateViewport()
    }, [index, updateViewport])

    const visibleItems = queue.slice(viewport.start, viewport.start + viewport.count)
    return (
        <div
            ref={containerRef}
            onScroll={updateViewport}
            className="relative max-h-96 overflow-y-auto pr-2 lg:h-[calc(100vh-9rem)] lg:max-h-none"
        >
            <div className="relative" style={{ height: `${queue.length * QUEUE_ROW_HEIGHT}px` }}>
                {visibleItems.map((item, visibleIndex) => {
                    const queueIndex = viewport.start + visibleIndex
                    return (
                        <button
                            key={item.queueEntryId}
                            type="button"
                            onClick={() => onPlayQueueItem(queueIndex)}
                            className={cn(
                                "absolute left-0 right-0 flex h-14 items-center gap-3 rounded-xl px-2 text-left transition-colors",
                                queueIndex === index ? "bg-primary/10 text-primary" : "hover:bg-secondary/45",
                            )}
                            style={{ top: `${queueIndex * QUEUE_ROW_HEIGHT}px` }}
                        >
                            <Cover track={item} className="h-12 w-12 rounded-xl" />
                            <span className="min-w-0 flex-1">
                                <span className="block truncate text-sm font-semibold">{item.title}</span>
                                <span className="block truncate text-xs text-muted-foreground">{item.artist}</span>
                            </span>
                        </button>
                    )
                })}
            </div>
        </div>
    )
})

export const LyricsPanel = memo(function LyricsPanel({
    lyrics,
    status,
    onRetry,
    activeIndex,
    onSeek,
}: {
    lyrics: ReturnType<typeof parseLyrics>
    status: TrackResourceStatus
    onRetry: () => void
    activeIndex: number
    onSeek: (time: number) => void
}) {
    const containerRef = useRef<HTMLDivElement | null>(null)
    const lineRefs = useRef(new Map<number, HTMLButtonElement>())
    const scrollTimerRef = useRef<number | null>(null)
    const animationFrameRef = useRef<number | null>(null)
    const autoScrollRef = useRef(false)
    const initialCenteredRef = useRef(false)
    const [tracking, setTracking] = useState(true)

    const activeLineIsVisible = useCallback(() => {
        const container = containerRef.current
        const line = lineRefs.current.get(activeIndex)
        if (!container || !line) return false
        const containerRect = container.getBoundingClientRect()
        const lineRect = line.getBoundingClientRect()
        return lineRect.top >= containerRect.top && lineRect.bottom <= containerRect.bottom
    }, [activeIndex])

    useEffect(() => () => {
        if (scrollTimerRef.current != null) window.clearTimeout(scrollTimerRef.current)
        if (animationFrameRef.current != null) window.cancelAnimationFrame(animationFrameRef.current)
    }, [])

    useLayoutEffect(() => {
        if (!tracking || activeIndex < 0) return
        const container = containerRef.current
        const line = lineRefs.current.get(activeIndex)
        if (!container || !line) return
        autoScrollRef.current = true
        scrollLyricToCenter(container, line, !initialCenteredRef.current, animationFrameRef)
        initialCenteredRef.current = true
        const id = window.setTimeout(() => {
            autoScrollRef.current = false
        }, 1250)
        return () => window.clearTimeout(id)
    }, [activeIndex, lyrics.synced.length, tracking])

    useEffect(() => {
        if (tracking || activeIndex < 0) return
        const id = window.setTimeout(() => {
            if (activeLineIsVisible()) setTracking(true)
        }, 1500)
        return () => window.clearTimeout(id)
    }, [activeIndex, activeLineIsVisible, tracking])

    const handleScroll = () => {
        if (autoScrollRef.current) return
        setTracking(false)
        if (scrollTimerRef.current != null) window.clearTimeout(scrollTimerRef.current)
        scrollTimerRef.current = window.setTimeout(() => {
            if (activeLineIsVisible()) setTracking(true)
        }, 1500)
    }

    if (lyrics.synced.length > 0) {
        return (
            <div
                ref={containerRef}
                onScroll={handleScroll}
                className="scrollbar-hide h-full overflow-y-auto overflow-x-hidden px-6 py-[26vh] sm:px-8"
                style={{
                    WebkitMaskImage: "linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%)",
                    maskImage: "linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%)",
                }}
            >
                {lyrics.synced.map((line, index) => (
                    <button
                        key={`${line.time}-${index}`}
                        ref={(node) => {
                            if (node) lineRefs.current.set(index, node)
                            else lineRefs.current.delete(index)
                        }}
                        type="button"
                        onClick={() => {
                            onSeek(line.time)
                            setTracking(true)
                        }}
                        className={cn(
                            "block w-full max-w-full origin-left whitespace-normal break-words py-2 text-left text-3xl font-black leading-tight tracking-tight transition-all duration-300 focus-visible:outline-none md:text-4xl",
                            index === activeIndex
                                ? "scale-[1.08] text-foreground"
                                : Math.abs(index - activeIndex) === 1
                                    ? "text-muted-foreground/65"
                                    : "text-muted-foreground/30 hover:text-muted-foreground/70",
                        )}
                    >
                        {line.text || "♪"}
                    </button>
                ))}
            </div>
        )
    }
    if (lyrics.plain.length > 0) {
        return (
            <div
                className="scrollbar-hide h-full overflow-y-auto overflow-x-hidden px-6 py-[18vh] sm:px-8"
                style={{
                    WebkitMaskImage: "linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%)",
                    maskImage: "linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%)",
                }}
            >
                <div className="max-w-full whitespace-pre-wrap break-words text-3xl font-black leading-tight tracking-tight text-foreground/80 md:text-4xl">
                    {lyrics.plain.join("\n")}
                </div>
            </div>
        )
    }
    return (
        <div className="flex h-full min-h-72 flex-col items-center justify-center text-center">
            <h4 className="text-lg font-bold">
                {status === "loading"
                    ? "Loading lyrics…"
                    : status === "error"
                        ? "Lyrics unavailable"
                        : "No lyrics yet"}
            </h4>
            {status === "error" && (
                <button
                    type="button"
                    onClick={onRetry}
                    className="mt-3 rounded-full bg-secondary px-4 py-2 text-sm font-semibold"
                >
                    Retry
                </button>
            )}
        </div>
    )
})

export function Cover({ track, className }: { track: PlayerTrack, className?: string }) {
    const fallback = (
        <span className="text-2xl font-bold text-muted-foreground">{track.title.slice(0, 1)}</span>
    )
    return (
        <div className={cn("relative flex shrink-0 items-center justify-center overflow-hidden bg-secondary", className)}>
            {track.artworkUrl ? (
                <AuthImage
                    apiSrc={track.artworkUrl}
                    alt=""
                    loading="eager"
                    className="h-full w-full object-cover"
                    fallback={fallback}
                />
            ) : (
                fallback
            )}
        </div>
    )
}

export function CoverButton({ track, onClick }: { track: PlayerTrack, onClick: () => void }) {
    return (
        <button
            type="button"
            onClick={onClick}
            className="group relative overflow-hidden rounded-[0.95rem] text-left shadow-lg shadow-black/10"
            aria-label="Open full player"
            title="Open full player"
        >
            <Cover track={track} className="h-12 w-12 rounded-[0.95rem] sm:h-14 sm:w-14" />
            <span className="absolute inset-0 flex items-center justify-center bg-black/45 opacity-0 transition-opacity group-hover:opacity-100">
                <Maximize2 className="h-5 w-5 text-white" />
            </span>
        </button>
    )
}

export function ProgressBar({
    currentTime,
    duration,
    onSeek,
    compact,
}: {
    currentTime: number
    duration: number
    onSeek: (time: number) => void
    compact?: boolean
}) {
    const safeDuration = Number.isFinite(duration) ? duration : 0
    const value = Math.min(currentTime, safeDuration || currentTime)
    const seekable = safeDuration > 0
    const remaining = seekable ? Math.max(0, safeDuration - value) : 0
    return (
        <div className={cn(
            "grid select-none grid-cols-[minmax(0,1fr)_3rem] items-center",
            compact ? "gap-2" : "gap-3",
        )}>
            <SeekTrack value={value} max={seekable ? safeDuration : 1} disabled={!seekable} onSeek={onSeek} compact={compact} />
            <span className="text-right text-[11px] font-medium tabular-nums text-muted-foreground">
                {seekable ? `-${formatTime(remaining)}` : "--:--"}
            </span>
        </div>
    )
}

export function VolumeControl({ volume, onChange }: { volume: number, onChange: (volume: number) => void }) {
    const [open, setOpen] = useState(false)
    const rootRef = useRef<HTMLDivElement | null>(null)
    const percent = Math.min(100, Math.max(0, volume * 100))
    useEffect(() => {
        if (!open) return
        const handlePointerDown = (event: PointerEvent) => {
            if (rootRef.current?.contains(event.target as Node)) return
            setOpen(false)
        }
        document.addEventListener("pointerdown", handlePointerDown)
        return () => document.removeEventListener("pointerdown", handlePointerDown)
    }, [open])
    return (
        <div ref={rootRef} className="relative flex h-9 w-9 items-center justify-center">
            <button
                type="button"
                onClick={() => setOpen((value) => !value)}
                className={cn(
                    "inline-flex h-9 w-9 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground",
                    open ? "bg-primary/15 text-primary" : "bg-secondary/70",
                )}
                aria-label="Volume"
                title="Volume"
            >
                <Volume2 className="h-4 w-4" />
            </button>
            {open && (
                <div className="absolute bottom-12 left-1/2 flex h-36 w-12 -translate-x-1/2 items-center justify-center rounded-2xl border border-border bg-card shadow-2xl shadow-black/20">
                    <div className="relative h-24 w-5">
                        <div className="absolute bottom-0 left-1/2 top-0 w-1.5 -translate-x-1/2 rounded-full bg-secondary" />
                        <div
                            className="absolute bottom-0 left-1/2 w-1.5 -translate-x-1/2 rounded-full bg-primary"
                            style={{ height: `${percent}%` }}
                        />
                        <div
                            className="absolute left-1/2 h-3.5 w-3.5 -translate-x-1/2 translate-y-1/2 rounded-full border-2 border-card bg-primary shadow-lg shadow-black/20"
                            style={{ bottom: `${percent}%` }}
                        />
                        <input
                            type="range"
                            min={0}
                            max={1}
                            step={0.01}
                            value={volume}
                            onChange={(event) => onChange(Number(event.target.value))}
                            className="absolute left-1/2 top-1/2 h-8 w-28 -translate-x-1/2 -translate-y-1/2 -rotate-90 cursor-pointer opacity-0"
                            aria-label="Volume"
                        />
                    </div>
                </div>
            )}
        </div>
    )
}

function SeekTrack({
    value,
    max,
    disabled,
    onSeek,
    compact,
}: {
    value: number
    max: number
    disabled: boolean
    onSeek: (time: number) => void
    compact?: boolean
}) {
    const [dragging, setDragging] = useState(false)
    const [draft, setDraft] = useState(value)
    const draggingRef = useRef(false)
    const displayedValue = dragging ? draft : value
    const percent = disabled ? 0 : Math.min(100, Math.max(0, displayedValue / max * 100))

    const handleInput = (event: FormEvent<HTMLInputElement>) => {
        draggingRef.current = true
        setDragging(true)
        setDraft(Number(event.currentTarget.value))
    }
    const commit = (value: number) => {
        if (!draggingRef.current) return
        draggingRef.current = false
        setDragging(false)
        setDraft(value)
        onSeek(value)
    }
    return (
        <div className={cn("group relative", compact ? "h-5" : "h-6")}>
            <div className={cn(
                "absolute left-0 right-0 top-1/2 -translate-y-1/2 rounded-full bg-secondary",
                compact ? "h-1.5" : "h-2",
            )} />
            <div
                className={cn(
                    "absolute left-0 top-1/2 -translate-y-1/2 rounded-full bg-primary",
                    compact ? "h-1.5" : "h-2 shadow-[0_0_18px_rgba(10,132,255,0.35)]",
                )}
                style={{ width: `${percent}%` }}
            />
            <div
                className={cn(
                    "absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-card bg-primary shadow-lg shadow-black/20 transition-transform",
                    compact ? "h-3.5 w-3.5" : "h-4 w-4",
                    disabled ? "opacity-0" : "group-hover:scale-110",
                )}
                style={{ left: `${percent}%` }}
            />
            <input
                type="range"
                min={0}
                max={max}
                step={0.1}
                value={disabled ? 0 : displayedValue}
                disabled={disabled}
                onInput={handleInput}
                onPointerDown={() => {
                    draggingRef.current = true
                    setDraft(value)
                    setDragging(true)
                }}
                onPointerUp={(event) => commit(Number(event.currentTarget.value))}
                onPointerCancel={(event) => commit(Number(event.currentTarget.value))}
                onKeyUp={(event) => {
                    if (["ArrowLeft", "ArrowRight", "Home", "End", "PageUp", "PageDown"].includes(event.key)) {
                        commit(Number(event.currentTarget.value))
                    }
                }}
                onBlur={(event) => {
                    if (draggingRef.current) commit(Number(event.currentTarget.value))
                }}
                className="absolute inset-x-0 top-1/2 h-8 -translate-y-1/2 cursor-pointer opacity-0 disabled:cursor-default"
                aria-label="Seek"
            />
        </div>
    )
}

function scrollLyricToCenter(
    container: HTMLDivElement,
    line: HTMLElement,
    immediate: boolean,
    frameRef: MutableRefObject<number | null>,
) {
    const target = Math.max(0, line.offsetTop - container.clientHeight / 2 + line.clientHeight / 2)
    if (frameRef.current != null) window.cancelAnimationFrame(frameRef.current)
    if (immediate) {
        container.scrollTop = target
        return
    }
    const start = container.scrollTop
    const distance = target - start
    const duration = 950
    const startedAt = performance.now()
    const ease = (value: number) => 1 - Math.pow(1 - value, 3)
    const tick = (now: number) => {
        const progress = Math.min(1, (now - startedAt) / duration)
        container.scrollTop = start + distance * ease(progress)
        if (progress < 1) {
            frameRef.current = window.requestAnimationFrame(tick)
        } else {
            frameRef.current = null
        }
    }
    frameRef.current = window.requestAnimationFrame(tick)
}
