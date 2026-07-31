import { createPortal } from "react-dom"
import { useCallback, useEffect, useState } from "react"
import { ListMusic, Pause, Play, Repeat, Repeat1, Shuffle, SkipBack, SkipForward } from "lucide-react"
import { PlayerButton } from "./music-player-button"
import { CoverButton, FullscreenPlayer, ProgressBar, VolumeControl } from "./music-player-ui"
import { isKeyboardControlTarget, repeatLabel } from "./music-player-utils"
import { useMusicPlayerController } from "./use-music-player-controller"

export function GlobalMusicPlayer() {
    const [fullscreen, setFullscreen] = useState(false)
    const [fullscreenQueueOpen, setFullscreenQueueOpen] = useState(false)
    const {
        audioRef,
        track,
        queue,
        index,
        currentTime,
        duration,
        volume,
        shuffle,
        repeatMode,
        isPlaying,
        lyrics,
        lyricsStatus,
        retryLyrics,
        activeLyricIndex,
        selectQueueIndex,
        setVolume,
        toggleShuffle,
        cycleRepeat,
        toggle,
        next,
        previous,
        seek,
        audioHandlers,
    } = useMusicPlayerController()
    const playQueueItem = useCallback((queueIndex: number) => {
        selectQueueIndex(queueIndex, true, true)
    }, [selectQueueIndex])

    const openFullscreenPlayer = (showQueue: boolean) => {
        setFullscreenQueueOpen(showQueue)
        setFullscreen(true)
    }

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

    return (
        <>
            <audio ref={audioRef} preload="metadata" {...audioHandlers} />
            {track && (
                <div
                    className="pointer-events-none fixed bottom-5 left-[4.75rem] right-0 z-50 px-3 sm:left-64 sm:px-6"
                    style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
                >
            <div className="pointer-events-auto w-full rounded-[1.5rem] border border-border bg-card px-4 py-2.5 shadow-2xl shadow-black/18">
                <div className="grid items-center gap-3 lg:grid-cols-[minmax(0,1fr)_auto_auto]">
                    <div className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] items-center gap-3">
                        <CoverButton track={track} onClick={() => openFullscreenPlayer(false)} />
                        <div className="min-w-0">
                            <div className="min-w-0 text-left">
                                <div className="truncate text-[15px] font-bold leading-tight">{track.title}</div>
                                <div className="mt-0.5 truncate text-[13px] text-muted-foreground">
                                    {[track.artist, track.album].filter(Boolean).join(" - ")}
                                </div>
                            </div>
                            <div className="mt-1.5 max-w-xl">
                                <ProgressBar
                                    currentTime={currentTime}
                                    duration={duration}
                                    onSeek={seek}
                                    compact
                                />
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
                    duration={duration}
                    isPlaying={isPlaying}
                    shuffle={shuffle}
                    repeatMode={repeatMode}
                    lyrics={lyrics}
                    lyricsStatus={lyricsStatus}
                    onRetryLyrics={retryLyrics}
                    activeLyricIndex={activeLyricIndex}
                    showQueue={fullscreenQueueOpen}
                    onShowQueueChange={setFullscreenQueueOpen}
                    onClose={() => setFullscreen(false)}
                    onSeek={seek}
                    onPlayQueueItem={playQueueItem}
                    onToggle={toggle}
                    onPrevious={previous}
                    onNext={next}
                    onShuffle={toggleShuffle}
                    onRepeat={cycleRepeat}
                />,
                document.body,
            )}
                </div>
            )}
        </>
    )
}

async function toggleBrowserFullscreen() {
    if (document.fullscreenElement) {
        await document.exitFullscreen()
        return
    }
    await document.documentElement.requestFullscreen()
}
