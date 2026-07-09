import { createPortal } from "react-dom"
import { useEffect, useMemo, useRef, useState } from "react"
import { ListMusic, Pause, Play, Repeat, Repeat1, Shuffle, SkipBack, SkipForward } from "lucide-react"
import { api } from "@/api/client"
import { currentTrack, usePlayerStore } from "@/stores/player"
import { notify } from "@/stores/notifications"
import { PlayerButton } from "./music-player-button"
import { CoverButton, FullscreenPlayer, ProgressBar, VolumeControl } from "./music-player-ui"
import {
    type AudioInfoResponse,
    activeLyricLine,
    isKeyboardControlTarget,
    organizerFileUrl,
    parseLyrics,
    repeatLabel,
    validDuration,
} from "./music-player-utils"
import { useEnrichedPlayerTrack, usePrefetchEnrichedPlayerTracks } from "./use-enriched-player-track"

export function GlobalMusicPlayer() {
    const audioRef = useRef<HTMLAudioElement | null>(null)
    const registeredPlayRef = useRef<string | null>(null)
    const [fullscreen, setFullscreen] = useState(false)
    const [fullscreenQueueOpen, setFullscreenQueueOpen] = useState(false)
    const queue = usePlayerStore((state) => state.queue)
    const index = usePlayerStore((state) => state.index)
    const isPlaying = usePlayerStore((state) => state.isPlaying)
    const currentTime = usePlayerStore((state) => state.currentTime)
    const duration = usePlayerStore((state) => state.duration)
    const volume = usePlayerStore((state) => state.volume)
    const shuffle = usePlayerStore((state) => state.shuffle)
    const repeatMode = usePlayerStore((state) => state.repeatMode)
    const setQueue = usePlayerStore((state) => state.setQueue)
    const play = usePlayerStore((state) => state.play)
    const pause = usePlayerStore((state) => state.pause)
    const toggle = usePlayerStore((state) => state.toggle)
    const next = usePlayerStore((state) => state.next)
    const previous = usePlayerStore((state) => state.previous)
    const toggleShuffle = usePlayerStore((state) => state.toggleShuffle)
    const cycleRepeat = usePlayerStore((state) => state.cycleRepeat)
    const registerPlay = usePlayerStore((state) => state.registerPlay)
    const setTime = usePlayerStore((state) => state.setTime)
    const setDuration = usePlayerStore((state) => state.setDuration)
    const setVolume = usePlayerStore((state) => state.setVolume)
    const track = useMemo(() => currentTrack({ queue, index }), [index, queue])
    const trackUrl = useMemo(() => track?.playbackId ? organizerFileUrl(track.playbackId) : "", [track])
    const displayDuration = duration > 0 ? duration : track?.duration ?? 0
    const lyrics = useMemo(() => parseLyrics(track), [track])
    const activeLyricIndex = useMemo(() => activeLyricLine(lyrics.synced, currentTime), [currentTime, lyrics.synced])
    useEnrichedPlayerTrack(track)
    usePrefetchEnrichedPlayerTracks(queue, index)

    const openFullscreenPlayer = (showQueue: boolean) => {
        setFullscreenQueueOpen(showQueue)
        setFullscreen(true)
    }

    useEffect(() => {
        const audio = audioRef.current
        if (!audio || !trackUrl || !track?.playbackId) return
        if (audio.src !== new URL(trackUrl, window.location.href).href) {
            audio.src = trackUrl
            audio.load()
        }
        setDuration(track?.duration ?? 0)
        const playbackId = track.playbackId
        void api.get<AudioInfoResponse>("/player/audio/info", { params: { playback_id: playbackId } })
            .then((response) => {
                const duration = response.data.duration
                if (duration && duration > 0 && usePlayerStore.getState().queue[usePlayerStore.getState().index]?.playbackId === playbackId) {
                    setDuration(duration)
                }
            })
            .catch(() => undefined)
        if (usePlayerStore.getState().isPlaying) {
            void audio.play().catch(() => {
                notify.error("Playback failed", "The browser could not start this audio file.")
                pause()
            })
        }
    }, [pause, setDuration, track?.playbackId, trackUrl])

    useEffect(() => {
        if (duration > 0 || !track?.duration) return
        setDuration(track.duration)
    }, [duration, setDuration, track?.duration])

    useEffect(() => {
        const audio = audioRef.current
        if (!audio) return
        audio.volume = volume
    }, [volume])

    useEffect(() => {
        if (!track) {
            registeredPlayRef.current = null
            return
        }
        if (!isPlaying || registeredPlayRef.current === track.id) return
        registeredPlayRef.current = track.id
        registerPlay(track)
    }, [isPlaying, registerPlay, track])

    useEffect(() => {
        const audio = audioRef.current
        if (!audio || !track) return
        if (isPlaying) {
            void audio.play().catch(() => {
                notify.error("Playback failed", "The browser could not play this audio file.")
                pause()
            })
        }
        else audio.pause()
    }, [isPlaying, pause, track])

    useEffect(() => {
        if (!("mediaSession" in navigator) || !track) return
        navigator.mediaSession.metadata = new MediaMetadata({
            title: track.title,
            artist: track.artist,
            album: track.album,
            artwork: track.artworkUrl ? [{ src: track.artworkUrl, sizes: "512x512", type: "image/jpeg" }] : [],
        })
        navigator.mediaSession.setActionHandler("play", play)
        navigator.mediaSession.setActionHandler("pause", pause)
        navigator.mediaSession.setActionHandler("previoustrack", previous)
        navigator.mediaSession.setActionHandler("nexttrack", next)
        navigator.mediaSession.setActionHandler("seekto", (details) => {
            if (details.seekTime != null && audioRef.current) {
                audioRef.current.currentTime = details.seekTime
                setTime(details.seekTime)
            }
        })
        return () => {
            navigator.mediaSession.setActionHandler("play", null)
            navigator.mediaSession.setActionHandler("pause", null)
            navigator.mediaSession.setActionHandler("previoustrack", null)
            navigator.mediaSession.setActionHandler("nexttrack", null)
            navigator.mediaSession.setActionHandler("seekto", null)
        }
    }, [next, pause, play, previous, setTime, track])

    useEffect(() => {
        if (!fullscreen) return
        const previousOverflow = document.body.style.overflow
        document.body.style.overflow = "hidden"
        return () => {
            document.body.style.overflow = previousOverflow
        }
    }, [fullscreen])

    useEffect(() => {
        if (!fullscreen) return
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                setFullscreen(false)
                return
            }
            if (event.key.toLowerCase() === "f" && !event.repeat && !isKeyboardControlTarget(event.target)) {
                event.preventDefault()
                void toggleBrowserFullscreen().catch(() => undefined)
                return
            }
            if (event.code !== "Space" || event.repeat || isKeyboardControlTarget(event.target)) return
            event.preventDefault()
            toggle()
        }
        window.addEventListener("keydown", handleKeyDown)
        return () => window.removeEventListener("keydown", handleKeyDown)
    }, [fullscreen, toggle])

    if (!track) return null

    const seek = (time: number) => {
        if (audioRef.current) audioRef.current.currentTime = time
        setTime(time)
    }

    const handleEnded = () => {
        if (usePlayerStore.getState().repeatMode === "one" && audioRef.current) {
            audioRef.current.currentTime = 0
            setTime(0)
            void audioRef.current.play().catch(() => {
                notify.error("Playback failed", `${track.title} could not be replayed.`)
                pause()
            })
            return
        }
        next()
    }

    return (
        <div
            className="pointer-events-none fixed bottom-5 left-[4.75rem] right-0 z-50 px-3 sm:left-64 sm:px-6"
            style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
        >
            <audio
                ref={audioRef}
                preload="metadata"
                onTimeUpdate={(event) => setTime(event.currentTarget.currentTime)}
                onDurationChange={(event) => {
                    const duration = validDuration(event.currentTarget.duration)
                    if (duration != null) setDuration(duration)
                }}
                onLoadedMetadata={(event) => {
                    const duration = validDuration(event.currentTarget.duration)
                    if (duration != null) setDuration(duration)
                }}
                onError={() => {
                    const code = audioRef.current?.error?.code
                    notify.error("Playback failed", `${track.title} could not be played${code ? ` (code ${code})` : ""}.`)
                    pause()
                }}
                onEnded={handleEnded}
            />
            <div className="pointer-events-auto w-full rounded-[1.5rem] border border-border bg-card px-4 py-2.5 shadow-2xl shadow-black/18">
                <div className="grid items-center gap-3 lg:grid-cols-[minmax(0,1fr)_auto_auto]">
                    <div className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] items-center gap-3">
                        <CoverButton track={track} onClick={() => openFullscreenPlayer(false)} />
                        <div className="min-w-0">
                            <div className="min-w-0 text-left">
                                <div className="truncate text-[15px] font-bold leading-tight">{track.title}</div>
                                <div className="mt-0.5 truncate text-[13px] text-muted-foreground">{[track.artist, track.album].filter(Boolean).join(" - ")}</div>
                            </div>
                            <div className="mt-1.5 max-w-xl">
                                <ProgressBar currentTime={currentTime} duration={displayDuration} onSeek={seek} compact />
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center justify-center gap-1 sm:gap-2">
                        <PlayerButton onClick={toggleShuffle} label="Shuffle" active={shuffle} small className="hidden bg-transparent hover:bg-secondary/70 sm:flex">
                            <Shuffle className="h-4 w-4" />
                        </PlayerButton>
                        <PlayerButton onClick={previous} label="Previous" small>
                            <SkipBack className="h-4 w-4" />
                        </PlayerButton>
                        <PlayerButton onClick={toggle} label={isPlaying ? "Pause" : "Play"} primary>
                            {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="ml-0.5 h-5 w-5" />}
                        </PlayerButton>
                        <PlayerButton onClick={next} label="Next" disabled={queue.length <= 1 && repeatMode !== "one"} small>
                            <SkipForward className="h-4 w-4" />
                        </PlayerButton>
                        <PlayerButton onClick={cycleRepeat} label={repeatLabel(repeatMode)} active={repeatMode !== "off"} small className="hidden bg-transparent hover:bg-secondary/70 sm:flex">
                            {repeatMode === "one" ? <Repeat1 className="h-4 w-4" /> : <Repeat className="h-4 w-4" />}
                        </PlayerButton>
                    </div>

                    <div className="hidden min-w-0 items-center justify-end gap-2 lg:flex">
                        <VolumeControl volume={volume} onChange={setVolume} />
                        <button
                            type="button"
                            onClick={() => openFullscreenPlayer(true)}
                            className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary/70 text-muted-foreground hover:text-foreground"
                            aria-label="Open queue"
                            title="Open queue"
                        >
                            <ListMusic className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            </div>
            {fullscreen && typeof document !== "undefined" && createPortal(
                <FullscreenPlayer
                    track={track}
                    queue={queue}
                    index={index}
                    currentTime={currentTime}
                    duration={displayDuration}
                    isPlaying={isPlaying}
                    shuffle={shuffle}
                    repeatMode={repeatMode}
                    lyrics={lyrics}
                    activeLyricIndex={activeLyricIndex}
                    showQueue={fullscreenQueueOpen}
                    onShowQueueChange={setFullscreenQueueOpen}
                    onClose={() => setFullscreen(false)}
                    onSeek={seek}
                    onPlayQueueItem={(queueIndex) => setQueue(queue, queueIndex, true)}
                    onToggle={toggle}
                    onPrevious={previous}
                    onNext={next}
                    onShuffle={toggleShuffle}
                    onRepeat={cycleRepeat}
                />,
                document.body,
            )}
        </div>
    )
}

async function toggleBrowserFullscreen() {
    if (document.fullscreenElement) {
        await document.exitFullscreen()
        return
    }
    await document.documentElement.requestFullscreen()
}
