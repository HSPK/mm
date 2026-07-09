import { useCallback, useEffect, useRef, useState, type PointerEvent } from "react"
import type Hls from "hls.js"
import { Captions, Check, Expand, Gauge, Languages, Pause, Play, SkipForward, Volume2, VolumeX } from "lucide-react"
import { playerRepo, type VideoPlaybackSource, type VideoTrack } from "@/api/player"
import { browserTokenStorage } from "@/lib/token-storage"
import { cn } from "@/lib/utils"

const CONTROLS_IDLE_MS = 2200
const SPEED_OPTIONS = [0.5, 0.75, 1, 1.25, 1.5, 2]
const CONTROL_BUTTON_CLASS = "flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.08] text-white/90 shadow-lg shadow-black/20 transition hover:bg-white/[0.16] hover:text-white disabled:pointer-events-none disabled:opacity-35"
const CONTROL_CHIP_CLASS = "inline-flex h-10 items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.08] px-3 text-sm font-semibold text-white/90 shadow-lg shadow-black/20 transition hover:bg-white/[0.16] hover:text-white disabled:pointer-events-none disabled:opacity-35"

interface TrackOption {
    index: number
    label: string
    url?: string | null
}

export function VideoPlayer({
    playbackId,
    poster,
    initialTime = 0,
    onNext,
    onProgress,
}: {
    playbackId: string
    poster?: string
    initialTime?: number
    onNext?: () => void
    onProgress?: (time: number, duration: number) => void
}) {
    const videoRef = useRef<HTMLVideoElement | null>(null)
    const rootRef = useRef<HTMLDivElement | null>(null)
    const hlsRef = useRef<Hls | null>(null)
    const lastProgressRef = useRef(0)
    const restoredRef = useRef(false)
    const draggingRef = useRef(false)
    const hideControlsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const pendingRestoreTimeRef = useRef<number | null>(null)
    const resumeAfterSourceLoadRef = useRef(false)
    const [playing, setPlaying] = useState(false)
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const [volume, setVolume] = useState(0.9)
    const [playbackRate, setPlaybackRate] = useState(1)
    const [controlsVisible, setControlsVisible] = useState(false)
    const [fullscreen, setFullscreen] = useState(false)
    const [volumeOpen, setVolumeOpen] = useState(false)
    const [trackMenu, setTrackMenu] = useState<"audio" | "subtitles" | null>(null)
    const [error, setError] = useState("")
    const [bufferedPercent, setBufferedPercent] = useState(0)
    const [preview, setPreview] = useState<{ x: number; time: number } | null>(null)
    const [muted, setMuted] = useState(false)
    const [audioTracks, setAudioTracks] = useState<TrackOption[]>([])
    const [subtitleTracks, setSubtitleTracks] = useState<TrackOption[]>([])
    const [selectedAudioTrack, setSelectedAudioTrack] = useState(0)
    const [selectedSubtitleTrack, setSelectedSubtitleTrack] = useState(-1)
    const [requestedAudioStream, setRequestedAudioStream] = useState<number | null>(null)
    const progressPercent = duration > 0 ? Math.min(100, Math.max(0, currentTime / duration * 100)) : 0

    const applySourceTracks = useCallback((source: VideoPlaybackSource) => {
        const nextAudioTracks = source.audio_tracks.map(trackOption)
        const nextSubtitleTracks = source.subtitle_tracks.filter((track) => track.url).map(trackOption)
        const selectedAudio = source.selected_audio_stream ?? nextAudioTracks[0]?.index ?? 0
        setAudioTracks(nextAudioTracks)
        setSubtitleTracks(nextSubtitleTracks)
        setSelectedAudioTrack(selectedAudio)
        setSelectedSubtitleTrack((current) => (
            nextSubtitleTracks.some((track) => track.index === current) ? current : -1
        ))
    }, [])

    const clearControlsTimer = () => {
        if (hideControlsTimerRef.current) {
            window.clearTimeout(hideControlsTimerRef.current)
            hideControlsTimerRef.current = null
        }
    }

    const scheduleControlsHide = (enabled = fullscreen) => {
        clearControlsTimer()
        if (!enabled) return
        hideControlsTimerRef.current = window.setTimeout(() => {
            setControlsVisible(false)
            setVolumeOpen(false)
            setTrackMenu(null)
            hideControlsTimerRef.current = null
        }, CONTROLS_IDLE_MS)
    }

    const revealControls = (autoHide = fullscreen) => {
        setControlsVisible(true)
        scheduleControlsHide(autoHide)
    }

    useEffect(() => {
        setPlaying(false)
        setCurrentTime(0)
        setDuration(0)
        setBufferedPercent(0)
        setError("")
        setAudioTracks([])
        setSubtitleTracks([])
        setSelectedAudioTrack(0)
        setSelectedSubtitleTrack(-1)
        setRequestedAudioStream(null)
        setVolumeOpen(false)
        setTrackMenu(null)
        pendingRestoreTimeRef.current = null
        resumeAfterSourceLoadRef.current = false
        lastProgressRef.current = 0
        restoredRef.current = false
    }, [playbackId])

    useEffect(() => {
        const frame = window.requestAnimationFrame(() => rootRef.current?.focus({ preventScroll: true }))
        return () => window.cancelAnimationFrame(frame)
    }, [playbackId])

    useEffect(() => {
        const handleFullscreenChange = () => {
            const active = document.fullscreenElement === rootRef.current
            setFullscreen(active)
            setControlsVisible(active)
            if (active) scheduleControlsHide(true)
            else {
                clearControlsTimer()
                setVolumeOpen(false)
                setTrackMenu(null)
            }
        }
        document.addEventListener("fullscreenchange", handleFullscreenChange)
        return () => {
            document.removeEventListener("fullscreenchange", handleFullscreenChange)
            clearControlsTimer()
        }
    }, [])

    useEffect(() => {
        let cancelled = false
        const video = videoRef.current
        if (!video) return
        hlsRef.current?.destroy()
        hlsRef.current = null
        video.removeAttribute("src")
        video.load()
        setError("")
        void loadVideoSource(playbackId, requestedAudioStream)
            .then(async (source) => {
                if (cancelled) return
                applySourceTracks(source)
                if (source.mode === "hls") {
                    if (video.canPlayType("application/vnd.apple.mpegurl")) {
                        video.src = source.url
                        video.load()
                        return
                    }
                    const { default: Hls } = await import("hls.js")
                    if (cancelled) return
                    if (!Hls.isSupported()) {
                        setError("HLS playback is not supported in this browser")
                        return
                    }
                    const hls = new Hls({
                        xhrSetup: (xhr) => {
                            const token = browserTokenStorage.get()
                            if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`)
                        },
                    })
                    hlsRef.current = hls
                    hls.on(Hls.Events.ERROR, (_event, data) => {
                        if (data.fatal) setError("Video playback failed")
                    })
                    hls.loadSource(source.url)
                    hls.attachMedia(video)
                    return
                }
                video.src = source.url
                video.load()
            })
            .catch((err: unknown) => {
                setError(err instanceof Error ? err.message : "Could not prepare video playback")
            })
        return () => {
            cancelled = true
            hlsRef.current?.destroy()
            hlsRef.current = null
        }
    }, [applySourceTracks, playbackId, requestedAudioStream])

    useEffect(() => {
        const video = videoRef.current
        if (!video) return
        video.volume = volume
    }, [volume])

    useEffect(() => {
        const video = videoRef.current
        if (!video) return
        video.muted = muted
    }, [muted])

    useEffect(() => {
        const video = videoRef.current
        if (!video) return
        video.playbackRate = playbackRate
    }, [playbackRate])

    const toggle = () => {
        const video = videoRef.current
        if (!video) return
        if (video.paused) {
            setError("")
            void video.play().catch(() => {
                setError("Could not start playback")
            })
        } else video.pause()
    }

    const seek = (time: number) => {
        const video = videoRef.current
        if (!video) return
        const next = Math.min(Math.max(time, 0), duration || Number.POSITIVE_INFINITY)
        video.currentTime = next
        setCurrentTime(next)
        onProgress?.(next, duration)
    }

    const seekBy = (delta: number) => {
        const video = videoRef.current
        if (!video) return
        seek(video.currentTime + delta)
    }

    const toggleFullscreen = () => {
        const root = rootRef.current
        if (!root) return
        if (document.fullscreenElement) void document.exitFullscreen()
        else void root.requestFullscreen()
    }

    const cyclePlaybackRate = () => {
        setPlaybackRate((rate) => {
            const index = SPEED_OPTIONS.indexOf(rate)
            return SPEED_OPTIONS[(index + 1) % SPEED_OPTIONS.length] ?? 1
        })
    }

    const selectAudioTrack = (index: number) => {
        const video = videoRef.current
        pendingRestoreTimeRef.current = video?.currentTime ?? currentTime
        resumeAfterSourceLoadRef.current = Boolean(video && !video.paused)
        setSelectedAudioTrack(index)
        setRequestedAudioStream(index)
        setTrackMenu(null)
        revealControls(fullscreen)
    }

    const selectSubtitleTrack = (index: number) => {
        const textTracks = videoRef.current?.textTracks
        if (textTracks) {
            for (let i = 0; i < textTracks.length; i += 1) {
                const id = Number(textTracks[i].id)
                textTracks[i].mode = id === index ? "showing" : "disabled"
            }
        }
        setSelectedSubtitleTrack(index)
        setTrackMenu(null)
        revealControls(fullscreen)
    }

    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.metaKey || event.ctrlKey || event.altKey) return
            if (event.target instanceof HTMLElement) {
                if (event.target.closest("input, textarea, select, [contenteditable='true']")) return
                if (event.target.closest("button") && !rootRef.current?.contains(event.target)) return
            }
            let handled = true
            if (event.key === "ArrowLeft") {
                seekBy(-5)
            } else if (event.key === "ArrowRight") {
                seekBy(5)
            } else if (event.key === " " || event.key.toLowerCase() === "k") {
                toggle()
            } else if (event.key === "ArrowUp") {
                setVolume((value) => Math.min(value + 0.05, 1))
            } else if (event.key === "ArrowDown") {
                setVolume((value) => Math.max(value - 0.05, 0))
            } else if (event.key.toLowerCase() === "f") {
                toggleFullscreen()
            } else if (event.key.toLowerCase() === "m") {
                setMuted((value) => !value)
            } else {
                handled = false
            }
            if (handled) {
                event.preventDefault()
                event.stopPropagation()
                revealControls(fullscreen)
            }
        }
        document.addEventListener("keydown", handleKeyDown, { capture: true })
        return () => document.removeEventListener("keydown", handleKeyDown, { capture: true })
    })

    return (
        <div
            ref={rootRef}
            tabIndex={0}
            className="group relative aspect-video h-full max-h-[62vh] overflow-hidden bg-black shadow-2xl shadow-black/20 focus:outline-none [&:fullscreen]:h-screen [&:fullscreen]:max-h-none [&:fullscreen]:w-screen"
            onMouseEnter={() => revealControls(fullscreen)}
            onMouseMove={() => revealControls(fullscreen)}
            onMouseLeave={() => {
                if (!fullscreen) {
                    setControlsVisible(false)
                    setVolumeOpen(false)
                }
            }}
        >
            <video
                ref={videoRef}
                poster={poster}
                preload="metadata"
                className="h-full w-full bg-black object-contain"
                onClick={toggle}
                onPlay={() => setPlaying(true)}
                onPause={(event) => {
                    setPlaying(false)
                    onProgress?.(event.currentTarget.currentTime, validDuration(event.currentTarget.duration))
                }}
                onTimeUpdate={(event) => {
                    const time = event.currentTarget.currentTime
                    const nextDuration = validDuration(event.currentTarget.duration)
                    setCurrentTime(time)
                    setBufferedPercent(bufferedProgress(event.currentTarget))
                    if (Math.abs(time - lastProgressRef.current) >= 5) {
                        lastProgressRef.current = time
                        onProgress?.(time, nextDuration)
                    }
                }}
                onLoadedMetadata={(event) => {
                    const nextDuration = validDuration(event.currentTarget.duration)
                    setDuration(nextDuration)
                    setBufferedPercent(bufferedProgress(event.currentTarget))
                    if (pendingRestoreTimeRef.current != null) {
                        const restoreTime = Math.min(pendingRestoreTimeRef.current, Math.max(nextDuration - 1, 0))
                        event.currentTarget.currentTime = restoreTime
                        setCurrentTime(restoreTime)
                        pendingRestoreTimeRef.current = null
                        if (resumeAfterSourceLoadRef.current) {
                            resumeAfterSourceLoadRef.current = false
                            void event.currentTarget.play().catch(() => {
                                setError("Could not resume playback")
                            })
                        }
                    } else if (!restoredRef.current && initialTime > 5 && initialTime < nextDuration - 5) {
                        event.currentTarget.currentTime = initialTime
                        setCurrentTime(initialTime)
                    }
                    restoredRef.current = true
                }}
                onDurationChange={(event) => setDuration(validDuration(event.currentTarget.duration))}
                onProgress={(event) => setBufferedPercent(bufferedProgress(event.currentTarget))}
                onEnded={(event) => onProgress?.(event.currentTarget.duration, validDuration(event.currentTarget.duration))}
                onError={() => setError("This video could not be played in the browser")}
            >
                {subtitleTracks.map((track) => (
                    <track
                        key={`${track.index}:${track.url}`}
                        id={String(track.index)}
                        kind="subtitles"
                        label={track.label}
                        src={track.url ?? ""}
                    />
                ))}
            </video>

            {error && (
                <div className="absolute inset-x-4 top-4 rounded-lg bg-destructive/90 px-3 py-2 text-sm font-semibold text-destructive-foreground shadow-lg">
                    {error}
                </div>
            )}

            <div className={cn(
                "absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/38 to-transparent px-4 pb-2 pt-12 text-white transition-opacity duration-200",
                controlsVisible ? "opacity-100" : "pointer-events-none opacity-0",
            )}>
                <div className="flex items-center gap-2">
                    <button type="button" onClick={toggle} className={CONTROL_BUTTON_CLASS} aria-label={playing ? "Pause" : "Play"}>
                        {playing ? <Pause className="h-4 w-4" /> : <Play className="ml-0.5 h-4 w-4" />}
                    </button>
                    {onNext && (
                        <button type="button" onClick={onNext} className={CONTROL_BUTTON_CLASS} aria-label="Next episode">
                            <SkipForward className="h-4 w-4" />
                        </button>
                    )}
                    <span className="ml-1 min-w-[6.5rem] text-sm font-medium tabular-nums text-white/82">
                        {formatTime(currentTime)} / {formatTime(duration)}
                    </span>
                    <button
                        type="button"
                        onClick={cyclePlaybackRate}
                        className={CONTROL_CHIP_CLASS}
                        aria-label={`Playback speed ${playbackRate}x`}
                    >
                        <Gauge className="h-4 w-4" />
                        {playbackRate}x
                    </button>
                    <div className="relative">
                        <button
                            type="button"
                            onClick={() => {
                                setTrackMenu((value) => value === "audio" ? null : "audio")
                                setVolumeOpen(false)
                            }}
                            disabled={audioTracks.length <= 1}
                            className={cn(CONTROL_BUTTON_CLASS, trackMenu === "audio" && "bg-white/[0.18] text-white")}
                            aria-label="Audio track"
                            aria-expanded={trackMenu === "audio"}
                        >
                            <Languages className="h-4 w-4" />
                        </button>
                        <TrackMenu
                            open={trackMenu === "audio"}
                            title="Audio"
                            options={audioTracks}
                            selected={selectedAudioTrack}
                            onSelect={selectAudioTrack}
                        />
                    </div>
                    <div className="relative">
                        <button
                            type="button"
                            onClick={() => {
                                setTrackMenu((value) => value === "subtitles" ? null : "subtitles")
                                setVolumeOpen(false)
                            }}
                            disabled={subtitleTracks.length === 0}
                            className={cn(CONTROL_BUTTON_CLASS, selectedSubtitleTrack >= 0 && "bg-white/[0.18] text-white")}
                            aria-label="Subtitles"
                            aria-expanded={trackMenu === "subtitles"}
                        >
                            <Captions className="h-4 w-4" />
                        </button>
                        <TrackMenu
                            open={trackMenu === "subtitles"}
                            title="Subtitles"
                            options={subtitleTracks}
                            selected={selectedSubtitleTrack}
                            offLabel="Off"
                            onSelect={selectSubtitleTrack}
                        />
                    </div>
                    <div className="relative ml-auto flex items-center gap-2">
                        <button
                            type="button"
                            onClick={() => {
                                setVolumeOpen((value) => !value)
                                setTrackMenu(null)
                            }}
                            className={cn(
                                CONTROL_BUTTON_CLASS,
                                (volumeOpen || muted) && "bg-white/[0.18] text-white",
                            )}
                            aria-label="Volume"
                            aria-expanded={volumeOpen}
                        >
                            {muted || volume <= 0 ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                        </button>
                        {volumeOpen && (
                            <div className="absolute bottom-12 left-1/2 z-20 flex h-32 w-11 -translate-x-1/2 items-center justify-center rounded-2xl border border-white/10 bg-black/82 shadow-xl shadow-black/35 backdrop-blur-xl">
                                <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.01}
                                    value={volume}
                                    onChange={(event) => setVolume(Number(event.currentTarget.value))}
                                    className="h-24 w-5 -rotate-90 accent-primary"
                                    aria-label="Volume"
                                />
                            </div>
                        )}
                        <button type="button" onClick={toggleFullscreen} className={CONTROL_BUTTON_CLASS} aria-label="Fullscreen">
                            <Expand className="h-4 w-4" />
                        </button>
                    </div>
                </div>
                <VideoProgress
                    duration={duration}
                    progressPercent={progressPercent}
                    bufferedPercent={bufferedPercent}
                    preview={preview}
                    previewSrc={preview ? playerRepo.videoPreviewUrl(playbackId, preview.time) : poster}
                    draggingRef={draggingRef}
                    onPreview={setPreview}
                    onSeek={seek}
                    onPreviewTime={setCurrentTime}
                />
            </div>
        </div>
    )
}

async function loadVideoSource(playbackId: string, audioStream: number | null) {
    let lastError: unknown
    for (let attempt = 0; attempt < 4; attempt += 1) {
        try {
            return await playerRepo.videoSource(playbackId, audioStream)
        } catch (err) {
            lastError = err
            await new Promise((resolve) => window.setTimeout(resolve, 900 + attempt * 600))
        }
    }
    throw lastError instanceof Error ? lastError : new Error("Could not prepare video playback")
}

function validDuration(value: number) {
    return Number.isFinite(value) && value > 0 ? value : 0
}

function bufferedProgress(video: HTMLVideoElement) {
    const duration = validDuration(video.duration)
    if (!duration || video.buffered.length === 0) return 0
    const end = video.buffered.end(video.buffered.length - 1)
    return Math.min(100, Math.max(0, end / duration * 100))
}

function TrackMenu({
    open,
    title,
    options,
    selected,
    offLabel,
    onSelect,
}: {
    open: boolean
    title: string
    options: TrackOption[]
    selected: number
    offLabel?: string
    onSelect: (index: number) => void
}) {
    if (!open) return null
    return (
        <div className="absolute bottom-12 left-1/2 z-30 min-w-44 -translate-x-1/2 overflow-hidden rounded-2xl border border-white/10 bg-black/86 p-1.5 text-white shadow-2xl shadow-black/40 backdrop-blur-xl">
            <div className="px-2.5 pb-1.5 pt-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/45">
                {title}
            </div>
            {offLabel && (
                <TrackMenuItem
                    label={offLabel}
                    active={selected < 0}
                    onClick={() => onSelect(-1)}
                />
            )}
            {options.map((option) => (
                <TrackMenuItem
                    key={option.index}
                    label={option.label}
                    active={selected === option.index}
                    onClick={() => onSelect(option.index)}
                />
            ))}
        </div>
    )
}

function TrackMenuItem({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={cn(
                "flex h-9 w-full items-center gap-2 rounded-xl px-2.5 text-left text-sm font-medium transition",
                active ? "bg-white/16 text-white" : "text-white/72 hover:bg-white/10 hover:text-white",
            )}
        >
            <Check className={cn("h-4 w-4", active ? "opacity-100" : "opacity-0")} />
            <span className="truncate">{label}</span>
        </button>
    )
}

function trackLabel(track: { label?: string; name?: string; language?: string; lang?: string }, index: number, fallback: string) {
    const label = track.label || track.name || track.language || track.lang
    return label?.trim() || `${fallback} ${index + 1}`
}

function trackOption(track: VideoTrack): TrackOption {
    return {
        index: track.index,
        label: track.label || trackLabel(track, track.index, "Track"),
        url: track.url,
    }
}

function VideoProgress({
    duration,
    progressPercent,
    bufferedPercent,
    preview,
    previewSrc,
    draggingRef,
    onPreview,
    onSeek,
    onPreviewTime,
}: {
    duration: number
    progressPercent: number
    bufferedPercent: number
    preview: { x: number; time: number } | null
    previewSrc?: string
    draggingRef: React.MutableRefObject<boolean>
    onPreview: (preview: { x: number; time: number } | null) => void
    onSeek: (time: number) => void
    onPreviewTime: (time: number) => void
}) {
    const handlePointer = (event: PointerEvent<HTMLDivElement>, commit: boolean) => {
        const rect = event.currentTarget.getBoundingClientRect()
        const x = Math.min(rect.width, Math.max(0, event.clientX - rect.left))
        const ratio = rect.width > 0 ? x / rect.width : 0
        const time = ratio * duration
        onPreview({ x, time })
        if (draggingRef.current) onPreviewTime(time)
        if (commit) onSeek(time)
    }
    const activePreview = preview && duration > 0 ? preview : null
    return (
        <div
            className="relative mb-1 h-6 cursor-grab active:cursor-grabbing"
            onPointerMove={(event) => handlePointer(event, draggingRef.current)}
            onPointerLeave={() => onPreview(null)}
            onPointerDown={(event) => {
                draggingRef.current = true
                event.currentTarget.setPointerCapture(event.pointerId)
                handlePointer(event, true)
            }}
            onPointerUp={(event) => {
                draggingRef.current = false
                event.currentTarget.releasePointerCapture(event.pointerId)
                handlePointer(event, true)
            }}
        >
            {activePreview && (
                <div
                    className="pointer-events-none absolute bottom-6 z-20 w-32 -translate-x-1/2 overflow-hidden rounded-md bg-black shadow-xl"
                    style={{ left: activePreview.x }}
                >
                    <div className="aspect-video bg-secondary">
                        {previewSrc && <img src={previewSrc} alt="" className="h-full w-full object-cover" />}
                    </div>
                    <div className="px-2 py-1 text-center text-xs font-semibold text-white">
                        {formatTime(activePreview.time)}
                    </div>
                </div>
            )}
            <div
                className={cn(
                    "absolute left-0 right-0 top-1/2 h-1 -translate-y-1/2 overflow-hidden rounded-[1px] bg-white/18 transition-[height]",
                    activePreview ? "h-1.5" : "h-1",
                )}
            >
                <div className="absolute inset-y-0 left-0 bg-white/35" style={{ width: `${bufferedPercent}%` }} />
                <div className="absolute inset-y-0 left-0 bg-primary" style={{ width: `${progressPercent}%` }} />
            </div>
            <div
                className={cn(
                    "absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary shadow-lg transition-opacity",
                    activePreview ? "opacity-100" : "opacity-0",
                )}
                style={{ left: `${progressPercent}%` }}
            />
        </div>
    )
}

function formatTime(seconds: number) {
    if (!Number.isFinite(seconds) || seconds <= 0) return "0:00"
    const minutes = Math.floor(seconds / 60)
    const rest = Math.floor(seconds % 60)
    return `${minutes}:${String(rest).padStart(2, "0")}`
}
