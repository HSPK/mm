import { useEffect, useState, useCallback } from "react"
import { createPortal } from "react-dom"
import { useNavigate } from "react-router-dom"
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch"

import { api } from "@/api/client"
import type { Media, MediaDetail as MediaDetailType } from "@/api/types"
import {
    X,
    Calendar,
    Camera,
    MapPin,
    Tag,
    FileText,
    ChevronLeft,
    Loader2,
    Info,
    Download,
    Trash2,
    Pencil,
    Plus,
    Check,
} from "lucide-react"
import { StarRating } from "@/components/ui/star-rating"
import { useReverseGeocode } from "@/hooks/use-reverse-geocode"
import { useMediaStore } from "@/stores/media"

// ─── Constants ─────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api"

// Extensions browsers can't render natively — use server-converted preview
const RAW_EXTENSIONS = new Set([
    ".heic", ".heif",
    ".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw",
])

function getMediaSrc(id: number) {
    return `${API_BASE}/media/${id}/file`
}
function getPreviewSrc(id: number) {
    return `${API_BASE}/media/${id}/preview`
}
function getThumbnailSrc(id: number) {
    return `${API_BASE}/media/${id}/thumbnail?size=xl`
}
/** For images: use preview (WebP) for RAW/HEIC, original file for browser-native formats */
function getImageSrc(item: { id: number; extension: string }) {
    return RAW_EXTENSIONS.has(item.extension.toLowerCase())
        ? getPreviewSrc(item.id)
        : getMediaSrc(item.id)
}

// ─── EXIF Chip ─────────────────────────────────────────────

function ExifChip({ children }: { children: React.ReactNode }) {
    return (
        <span className="text-[11px] font-mono text-white/55 bg-white/[0.06] px-2 py-[3px] rounded-md border border-white/[0.04]">
            {children}
        </span>
    )
}

// ─── Info Dialog (centered modal) ──────────────────────────

function InfoDialog({
    mediaId,
    open,
    initialEditMode = false,
    onClose,
    onNavigate,
}: {
    mediaId: number
    open: boolean
    initialEditMode?: boolean
    onClose: () => void
    onNavigate: () => void
}) {
    const navigate = useNavigate()
    const setFilters = useMediaStore((s) => s.setFilters)
    const [detail, setDetail] = useState<MediaDetailType | null>(null)
    const [loading, setLoading] = useState(false)
    const [isEditing, setIsEditing] = useState(false)
    const [editForm, setEditForm] = useState<Partial<NonNullable<MediaDetailType["metadata"]>>>({})
    const [saving, setSaving] = useState(false)
    const [tagInput, setTagInput] = useState("")

    useEffect(() => { setIsEditing(initialEditMode) }, [initialEditMode, open])

    const md = detail?.metadata ?? null
    // Use stored location label if available, otherwise reverse geocode on the fly
    const dynamicPlace = useReverseGeocode(!md?.location_label ? md?.gps_lat : null, !md?.location_label ? md?.gps_lon : null)
    const placeName = md?.location_label || dynamicPlace

    useEffect(() => {
        if (!open || !mediaId) return
        let alive = true
        setLoading(true)
        api.get<MediaDetailType>(`/media/${mediaId}`)
            .then((r) => {
                if (alive) {
                    setDetail(r.data)
                    setEditForm(r.data.metadata || {})
                }
            })
            .catch(() => { if (alive) setDetail(null) })
            .finally(() => { if (alive) setLoading(false) })
        return () => { alive = false }
    }, [mediaId, open])

    const handleSave = async () => {
        if (!detail) return
        setSaving(true)
        try {
            // Check diffs or just send it? API merges updates.
            // Convert date_taken to ISO string if needed
            const payload = { ...editForm }

            // Should validate date format if changed manually
            // But HTML input type="datetime-local" sets standard format usually

            const res = await api.patch<MediaDetailType>(`/media/${mediaId}/metadata`, payload)
            setDetail(res.data)
            setEditForm(res.data.metadata || {})
            setIsEditing(false)
        } catch (err) {
            console.error(err)
            alert("Failed to save metadata")
        } finally {
            setSaving(false)
        }
    }

    const cancelEdit = () => {
        setIsEditing(false)
        setEditForm(detail?.metadata || {})
    }

    const handleRating = async (rating: number) => {
        if (!detail) return
        try {
            await api.put(`/media/${mediaId}/rating`, { rating })
            setDetail((d) => (d ? { ...d, rating } : d))
        } catch { /* */ }
    }

    const handleAddTag = async () => {
        const name = tagInput.trim()
        if (!name || !detail) return
        try {
            await api.post(`/media/${mediaId}/tags`, { tags: [name] })
            setDetail((d) =>
                d ? { ...d, tags: [...d.tags, { name, source: "manual", confidence: null }] } : d,
            )
            setTagInput("")
        } catch { /* */ }
    }

    const handleRemoveTag = async (tagName: string) => {
        if (!detail) return
        try {
            await api.delete(`/media/${mediaId}/tags/${encodeURIComponent(tagName)}`)
            setDetail((d) =>
                d ? { ...d, tags: d.tags.filter((t) => t.name !== tagName) } : d,
            )
        } catch { /* */ }
    }

    // New: Controlled inputs for edit form
    const edit = (key: string, val: unknown) => setEditForm(prev => ({ ...prev, [key]: val }))

    return (
        /* Backdrop */
        <div
            className={`fixed inset-0 z-[10003] flex items-center justify-center p-4 transition-all duration-300
                ${open ? "opacity-100" : "opacity-0 pointer-events-none"}`}
            style={{ backgroundColor: "rgba(0,0,0,0.55)" }}
            onClick={onClose}
        >
            {/* Dialog card */}
            <div
                className={`w-full max-w-[420px] max-h-[80vh] rounded-2xl overflow-hidden transition-all duration-300 flex flex-col
                    ${open ? "scale-100 translate-y-0" : "scale-95 translate-y-4"}`}
                style={{
                    background: "rgba(30, 30, 32, 0.96)",
                    backdropFilter: "blur(40px)",
                    WebkitBackdropFilter: "blur(40px)",
                    boxShadow: "0 25px 60px -12px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06)",
                }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 pt-4 pb-2 shrink-0">
                    <span className="text-white/35 text-[11px] uppercase tracking-wider font-semibold">
                        {isEditing ? "Edit Metadata" : "Details"}
                    </span>
                    <div className="flex items-center gap-1">
                        {isEditing ? (
                            <>
                                <button
                                    onClick={cancelEdit}
                                    disabled={saving}
                                    className="p-1.5 rounded-full text-white/30 hover:text-white/70 hover:bg-white/10 transition-colors"
                                    title="Cancel"
                                >
                                    <X className="h-4 w-4" />
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={saving}
                                    className="p-1.5 rounded-full text-green-400/70 hover:text-green-400 hover:bg-white/10 transition-colors"
                                    title="Save"
                                >
                                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                                </button>
                            </>
                        ) : (
                            <>
                                <button
                                    onClick={() => { setIsEditing(true); setEditForm(JSON.parse(JSON.stringify(detail?.metadata || {}))) }}
                                    className="p-1.5 rounded-full text-white/30 hover:text-white/70 hover:bg-white/10 transition-colors"
                                    title="Edit"
                                >
                                    <Pencil className="h-3.5 w-3.5" />
                                </button>
                                <button
                                    onClick={onClose}
                                    className="p-1.5 rounded-full text-white/30 hover:text-white/70 hover:bg-white/10 transition-colors"
                                    title="Close"
                                >
                                    <X className="h-4 w-4" />
                                </button>
                            </>
                        )}
                    </div>
                </div>

                {loading || !detail ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="h-5 w-5 animate-spin text-white/20" />
                    </div>
                ) : (
                    <div className="overflow-y-auto overscroll-contain px-5 pb-6 flex-1">
                        {/* Filename + meta chips */}
                        <h3 className="text-white font-semibold text-[15px] truncate leading-tight mt-1 select-text">
                            {detail.filename}
                        </h3>
                        <div className="flex items-center gap-2 mt-1.5 flex-wrap text-white/35 text-xs select-text">
                            <span className="uppercase text-[10px] font-bold tracking-wider text-white/50 bg-white/[0.08] px-1.5 py-0.5 rounded">
                                {detail.extension.replace(".", "")}
                            </span>
                            <span>{(detail.file_size / 1024 / 1024).toFixed(1)} MB</span>
                            <span>{new Date(detail.scanned_at || "").toLocaleDateString()}</span>
                        </div>

                        {/* Rating */}
                        <div className="mt-3 mb-4">
                            <StarRating value={detail.rating} onChange={handleRating} interactive size={22} />
                        </div>

                        <div className="h-px bg-white/[0.06]" />

                        {/* Content Area: View vs Edit */}
                        {isEditing ? (
                            <div className="py-4 space-y-4">
                                {/* Date Taken */}
                                <div className="space-y-1">
                                    <label className="text-[10px] uppercase tracking-wider text-white/30 font-semibold block">Date Taken</label>
                                    <input
                                        type="datetime-local"
                                        className="w-full bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                        value={editForm.date_taken ? new Date(editForm.date_taken).toISOString().slice(0, 16) : ""}
                                        onChange={(e) => edit("date_taken", e.target.value ? new Date(e.target.value).toISOString() : null)}
                                    />
                                </div>

                                {/* Location Group */}
                                <div className="space-y-3 pt-1">
                                    <div className="flex gap-2">
                                        <div className="flex-1 space-y-1">
                                            <label className="text-[10px] uppercase tracking-wider text-white/30 font-semibold block">Latitude</label>
                                            <input
                                                type="number"
                                                step="any"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                                value={editForm.gps_lat ?? ""}
                                                onChange={(e) => edit("gps_lat", e.target.value ? parseFloat(e.target.value) : null)}
                                                placeholder="0.0000"
                                            />
                                        </div>
                                        <div className="flex-1 space-y-1">
                                            <label className="text-[10px] uppercase tracking-wider text-white/30 font-semibold block">Longitude</label>
                                            <input
                                                type="number"
                                                step="any"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                                value={editForm.gps_lon ?? ""}
                                                onChange={(e) => edit("gps_lon", e.target.value ? parseFloat(e.target.value) : null)}
                                                placeholder="0.0000"
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <label className="text-[10px] uppercase tracking-wider text-white/30 font-semibold block">Location Label</label>
                                        <input
                                            type="text"
                                            className="w-full bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                            value={editForm.location_label || ""}
                                            onChange={(e) => edit("location_label", e.target.value)}
                                            placeholder="Place name (e.g. Times Square)"
                                        />
                                    </div>
                                    <div className="flex gap-2">
                                        <div className="flex-1 space-y-1">
                                            <input
                                                type="text"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                                value={editForm.location_city || ""}
                                                onChange={(e) => edit("location_city", e.target.value)}
                                                placeholder="City"
                                            />
                                        </div>
                                        <div className="flex-1 space-y-1">
                                            <input
                                                type="text"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                                value={editForm.location_country || ""}
                                                onChange={(e) => edit("location_country", e.target.value)}
                                                placeholder="Country"
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Camera Group */}
                                <div className="space-y-3 pt-1">
                                    <label className="text-[10px] uppercase tracking-wider text-white/30 font-semibold block -mb-2">Device Info</label>
                                    <div className="flex gap-2">
                                        <input
                                            type="text"
                                            className="flex-1 min-w-0 bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                            value={editForm.camera_make || ""}
                                            onChange={(e) => edit("camera_make", e.target.value)}
                                            placeholder="Make"
                                        />
                                        <input
                                            type="text"
                                            className="flex-[2] min-w-0 bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                            value={editForm.camera_model || ""}
                                            onChange={(e) => edit("camera_model", e.target.value)}
                                            placeholder="Model"
                                        />
                                    </div>
                                    <input
                                        type="text"
                                        className="w-full bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                        value={editForm.lens_model || ""}
                                        onChange={(e) => edit("lens_model", e.target.value)}
                                        placeholder="Lens Model"
                                    />
                                    <div className="grid grid-cols-2 gap-2">
                                        <input
                                            type="number"
                                            className="bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                            value={editForm.focal_length || ""}
                                            onChange={(e) => edit("focal_length", parseFloat(e.target.value))}
                                            placeholder="Focal Length (mm)"
                                        />
                                        <input
                                            type="number"
                                            step="any"
                                            className="bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                            value={editForm.aperture || ""}
                                            onChange={(e) => edit("aperture", parseFloat(e.target.value))}
                                            placeholder="Aperture (f/)"
                                        />
                                        <input
                                            type="number"
                                            className="bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                            value={editForm.iso || ""}
                                            onChange={(e) => edit("iso", parseInt(e.target.value))}
                                            placeholder="ISO"
                                        />
                                        <input
                                            type="text"
                                            className="bg-white/[0.04] border border-white/[0.08] rounded text-white text-xs px-2 py-1.5 focus:outline-none focus:border-white/20"
                                            value={editForm.shutter_speed || ""}
                                            onChange={(e) => edit("shutter_speed", e.target.value)}
                                            placeholder="Shutter (1/100)"
                                        />
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="py-4 space-y-4">
                                {/* Date */}
                                {md?.date_taken && (
                                    <div className="flex gap-3">
                                        <Calendar className="h-[15px] w-[15px] text-white/25 mt-[3px] shrink-0" />
                                        <div>
                                            <div className="text-white/80 text-[13px] font-medium select-text">
                                                {new Date(md.date_taken).toLocaleDateString(undefined, {
                                                    weekday: "short", year: "numeric", month: "long", day: "numeric",
                                                })}
                                            </div>
                                            <div className="text-white/30 text-xs mt-0.5 select-text">
                                                {new Date(md.date_taken).toLocaleTimeString(undefined, {
                                                    hour: "2-digit", minute: "2-digit",
                                                })}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Camera */}
                                {(md?.camera_model || md?.lens_model) && (
                                    <div className="flex gap-3">
                                        <Camera className="h-[15px] w-[15px] text-white/25 mt-[3px] shrink-0" />
                                        <div className="min-w-0">
                                            {md.camera_make && (
                                                <div className="text-white/30 text-[10px] uppercase tracking-wider">
                                                    {md.camera_make}
                                                </div>
                                            )}
                                            {md.camera_model && (
                                                <div className="text-white/80 text-[13px] font-medium">
                                                    {md.camera_model}
                                                </div>
                                            )}
                                            {md.lens_model && (
                                                <div className="text-white/40 text-xs mt-0.5">{md.lens_model}</div>
                                            )}
                                            <div className="flex flex-wrap gap-1.5 mt-2">
                                                {md.focal_length && <ExifChip>{md.focal_length}mm</ExifChip>}
                                                {md.aperture && <ExifChip>ƒ/{md.aperture}</ExifChip>}
                                                {md.iso && <ExifChip>ISO {md.iso}</ExifChip>}
                                                {md.shutter_speed && <ExifChip>{md.shutter_speed}s</ExifChip>}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* GPS */}
                                {(md?.gps_lat != null && md?.gps_lon != null) && (
                                    <div className="flex gap-4 items-start">
                                        <div className="mt-1">
                                            <MapPin className="h-4 w-4 text-primary/70 shrink-0" />
                                        </div>
                                        <div className="flex flex-col gap-0.5 min-w-0">
                                            {/* Main Label: specific place or city */}
                                            <div
                                                title="Filter by this location"
                                                className="text-white/90 text-[13px] font-medium leading-tight cursor-pointer hover:text-primary transition-colors hover:underline decoration-white/20 underline-offset-4"
                                                onClick={() => {
                                                    if (md.gps_lat == null || md.gps_lon == null) return;
                                                    setFilters({ lat: md.gps_lat, lon: md.gps_lon, radius: 5 });
                                                    navigate("/");
                                                    onClose();
                                                    onNavigate();
                                                }}
                                            >
                                                {placeName || md.location_city || "Unknown Location"}
                                            </div>

                                            {/* City / Country: if not redundant with label */}
                                            {(md.location_city || md.location_country) && (
                                                <div className="text-white/50 text-[11px] font-medium tracking-wide">
                                                    {[
                                                        (md.location_city !== placeName ? md.location_city : null),
                                                        (md.location_country !== placeName ? md.location_country : null)
                                                    ].filter(Boolean).join(", ")}
                                                </div>
                                            )}

                                            {/* Coordinates - Open in Amap (Gaode) */}
                                            <a
                                                href={`https://uri.amap.com/marker?position=${md.gps_lon},${md.gps_lat}&name=${encodeURIComponent(md.location_label || "Location")}&coordinate=wgs84`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-[10px] font-mono text-white/30 bg-white/[0.04] px-1.5 py-0.5 rounded border border-white/[0.04] hover:bg-white/10 hover:text-white/60 transition-colors w-fit block mt-1.5"
                                                title="Open in Amap"
                                            >
                                                {md.gps_lat.toFixed(5)}, {md.gps_lon.toFixed(5)}
                                            </a>
                                        </div>
                                    </div>
                                )}

                                {/* File path */}
                                <div className="flex gap-3">
                                    <FileText className="h-[15px] w-[15px] text-white/25 mt-[3px] shrink-0" />
                                    <div className="text-white/25 text-[11px] font-mono break-all select-all leading-relaxed bg-white/[0.03] px-2 py-1.5 rounded-lg min-w-0 flex-1">
                                        {detail.path}
                                    </div>
                                </div>
                            </div> /* End View Mode py-4 */
                        )}

                        <div className="h-px bg-white/[0.06] mb-4" />

                        {/* Tags (always visible) */}
                        <div className="flex gap-3 pb-4">
                            <Tag className="h-[15px] w-[15px] text-white/25 mt-[3px] shrink-0" />
                            <div className="flex-1 min-w-0">
                                <div className="flex flex-wrap gap-1.5">
                                    {detail.tags.map((t) => (
                                        <span
                                            key={t.name}
                                            className="inline-flex items-center gap-1 pl-2.5 pr-1.5 py-[5px] bg-white/[0.07] text-white/65 rounded-full text-xs font-medium"
                                        >
                                            {t.name}
                                            <button
                                                onClick={() => handleRemoveTag(t.name)}
                                                className="p-0.5 rounded-full hover:bg-white/15 text-white/25 hover:text-white/60 transition-colors"
                                            >
                                                <X className="h-2.5 w-2.5" />
                                            </button>
                                        </span>
                                    ))}
                                    <form
                                        onSubmit={(e) => { e.preventDefault(); handleAddTag() }}
                                        className="inline-flex"
                                    >
                                        <div className="flex items-center border border-dashed border-white/[0.1] rounded-full overflow-hidden hover:border-white/20 focus-within:border-white/25 transition-colors">
                                            <Plus className="h-3 w-3 text-white/20 ml-2 shrink-0" />
                                            <input
                                                type="text"
                                                value={tagInput}
                                                onChange={(e) => setTagInput(e.target.value)}
                                                placeholder="Add…"
                                                className="bg-transparent text-white text-xs pl-1 pr-2.5 py-[5px] w-14 focus:w-24 focus:outline-none transition-all placeholder:text-white/15"
                                            />
                                        </div>
                                    </form>
                                </div>
                                {detail.tags.length === 0 && !tagInput && (
                                    <div className="text-white/15 text-[11px] mt-1 italic">No tags</div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
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
    const [initialEditMode, setInitialEditMode] = useState(false)
    const [currentIndex, setCurrentIndex] = useState(startIndex)
    const [fadeKey, setFadeKey] = useState(currentIndex)
    const [fadeIn, setFadeIn] = useState(true)

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
                    <button type="button" onClick={() => { }} className={actionBtnClass()} aria-label="Delete">
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
