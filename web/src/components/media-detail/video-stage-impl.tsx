import "@vidstack/react/player/styles/default/theme.css"
import "@vidstack/react/player/styles/default/layouts/video.css"

import { MediaPlayer, MediaProvider } from "@vidstack/react"
import { DefaultVideoLayout, defaultLayoutIcons } from "@vidstack/react/player/layouts/default"
import { Lock, Unlock } from "lucide-react"
import { useCallback, useState } from "react"
import type { Media } from "@/api/types"
import { useIsTouchDevice } from "@/hooks/use-is-touch-device"
import { mediaUrl } from "@/lib/media-url"
import { VideoGestures } from "./video-gestures"

interface VideoStageProps {
    item: Media
    onLoaded: (id: number) => void
    onError: (id: number, message: string) => void
}

export default function VideoStage({ item, onLoaded, onError }: VideoStageProps) {
    const isTouch = useIsTouchDevice()
    const [locked, setLocked] = useState(false)
    const [brightness, setBrightness] = useState(1)

    const handleCanPlay = useCallback(() => onLoaded(item.id), [item.id, onLoaded])
    const handleError = useCallback(() => onError(item.id, "Could not load video"), [item.id, onError])

    return (
        <div
            className="absolute inset-0 flex items-center justify-center"
            style={{ filter: `brightness(${brightness})` }}
        >
            <MediaPlayer
                key={item.id}
                title={item.filename}
                src={{ src: mediaUrl.file(item.id), type: "video/mp4" }}
                poster={mediaUrl.thumbnail(item.id, "xl")}
                playsInline
                crossOrigin="use-credentials"
                aspectRatio={item.width && item.height ? `${item.width}/${item.height}` : "16/9"}
                onCanPlay={handleCanPlay}
                onError={handleError}
                className="w-full h-full"
            >
                <MediaProvider />
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

function LockToggle({ locked, onToggle }: { locked: boolean; onToggle: () => void }) {
    return (
        <button
            type="button"
            onClick={onToggle}
            aria-label={locked ? "Unlock controls" : "Lock controls"}
            className={`absolute left-3 top-1/2 z-30 -translate-y-1/2 flex h-10 w-10 items-center justify-center rounded-full backdrop-blur-md text-white shadow-2xl transition-all ${locked
                ? "bg-black/65 hover:bg-black/80 opacity-100"
                : "bg-black/40 hover:bg-black/60 opacity-70 hover:opacity-100"
            }`}
            style={{ marginTop: "max(env(safe-area-inset-top, 0px), 0px)" }}
        >
            {locked ? <Lock className="h-4 w-4" /> : <Unlock className="h-4 w-4" />}
        </button>
    )
}
