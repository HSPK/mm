import { useEffect, useState, useRef, useCallback } from "react"
import Lightbox, { type Slide } from "yet-another-react-lightbox"
import Zoom from "yet-another-react-lightbox/plugins/zoom"
import "yet-another-react-lightbox/styles.css"
import "yet-another-react-lightbox/plugins/thumbnails.css"

import { api } from "@/api/client"
import type { Media, MediaDetail as MediaDetailType } from "@/api/types"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
    Info,
    X,
    Calendar,
    Camera,
    Aperture,
    Ruler,
    Timer,
    Gauge,
    Maximize2,
    MapPin,
    Tag,
    FileText,
    Star,
    ChevronLeft,
    ChevronRight,
    Loader2,
} from "lucide-react"
import { StarRating } from "@/components/ui/star-rating"

// ─── Constants ─────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api"

// ─── Helper: Media URLs (token sent via cookie) ───────────
function getMediaSrc(id: number) {
    return `${API_BASE}/media/${id}/file`
}

function getThumbnailSrc(id: number) {
    return `${API_BASE}/media/${id}/thumbnail?size=xl`
}

function getPosterSrc(id: number) {
    return `${API_BASE}/media/${id}/thumbnail?size=xl`
}

// ─── Component: Image Slide with thumbnail placeholder ─────
function ImageSlide({ slide }: { slide: Slide & { poster?: string } }) {
    const [loaded, setLoaded] = useState(false)
    const thumbSrc = slide.poster

    return (
        <div className="w-full h-full flex items-center justify-center relative">
            {/* Blurred thumbnail placeholder */}
            {!loaded && thumbSrc && (
                <img
                    src={thumbSrc}
                    crossOrigin="use-credentials"
                    alt=""
                    className="absolute inset-0 m-auto max-w-full max-h-full object-contain"
                    style={{ filter: "blur(20px)", transform: "scale(1.05)", opacity: 0.7 }}
                />
            )}
            {/* Full resolution image */}
            <img
                src={slide.src}
                crossOrigin="use-credentials"
                alt=""
                onLoad={() => setLoaded(true)}
                className="max-w-full max-h-full object-contain relative z-10"
                style={{
                    maxHeight: "100vh",
                    transition: "opacity 0.3s ease",
                    opacity: loaded ? 1 : 0,
                }}
            />
        </div>
    )
}

// ─── Component: Native Video Slide ─────────────────────────
function VideoSlide({ slide }: { slide: Slide }) {
    const videoRef = useRef<HTMLVideoElement>(null)

    // Native HTML5 video - let browser handle loading UI
    return (
        <div className="w-full h-full flex items-center justify-center bg-black" onKeyDown={(e) => e.stopPropagation()}>
            <video
                ref={videoRef}
                src={slide.src}
                poster={slide.poster}
                controls
                playsInline
                preload="none"
                crossOrigin="use-credentials"
                className="max-w-full max-h-full object-contain"
                style={{ maxHeight: '100vh' }}
            />
        </div>
    )
}

// ─── Component: Metadata Sidebar ───────────────────────────
function MetadataSidebar({
    mediaId,
    onClose
}: {
    mediaId: number
    onClose: () => void
}) {
    const [detail, setDetail] = useState<MediaDetailType | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        let mounted = true
        setLoading(true)
        api.get<MediaDetailType>(`/media/${mediaId}`)
            .then(res => {
                if (mounted) setDetail(res.data)
            })
            .catch(() => {
                if (mounted) setDetail(null)
            })
            .finally(() => {
                if (mounted) setLoading(false)
            })
        return () => { mounted = false }
    }, [mediaId])

    const handleRating = async (rating: number) => {
        if (!detail) return
        try {
            await api.put(`/media/${mediaId}/rating`, { rating })
            setDetail(d => (d ? { ...d, rating } : d))
        } catch { }
    }

    if (loading) return (
        <div className="w-80 h-full bg-background border-l p-4 flex items-center justify-center text-muted-foreground absolute right-0 top-0 bottom-0 z-[1000]">
            Loading info...
        </div>
    )

    if (!detail) return null

    const md = detail.metadata

    return (
        <div className="w-80 h-full bg-background/95 backdrop-blur-md border-l flex flex-col shadow-2xl absolute right-0 top-0 bottom-0 z-[1000] text-foreground">
            <div className="flex items-center justify-between p-4 border-b bg-background/50">
                <h3 className="font-medium text-sm text-foreground">Info</h3>
                <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8 hover:bg-muted">
                    <X className="h-4 w-4" />
                </Button>
            </div>

            <ScrollArea className="flex-1">
                <div className="p-4 space-y-6 text-sm">

                    {/* Rating */}
                    <div className="flex items-center justify-between">
                        <span className="text-muted-foreground font-medium text-xs uppercase tracking-wider">Rating</span>
                        <div className="bg-muted/50 px-2 py-1 rounded-md">
                            <StarRating value={detail.rating} onChange={handleRating} interactive size={16} />
                        </div>
                    </div>

                    <div className="h-px bg-border/50" />

                    {/* Date */}
                    {md?.date_taken && (
                        <div className="space-y-1">
                            <div className="flex items-center gap-2 text-muted-foreground font-medium text-xs uppercase tracking-wider">
                                <Calendar className="h-3.5 w-3.5" />
                                Date Taken
                            </div>
                            <div className="pl-6 font-medium">
                                {new Date(md.date_taken).toLocaleString(undefined, {
                                    weekday: 'short',
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                })}
                            </div>
                        </div>
                    )}

                    {/* Camera */}
                    {(md?.camera_model || md?.lens_model) && (
                        <div className="space-y-2">
                            <div className="flex items-center gap-2 text-muted-foreground font-medium text-xs uppercase tracking-wider">
                                <Camera className="h-3.5 w-3.5" />
                                Camera
                            </div>
                            <div className="pl-6 grid gap-1.5">
                                {md.camera_model && <div className="font-medium">{md.camera_model}</div>}
                                {md.lens_model && <div className="text-xs text-muted-foreground">{md.lens_model}</div>}

                                <div className="flex flex-wrap gap-2 mt-1 text-xs font-mono text-muted-foreground">
                                    {md.focal_length && <span className="bg-muted px-1.5 py-0.5 rounded border">{md.focal_length}mm</span>}
                                    {md.aperture && <span className="bg-muted px-1.5 py-0.5 rounded border">ƒ/{md.aperture}</span>}
                                    {md.iso && <span className="bg-muted px-1.5 py-0.5 rounded border">ISO {md.iso}</span>}
                                    {md.shutter_speed && <span className="bg-muted px-1.5 py-0.5 rounded border">{md.shutter_speed}s</span>}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* File */}
                    <div className="space-y-2">
                        <div className="flex items-center gap-2 text-muted-foreground font-medium text-xs uppercase tracking-wider">
                            <FileText className="h-3.5 w-3.5" />
                            File Info
                        </div>
                        <div className="pl-6 grid gap-1.5 text-xs">
                            <div className="break-all font-mono bg-muted/30 p-1.5 rounded border text-muted-foreground select-all">
                                {detail.filename}
                            </div>
                            <div className="flex items-center justify-between text-muted-foreground px-1">
                                <span className="uppercase font-bold text-[10px]">{detail.media_type}</span>
                                <span>{(detail.file_size / 1024 / 1024).toFixed(2)} MB</span>
                                {md?.width && <span>{md.width} × {md.height}</span>}
                            </div>
                            <div className="text-[10px] text-muted-foreground/50 break-all px-1 select-all font-mono">
                                {detail.path}
                            </div>
                        </div>
                    </div>

                    <div className="h-px bg-border/50" />

                    {/* Tags */}
                    <div className="space-y-2">
                        <div className="flex items-center gap-2 text-muted-foreground font-medium text-xs uppercase tracking-wider">
                            <Tag className="h-3.5 w-3.5" />
                            Tags
                        </div>
                        <div className="pl-6 flex flex-wrap gap-1.5">
                            {detail.tags.map(t => (
                                <span key={t.name} className="px-2.5 py-1 bg-secondary text-secondary-foreground rounded-full text-xs font-medium border border-secondary-foreground/10">
                                    {t.name}
                                </span>
                            ))}
                            {detail.tags.length === 0 && <span className="text-muted-foreground italic text-xs">No tags</span>}
                        </div>
                    </div>
                </div>
            </ScrollArea>
        </div>
    )
}

// ─── Main Component ────────────────────────────────────────

interface Props {
    items: Media[]
    startIndex: number
    onClose: () => void
}

export function MediaDetailPanel({ items, startIndex, onClose }: Props) {
    const [showInfo, setShowInfo] = useState(false)
    const [currentIndex, setCurrentIndex] = useState(startIndex)

    // Construct slides on the fly or memoize
    // Note: Lightbox might re-render heavily if slides prop changes ref, but items.map is fast for small N
    // ideally items is stable.
    const slides = items.map(item => {
        const isVideo = item.media_type === "video"
        return {
            type: isVideo ? "video" : "image",
            src: getMediaSrc(item.id),
            poster: isVideo ? getPosterSrc(item.id) : getThumbnailSrc(item.id),
            width: item.width || 1920,
            height: item.height || 1080,
            imageFit: "contain",
        } as Slide
    })

    const currentItem = items[currentIndex]

    return (
        <>
            <Lightbox
                open={true}
                close={() => onClose()}
                index={currentIndex}
                slides={slides}
                on={{
                    view: ({ index }) => setCurrentIndex(index)
                }}
                plugins={[Zoom]}
                zoom={{ maxZoomPixelRatio: 5, scrollToZoom: true }}
                render={{
                    slide: ({ slide }) => {
                        if (slide.type === "video") {
                            return <VideoSlide slide={slide} />
                        }
                        return <ImageSlide slide={slide} />
                    },
                    iconPrev: () => <ChevronLeft className="w-10 h-10 text-white drop-shadow-lg" />,
                    iconNext: () => <ChevronRight className="w-10 h-10 text-white drop-shadow-lg" />,
                    buttonPrev: items.length <= 1 ? () => null : undefined,
                    buttonNext: items.length <= 1 ? () => null : undefined,
                }}
                toolbar={{
                    buttons: [
                        <Button
                            key="info-toggle"
                            variant="ghost"
                            size="icon"
                            onClick={() => setShowInfo(!showInfo)}
                            className={`yarl__button ${showInfo ? "bg-white/20 text-white" : "text-white/70 hover:text-white"}`}
                            title="Toggle Info"
                        >
                            <Info className="h-5 w-5" />
                        </Button>,
                        "zoom",
                        "close"
                    ]
                }}
                styles={{
                    container: { backgroundColor: "rgba(0, 0, 0, .95)" },
                    // Make space for sidebar if open? No, overlay is better for mobile/desktop unification usually
                    // but we can add paddingRight if desktop
                }}
                className={showInfo ? "has-sidebar" : ""}
            />

            {showInfo && currentItem && (
                <MetadataSidebar
                    mediaId={currentItem.id}
                    onClose={() => setShowInfo(false)}
                />
            )}
        </>
    )
}
