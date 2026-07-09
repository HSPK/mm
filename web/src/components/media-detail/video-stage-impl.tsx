import "@vidstack/react/player/styles/default/theme.css"
import "@vidstack/react/player/styles/default/layouts/video.css"
import "./video-stage.css"

import { MediaPlayer, MediaProvider, useMediaRemote, useMediaState } from "@vidstack/react"
import { DefaultVideoLayout, defaultLayoutIcons } from "@vidstack/react/player/layouts/default"
import { Lock, Unlock } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import type { Media } from "@/api/types"
import { useIsTouchDevice } from "@/hooks/use-is-touch-device"
import { mediaUrl } from "@/lib/media-url"
import { VideoGestures } from "./video-gestures"

interface VideoStageProps {
    item: Media
    keyboardEnabled: boolean
    onLoaded: (id: number) => void
    onError: (id: number, message: string) => void
}

const SEEK_STEP_SECONDS = 10
const VOLUME_STEP = 0.05

export default function VideoStage({ item, keyboardEnabled, onLoaded, onError }: VideoStageProps) {
    const isTouch = useIsTouchDevice()
    const [locked, setLocked] = useState(false)
    const [brightness, setBrightness] = useState(1)

    const handleCanPlay = useCallback(() => onLoaded(item.id), [item.id, onLoaded])
    const handleError = useCallback(() => onError(item.id, "Could not load video"), [item.id, onError])

    return (
        <div
            className="absolute inset-0 flex items-center justify-center bg-black"
            style={{ filter: `brightness(${brightness})` }}
        >
            <MediaPlayer
                key={item.id}
                title={item.filename}
                src={{ src: mediaUrl.file(item.id), type: "video/mp4" }}
                poster={mediaUrl.thumbnail(item.id, "xl")}
                playsInline
                crossOrigin="use-credentials"
                keyTarget="document"
                aspectRatio={item.width && item.height ? `${item.width}/${item.height}` : "16/9"}
                onCanPlay={handleCanPlay}
                onError={handleError}
                className="mm-video-player h-full w-full bg-black [--media-border-radius:0px] [--video-border-radius:0px]"
            >
                <MediaProvider />
                <VideoKeyboardShortcuts enabled={keyboardEnabled && !locked} />
                {!locked && <DefaultVideoLayout icons={defaultLayoutIcons} />}
                {isTouch && (
                    <VideoGestures
                        disabled={locked}
                        onBrightnessChange={setBrightness}
                    />
                )}
                {isTouch && (
                    <LockToggle locked={locked} onToggle={() => setLocked((v) => !v)} />
                )}
            </MediaPlayer>
        </div>
    )
}

function VideoKeyboardShortcuts({ enabled }: { enabled: boolean }) {
    const remote = useMediaRemote()
    const currentTime = useMediaState("currentTime")
    const duration = useMediaState("duration")
    const volume = useMediaState("volume")
    const stateRef = useRef({ currentTime: 0, duration: 0, volume: 1 })

    useEffect(() => {
        stateRef.current = {
            currentTime: currentTime ?? 0,
            duration: duration ?? 0,
            volume: volume ?? 1,
        }
    }, [currentTime, duration, volume])

    useEffect(() => {
        if (!enabled) return

        const onKeyDown = (e: KeyboardEvent) => {
            if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.altKey) return
            if (isTextInputTarget(e.target)) return

            const seekTo = (time: number) => {
                const end = Number.isFinite(stateRef.current.duration) && stateRef.current.duration > 0
                    ? stateRef.current.duration
                    : Number.POSITIVE_INFINITY
                remote.seek(Math.min(Math.max(time, 0), end), e)
            }

            switch (e.key) {
                case " ":
                case "k":
                case "K":
                    e.preventDefault()
                    e.stopPropagation()
                    remote.togglePaused(e)
                    break
                case "ArrowLeft":
                case "j":
                case "J":
                    e.preventDefault()
                    e.stopPropagation()
                    seekTo(stateRef.current.currentTime - SEEK_STEP_SECONDS)
                    break
                case "ArrowRight":
                case "l":
                case "L":
                    e.preventDefault()
                    e.stopPropagation()
                    seekTo(stateRef.current.currentTime + SEEK_STEP_SECONDS)
                    break
                case "ArrowUp":
                    e.preventDefault()
                    e.stopPropagation()
                    remote.changeVolume(Math.min(stateRef.current.volume + VOLUME_STEP, 1), e)
                    break
                case "ArrowDown":
                    e.preventDefault()
                    e.stopPropagation()
                    remote.changeVolume(Math.max(stateRef.current.volume - VOLUME_STEP, 0), e)
                    break
                case "m":
                case "M":
                    e.preventDefault()
                    e.stopPropagation()
                    remote.toggleMuted(e)
                    break
                case "f":
                case "F":
                    e.preventDefault()
                    e.stopPropagation()
                    remote.toggleFullscreen("prefer-media", e)
                    break
                default:
                    break
            }
        }

        document.addEventListener("keydown", onKeyDown, { capture: true })
        return () => document.removeEventListener("keydown", onKeyDown, { capture: true })
    }, [enabled, remote])

    return null
}

function isTextInputTarget(target: EventTarget | null): boolean {
    if (!(target instanceof HTMLElement)) return false
    return Boolean(target.closest("input, textarea, select, [contenteditable='true'], [role='textbox']"))
}

function LockToggle({ locked, onToggle }: { locked: boolean; onToggle: () => void }) {
    return (
        <button
            type="button"
            onClick={onToggle}
            aria-label={locked ? "Unlock controls" : "Lock controls"}
            className={`absolute left-3 top-1/2 z-30 -translate-y-1/2 flex h-10 w-10 items-center justify-center rounded-xl text-white shadow-2xl transition-all ${locked
                ? "bg-black/65 hover:bg-black/80 opacity-100"
                : "bg-black/40 hover:bg-black/60 opacity-70 hover:opacity-100"
            }`}
            style={{ marginTop: "max(env(safe-area-inset-top, 0px), 0px)" }}
        >
            {locked ? <Lock className="h-4 w-4" /> : <Unlock className="h-4 w-4" />}
        </button>
    )
}
