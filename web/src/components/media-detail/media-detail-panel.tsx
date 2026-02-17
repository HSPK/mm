import { useState, useCallback, useEffect } from "react"
import { createPortal } from "react-dom"
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch"

import { api } from "@/api/client"
import type { Media } from "@/api/types"
import {
    ChevronLeft,
    Info,
    Download,
    Trash2,
    Pencil,
} from "lucide-react"
import { getMediaSrc, getThumbnailSrc, getImageSrc } from "@/lib/media-url"
import { InfoDialog } from "./info-dialog"

// ─── Main Component ────────────────────────────────────────

interface Props {
    items: Media[]
    startIndex: number
    onClose: () => void
    onDelete?: (id: number) => void
}

export function MediaDetailPanel({ items, startIndex, onClose, onDelete }: Props) {
    const [showInfo, setShowInfo] = useState(false)
    const [initialEditMode, setInitialEditMode] = useState(false)
    const [currentIndex, setCurrentIndex] = useState(startIndex)
    const [fadeKey, setFadeKey] = useState(currentIndex)
    const [fadeIn, setFadeIn] = useState(true)
    const [deleting, setDeleting] = useState(false)

    const currentItem = items[currentIndex]
    const isVideo = currentItem?.media_type === "video"

    const openInfo = (edit = false) => {
        setInitialEditMode(edit)
        setShowInfo(true)
    }

    const navigateTo = useCallback((nextIndex: number) => {
        if (nextIndex === currentIndex || nextIndex < 0 || nextIndex >= items.length) return
        setFadeIn(false)
        setTimeout(() => {
            setCurrentIndex(nextIndex)
            setFadeKey(nextIndex)
            requestAnimationFrame(() => setFadeIn(true))
        }, 180)
    }, [currentIndex, items.length])
    const goPrev = useCallback(() => navigateTo(currentIndex - 1), [navigateTo, currentIndex])
    const goNext = useCallback(() => navigateTo(currentIndex + 1), [navigateTo, currentIndex])

    // Keyboard navigation
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if (showInfo) return
            if (e.key === "ArrowLeft") goPrev()
            else if (e.key === "ArrowRight") goNext()
            else if (e.key === "Escape") onClose()
        }
        window.addEventListener("keydown", onKey)
        return () => window.removeEventListener("keydown", onKey)
    }, [goPrev, goNext, onClose, showInfo])

    // Prevent body scroll
    useEffect(() => {
        const prev = document.body.style.overflow
        document.body.style.overflow = "hidden"
        return () => { document.body.style.overflow = prev }
    }, [])

    const handleDownload = async () => {
        if (!currentItem) return
        try {
            const resp = await api.get(`/media/${currentItem.id}/file`, { responseType: "blob" })
            const url = URL.createObjectURL(resp.data)
            const a = document.createElement("a")
            a.href = url
            a.download = currentItem.filename
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
        } catch { /* */ }
    }

    const handleDelete = async () => {
        if (!currentItem || deleting) return

        setDeleting(true)
        try {
            await api.delete(`/media/${currentItem.id}`)
            onDelete?.(currentItem.id)
            if (items.length <= 1) {
                onClose()
            } else if (currentIndex >= items.length - 1) {
                const newIdx = currentIndex - 1
                setCurrentIndex(newIdx)
                setFadeKey(newIdx)
            }
        } catch {
            /* */
        } finally {
            setDeleting(false)
        }
    }

    const actionBtnClass = (active = false) =>
        `flex items-center justify-center w-10 h-10 rounded-full transition-all duration-100 active:scale-90 ${active
            ? "text-white bg-white/20"
            : "text-white/70 hover:text-white hover:bg-white/10"
        }`

    return createPortal(
        <div className="fixed inset-0 z-[9999] flex flex-col bg-black select-none">
            {/* ── Top bar ── */}
            <div
                className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-3 pb-3"
                style={{
                    paddingTop: "max(env(safe-area-inset-top, 0px), 12px)",
                    background: "linear-gradient(to bottom, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.25) 60%, transparent 100%)",
                }}
            >
                <button
                    type="button"
                    onClick={onClose}
                    className="flex items-center justify-center w-10 h-10 rounded-full text-white/80 hover:text-white hover:bg-white/10 active:scale-90 transition-all duration-100"
                    aria-label="Back"
                >
                    <ChevronLeft className="h-6 w-6" />
                </button>

                <div className="flex items-center gap-1">
                    <button type="button" onClick={() => openInfo(false)} className={actionBtnClass(showInfo && !initialEditMode)} aria-label="Info">
                        <Info className="h-[1.2rem] w-[1.2rem]" strokeWidth={showInfo && !initialEditMode ? 2.2 : 1.8} />
                    </button>
                    <button type="button" onClick={() => openInfo(true)} className={actionBtnClass(showInfo && initialEditMode)} aria-label="Edit">
                        <Pencil className="h-[1.2rem] w-[1.2rem]" strokeWidth={showInfo && initialEditMode ? 2.2 : 1.8} />
                    </button>
                    <button type="button" onClick={handleDownload} className={actionBtnClass()} aria-label="Download">
                        <Download className="h-[1.2rem] w-[1.2rem]" strokeWidth={1.8} />
                    </button>
                    <button type="button" onClick={handleDelete} className={actionBtnClass()} aria-label="Delete" disabled={deleting}>
                        <Trash2 className="h-[1.2rem] w-[1.2rem]" strokeWidth={1.8} />
                    </button>
                </div>
            </div>

            {/* ── Media area ── */}
            <div className="flex-1 relative overflow-hidden">
                <div
                    key={fadeKey}
                    className="absolute inset-0 transition-opacity duration-200 ease-in-out"
                    style={{ opacity: fadeIn ? 1 : 0 }}
                >
                    {isVideo ? (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <video
                                key={currentItem.id}
                                src={getMediaSrc(currentItem.id)}
                                poster={getThumbnailSrc(currentItem.id)}
                                controls
                                playsInline
                                preload="none"
                                crossOrigin="use-credentials"
                                className="max-w-full max-h-full object-contain"
                            />
                        </div>
                    ) : (
                        <TransformWrapper
                            key={currentItem.id}
                            initialScale={1}
                            minScale={1}
                            maxScale={10}
                            centerOnInit
                            limitToBounds
                            wheel={{ step: 0.06 }}
                            pinch={{ disabled: true }}
                            doubleClick={{ mode: "toggle", step: 3 }}
                            panning={{ velocityDisabled: false }}
                        >
                            <TransformComponent
                                wrapperStyle={{ width: "100%", height: "100%" }}
                            >
                                <img
                                    src={getImageSrc(currentItem)}
                                    alt={currentItem.filename}
                                    crossOrigin="use-credentials"
                                    draggable={false}
                                    style={{
                                        maxWidth: "100vw",
                                        maxHeight: "100vh",
                                        objectFit: "contain",
                                        userSelect: "none",
                                        WebkitUserSelect: "none",
                                    }}
                                />
                            </TransformComponent>
                        </TransformWrapper>
                    )}
                </div>
            </div>

            {/* ── Info Dialog ── */}
            <InfoDialog
                mediaId={currentItem?.id ?? 0}
                open={showInfo}
                initialEditMode={initialEditMode}
                onClose={() => setShowInfo(false)}
                onNavigate={onClose}
            />
        </div>,
        document.body,
    )
}
