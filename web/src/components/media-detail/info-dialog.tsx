import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"

import { api } from "@/api/client"
import type { Media, MediaDetail as MediaDetailType, MediaMetadata } from "@/api/types"
import {
    X,
    Calendar,
    Camera,
    MapPin,
    Tag,
    FileText,
    Loader2,
    Pencil,
    Plus,
    Check,
    AlertTriangle,
} from "lucide-react"
import { StarRating } from "@/components/ui/star-rating"
import { useMediaStore } from "@/stores/media"
import { trapFocus } from "@/lib/focus"

// ─── EXIF Chip ─────────────────────────────────────────────

function ExifChip({ children }: { children: React.ReactNode }) {
    return (
        <span className="text-[11px] font-mono text-white/55 bg-white/[0.06] px-2 py-[3px] rounded-md border border-white/[0.04]">
            {children}
        </span>
    )
}

function toMediaPatch(detail: MediaDetailType): Partial<Media> {
    const md = detail.metadata
    return {
        rating: detail.rating,
        width: md?.width ?? undefined,
        height: md?.height ?? undefined,
        date_taken: md?.date_taken ?? null,
        camera_model: md?.camera_model ?? null,
        duration: md?.duration ?? null,
        gps_lat: md?.gps_lat ?? null,
        gps_lon: md?.gps_lon ?? null,
        location_label: md?.location_label ?? null,
        location_city: md?.location_city ?? null,
        location_country: md?.location_country ?? null,
    }
}

function formatScannedDate(value: string | null) {
    if (!value) return null
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return null
    return date.toLocaleDateString()
}

function serializeMetadata(value: Partial<MediaMetadata> | null | undefined) {
    return JSON.stringify(value ?? {})
}

function toDateTimeLocalValue(value: unknown) {
    return value ? String(value).replace(/Z$/, "").slice(0, 16) : ""
}

// ─── Info Dialog (centered modal) ──────────────────────────

export function InfoDialog({
    mediaId,
    open,
    initialEditMode = false,
    externalCloseRequested = false,
    onClose,
    onNavigate,
    onDirtyChange,
    onKeepEditing,
    onDiscardClose,
}: {
    mediaId: number
    open: boolean
    initialEditMode?: boolean
    externalCloseRequested?: boolean
    onClose: () => void
    onNavigate: () => void | Promise<void>
    onDirtyChange?: (dirty: boolean) => void
    onKeepEditing?: () => void
    onDiscardClose?: () => void
}) {
    const navigate = useNavigate()
    const setFilters = useMediaStore((s) => s.setFilters)
    const updateItem = useMediaStore((s) => s.updateItem)
    const filters = useMediaStore((s) => s.filters)
    const fetchMedia = useMediaStore((s) => s.fetchMedia)
    const [detail, setDetail] = useState<MediaDetailType | null>(null)
    const [loading, setLoading] = useState(false)
    const [loadError, setLoadError] = useState<string | null>(null)
    const [isEditing, setIsEditing] = useState(false)
    const [editForm, setEditForm] = useState<Partial<NonNullable<MediaDetailType["metadata"]>>>({})
    const [saving, setSaving] = useState(false)
    const [tagInput, setTagInput] = useState("")
    const [tagSubmitting, setTagSubmitting] = useState(false)
    const [removingTag, setRemovingTag] = useState<string | null>(null)
    const [notice, setNotice] = useState<string | null>(null)
    const [retryTick, setRetryTick] = useState(0)
    const [confirmCloseOpen, setConfirmCloseOpen] = useState(false)
    const dialogRef = useRef<HTMLDivElement>(null)
    const closeConfirmRef = useRef<HTMLDivElement>(null)
    const keepEditingButtonRef = useRef<HTMLButtonElement>(null)
    const previousFocusRef = useRef<HTMLElement | null>(null)
    const ratingRequestSeqRef = useRef(0)

    useEffect(() => { setIsEditing(initialEditMode) }, [initialEditMode, open])

    useEffect(() => {
        if (!notice) return
        const t = window.setTimeout(() => setNotice(null), 2600)
        return () => window.clearTimeout(t)
    }, [notice])

    useEffect(() => {
        if (!open) return
        previousFocusRef.current = document.activeElement instanceof HTMLElement
            ? document.activeElement
            : null
        const focusFrame = window.requestAnimationFrame(() => {
            const first = dialogRef.current?.querySelector<HTMLElement>(
                'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
            )
            const target = first ?? dialogRef.current
            target?.focus()
        })
        return () => {
            window.cancelAnimationFrame(focusFrame)
            previousFocusRef.current?.focus()
            previousFocusRef.current = null
        }
    }, [open])

    const md = detail?.metadata ?? null
    const placeName = md?.location_label || md?.location_city || null
    const scannedDate = detail ? formatScannedDate(detail.scanned_at) : null
    const hasUnsavedChanges = useMemo(() => (
        Boolean(isEditing && detail && serializeMetadata(editForm) !== serializeMetadata(detail.metadata))
    ), [detail, editForm, isEditing])
    const showCloseConfirm = confirmCloseOpen || (externalCloseRequested && hasUnsavedChanges)
    const visible = open || showCloseConfirm

    const requestClose = useCallback(() => {
        if (saving) return
        if (hasUnsavedChanges) {
            setConfirmCloseOpen(true)
            return
        }
        onClose()
    }, [hasUnsavedChanges, onClose, saving])

    const discardChangesAndClose = useCallback(() => {
        setConfirmCloseOpen(false)
        setIsEditing(false)
        setEditForm(detail?.metadata || {})
        onDirtyChange?.(false)
        if (externalCloseRequested) onDiscardClose?.()
        else onClose()
    }, [detail, externalCloseRequested, onClose, onDirtyChange, onDiscardClose])

    useEffect(() => {
        onDirtyChange?.(hasUnsavedChanges)
    }, [hasUnsavedChanges, onDirtyChange])

    useEffect(() => {
        if (!showCloseConfirm) return
        const frame = window.requestAnimationFrame(() => {
            keepEditingButtonRef.current?.focus()
        })
        return () => window.cancelAnimationFrame(frame)
    }, [showCloseConfirm])

    useEffect(() => {
        if (!open) return
        const onKey = (e: KeyboardEvent) => {
            if (showCloseConfirm) {
                if (e.key === "Escape") {
                    setConfirmCloseOpen(false)
                    onKeepEditing?.()
                    return
                }
                if (e.key === "Tab") {
                    trapFocus(e, closeConfirmRef.current)
                }
                return
            }
            if (e.key === "Escape" && !saving) {
                if (confirmCloseOpen) setConfirmCloseOpen(false)
                else requestClose()
                return
            }
            if (e.key !== "Tab") return
            trapFocus(e, dialogRef.current)
        }
        window.addEventListener("keydown", onKey)
        return () => window.removeEventListener("keydown", onKey)
    }, [confirmCloseOpen, onKeepEditing, open, requestClose, saving, showCloseConfirm])

    useEffect(() => {
        if (!open || !mediaId) return
        let alive = true
        setLoading(true)
        setLoadError(null)
        setConfirmCloseOpen(false)
        setDetail(null)
        api.get<MediaDetailType>(`/media/${mediaId}`)
            .then((r) => {
                if (alive) {
                    setDetail(r.data)
                    setEditForm(r.data.metadata || {})
                }
            })
            .catch(() => {
                if (alive) {
                    setDetail(null)
                    setEditForm({})
                    setLoadError("Could not load details")
                }
            })
            .finally(() => { if (alive) setLoading(false) })
        return () => { alive = false }
    }, [mediaId, open, retryTick])

    const applyLibraryFilter = useCallback(async (updates: Parameters<typeof setFilters>[0]) => {
        if (hasUnsavedChanges) {
            setConfirmCloseOpen(true)
            return
        }
        onClose()
        await onNavigate()
        setFilters(updates, { replace: true })
        navigate("/", { replace: true })
    }, [hasUnsavedChanges, navigate, onClose, onNavigate, setFilters])

    const handleSave = async () => {
        if (!detail) return
        setSaving(true)
        setNotice(null)
        try {
            const payload = { ...editForm }
            const originalDate = detail.metadata?.date_taken ?? null
            if (toDateTimeLocalValue(payload.date_taken) === toDateTimeLocalValue(originalDate)) {
                payload.date_taken = originalDate
            } else if (payload.date_taken) {
                payload.date_taken = toDateTimeLocalValue(payload.date_taken)
            }

            const res = await api.patch<MediaDetailType>(`/media/${mediaId}/metadata`, payload)
            setDetail(res.data)
            setEditForm(res.data.metadata || {})
            updateItem(mediaId, toMediaPatch(res.data))
            setIsEditing(false)
        } catch {
            setNotice("Failed to save metadata")
        } finally {
            setSaving(false)
        }
    }

    const cancelEdit = () => {
        setConfirmCloseOpen(false)
        setIsEditing(false)
        setEditForm(detail?.metadata || {})
    }

    const handleRating = async (rating: number) => {
        if (!detail) return
        const requestSeq = ++ratingRequestSeqRef.current
        setNotice(null)
        try {
            const res = await api.put<{ rating: number }>(`/media/${mediaId}/rating`, { rating })
            if (requestSeq !== ratingRequestSeqRef.current) return
            const nextRating = res.data.rating
            setDetail((d) => (d ? { ...d, rating: nextRating } : d))
            updateItem(mediaId, { rating: nextRating })
        } catch {
            if (requestSeq !== ratingRequestSeqRef.current) return
            setNotice("Failed to update rating")
        }
    }

    const handleAddTag = async () => {
        const name = tagInput.trim()
        if (!name || !detail || tagSubmitting) return
        const normalized = name.toLocaleLowerCase()
        if (detail.tags.some((t) => t.name.toLocaleLowerCase() === normalized)) {
            setTagInput("")
            return
        }
        setTagSubmitting(true)
        setNotice(null)
        try {
            await api.post(`/media/${mediaId}/tags`, { tags: [name] })
            setDetail((d) =>
                d ? { ...d, tags: [...d.tags, { name, source: "manual", confidence: null }] } : d,
            )
            setTagInput("")
            if (filters.tag || filters.search) void fetchMedia(true)
        } catch {
            setNotice("Failed to add tag")
        } finally {
            setTagSubmitting(false)
        }
    }

    const handleRemoveTag = async (tagName: string) => {
        if (!detail || removingTag) return
        setRemovingTag(tagName)
        setNotice(null)
        try {
            await api.delete(`/media/${mediaId}/tags/${encodeURIComponent(tagName)}`)
            setDetail((d) =>
                d ? { ...d, tags: d.tags.filter((t) => t.name !== tagName) } : d,
            )
            if (filters.tag || filters.search) void fetchMedia(true)
        } catch {
            setNotice("Failed to remove tag")
        } finally {
            setRemovingTag(null)
        }
    }

    const edit = (key: string, val: unknown) => setEditForm(prev => ({ ...prev, [key]: val }))

    if (!visible) return null

    return (
        /* Backdrop */
        <div
            className={`fixed inset-0 z-[10003] flex items-center justify-center p-4 transition-all duration-300
                ${visible ? "opacity-100" : "opacity-0 pointer-events-none"}`}
            style={{ backgroundColor: "rgba(0,0,0,0.55)" }}
            onClick={requestClose}
        >
            {/* Dialog card */}
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-label="Media details"
                tabIndex={-1}
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
                                    disabled={!detail || loading || !!loadError}
                                    className="p-1.5 rounded-full text-white/30 hover:text-white/70 hover:bg-white/10 transition-colors disabled:pointer-events-none disabled:opacity-30"
                                    title="Edit"
                                >
                                    <Pencil className="h-3.5 w-3.5" />
                                </button>
                                <button
                                    onClick={requestClose}
                                    className="p-1.5 rounded-full text-white/30 hover:text-white/70 hover:bg-white/10 transition-colors"
                                    title="Close"
                                >
                                    <X className="h-4 w-4" />
                                </button>
                            </>
                        )}
                    </div>
                </div>

                {notice && (
                    <div className="mx-5 mb-2 rounded-lg border border-red-400/15 bg-red-400/10 px-3 py-2 text-xs font-medium text-red-100/80">
                        {notice}
                    </div>
                )}

                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="h-5 w-5 animate-spin text-white/20" />
                    </div>
                ) : loadError ? (
                    <div className="flex flex-col items-center justify-center px-8 py-16 text-center">
                        <AlertTriangle className="mb-3 h-7 w-7 text-red-300/60" />
                        <div className="text-sm font-medium text-white/75">{loadError}</div>
                        <button
                            type="button"
                            onClick={() => setRetryTick((tick) => tick + 1)}
                            className="mt-4 rounded-full bg-white/10 px-4 py-2 text-xs font-semibold text-white/75 transition hover:bg-white/15 hover:text-white"
                        >
                            Retry
                        </button>
                    </div>
                ) : !detail ? (
                    <div className="flex flex-col items-center justify-center px-8 py-16 text-center">
                        <AlertTriangle className="mb-3 h-7 w-7 text-white/30" />
                        <div className="text-sm font-medium text-white/60">No details available</div>
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
                            {scannedDate && <span>{scannedDate}</span>}
                        </div>

                        {/* Rating */}
                        <div className="mt-3 mb-4">
                            <StarRating value={detail.rating} onChange={handleRating} interactive size={22} />
                        </div>

                        <div className="h-px bg-white/[0.06]" />

                        {/* Content Area: View vs Edit */}
                        {isEditing ? (
                            <div className="py-4 space-y-5">
                                {/* ── Date ── */}
                                <fieldset className="space-y-1.5">
                                    <legend className="text-[10px] uppercase tracking-wider text-white/30 font-semibold">Date Taken</legend>
                                    <input
                                        type="datetime-local"
                                        className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                        value={toDateTimeLocalValue(editForm.date_taken)}
                                        onChange={(e) => edit("date_taken", e.target.value || null)}
                                    />
                                </fieldset>

                                <div className="h-px bg-white/[0.05]" />

                                {/* ── Location ── */}
                                <fieldset className="space-y-2.5">
                                    <legend className="text-[10px] uppercase tracking-wider text-white/30 font-semibold">Location</legend>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="space-y-1">
                                            <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">Latitude</label>
                                            <input
                                                type="number"
                                                step="any"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                                value={editForm.gps_lat ?? ""}
                                                onChange={(e) => edit("gps_lat", e.target.value ? parseFloat(e.target.value) : null)}
                                                placeholder="30.0000"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">Longitude</label>
                                            <input
                                                type="number"
                                                step="any"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                                value={editForm.gps_lon ?? ""}
                                                onChange={(e) => edit("gps_lon", e.target.value ? parseFloat(e.target.value) : null)}
                                                placeholder="120.0000"
                                            />
                                        </div>
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">Place Name</label>
                                        <input
                                            type="text"
                                            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                            value={editForm.location_label || ""}
                                            onChange={(e) => edit("location_label", e.target.value)}
                                            placeholder="e.g. Times Square"
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="space-y-1">
                                            <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">City</label>
                                            <input
                                                type="text"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                                value={editForm.location_city || ""}
                                                onChange={(e) => edit("location_city", e.target.value)}
                                                placeholder="City"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">Country</label>
                                            <input
                                                type="text"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                                value={editForm.location_country || ""}
                                                onChange={(e) => edit("location_country", e.target.value)}
                                                placeholder="Country"
                                            />
                                        </div>
                                    </div>
                                </fieldset>

                                <div className="h-px bg-white/[0.05]" />

                                {/* ── Device ── */}
                                <fieldset className="space-y-2.5">
                                    <legend className="text-[10px] uppercase tracking-wider text-white/30 font-semibold">Device</legend>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="space-y-1">
                                            <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">Make</label>
                                            <input
                                                type="text"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                                value={editForm.camera_make || ""}
                                                onChange={(e) => edit("camera_make", e.target.value)}
                                                placeholder="e.g. Sony"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">Model</label>
                                            <input
                                                type="text"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                                value={editForm.camera_model || ""}
                                                onChange={(e) => edit("camera_model", e.target.value)}
                                                placeholder="e.g. A7R V"
                                            />
                                        </div>
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">Lens</label>
                                        <input
                                            type="text"
                                            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                            value={editForm.lens_model || ""}
                                            onChange={(e) => edit("lens_model", e.target.value)}
                                            placeholder="e.g. FE 24-70mm F2.8 GM II"
                                        />
                                    </div>
                                </fieldset>

                                <div className="h-px bg-white/[0.05]" />

                                {/* ── Exposure ── */}
                                <fieldset className="space-y-2.5">
                                    <legend className="text-[10px] uppercase tracking-wider text-white/30 font-semibold">Exposure</legend>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="space-y-1">
                                            <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">Focal Length</label>
                                            <input
                                                type="number"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                                value={editForm.focal_length ?? ""}
                                                onChange={(e) => edit("focal_length", e.target.value ? parseFloat(e.target.value) : null)}
                                                placeholder="mm"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">Aperture</label>
                                            <input
                                                type="number"
                                                step="any"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                                value={editForm.aperture ?? ""}
                                                onChange={(e) => edit("aperture", e.target.value ? parseFloat(e.target.value) : null)}
                                                placeholder="f/"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">ISO</label>
                                            <input
                                                type="number"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                                value={editForm.iso ?? ""}
                                                onChange={(e) => edit("iso", e.target.value ? parseInt(e.target.value) : null)}
                                                placeholder="e.g. 100"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5">Shutter Speed</label>
                                            <input
                                                type="text"
                                                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
                                                value={editForm.shutter_speed || ""}
                                                onChange={(e) => edit("shutter_speed", e.target.value)}
                                                placeholder="e.g. 1/250"
                                            />
                                        </div>
                                    </div>
                                </fieldset>
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
                                            <button
                                                type="button"
                                                title="Filter by this location"
                                                className="w-fit rounded-sm text-left text-white/90 text-[13px] font-medium leading-tight hover:text-primary focus:outline-none focus:ring-1 focus:ring-primary/50 transition-colors hover:underline decoration-white/20 underline-offset-4"
                                                onClick={() => {
                                                    if (md.gps_lat == null || md.gps_lon == null) return
                                                    applyLibraryFilter({ lat: md.gps_lat, lon: md.gps_lon, radius: 5 })
                                                }}
                                            >
                                                {placeName || md.location_city || "Unknown Location"}
                                            </button>

                                            {(md.location_city || md.location_country) && (
                                                <div className="text-white/50 text-[11px] font-medium tracking-wide">
                                                    {[
                                                        (md.location_city !== placeName ? md.location_city : null),
                                                        (md.location_country !== placeName ? md.location_country : null)
                                                    ].filter(Boolean).join(", ")}
                                                </div>
                                            )}

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
                            </div>
                        )}

                        <div className="h-px bg-white/[0.06] mb-4" />

                        {/* Tags (always visible) */}
                        <div className="pb-4">
                            <div className="flex flex-wrap items-center gap-1.5">
                                <Tag className="h-[13px] w-[13px] text-white/20 shrink-0 mr-0.5" />
                                {detail.tags.map((t) => (
                                    <span
                                        key={t.name}
                                        className="inline-flex items-center gap-1 pl-2.5 pr-1.5 py-[5px] bg-white/[0.07] text-white/65 rounded-full text-xs font-medium group"
                                    >
                                        <button
                                            onClick={() => {
                                                applyLibraryFilter({ tag: t.name })
                                            }}
                                            className="hover:text-white transition-colors cursor-pointer"
                                            title={`Filter by tag: ${t.name}`}
                                        >
                                            {t.name}
                                        </button>
                                        <button
                                            onClick={() => handleRemoveTag(t.name)}
                                            disabled={removingTag != null}
                                            className="p-0.5 rounded-full hover:bg-white/15 text-white/25 hover:text-white/60 transition-colors disabled:pointer-events-none disabled:opacity-40"
                                            title={`Remove tag: ${t.name}`}
                                        >
                                            {removingTag === t.name
                                                ? <Loader2 className="h-2.5 w-2.5 animate-spin" />
                                                : <X className="h-2.5 w-2.5" />}
                                        </button>
                                    </span>
                                ))}
                                <form
                                    onSubmit={(e) => {
                                        e.preventDefault()
                                        handleAddTag()
                                    }}
                                    className="inline-flex"
                                >
                                    <div className="flex items-center border border-dashed border-white/[0.08] rounded-full overflow-hidden hover:border-white/20 focus-within:border-white/25 transition-colors">
                                        {tagSubmitting
                                            ? <Loader2 className="h-3 w-3 text-white/25 ml-2 shrink-0 animate-spin" />
                                            : <Plus className="h-3 w-3 text-white/15 ml-2 shrink-0" />}
                                        <input
                                            type="text"
                                            value={tagInput}
                                            onChange={(e) => setTagInput(e.target.value)}
                                            disabled={tagSubmitting}
                                            placeholder={detail.tags.length === 0 ? "Add tag…" : "Add…"}
                                            className="bg-transparent text-white text-xs pl-1 pr-2.5 py-[5px] w-16 focus:w-24 focus:outline-none transition-all placeholder:text-white/15 disabled:opacity-50"
                                        />
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {showCloseConfirm && (
                <div
                    className="absolute inset-0 z-10 flex items-center justify-center bg-black/55 p-4 backdrop-blur-sm"
                    role="presentation"
                    onClick={(e) => e.stopPropagation()}
                >
                    <div
                        ref={closeConfirmRef}
                        role="dialog"
                        aria-modal="true"
                        aria-label="Discard unsaved changes"
                        tabIndex={-1}
                        className="w-full max-w-[340px] rounded-2xl border border-white/10 bg-neutral-950/95 p-5 text-white shadow-2xl"
                    >
                        <div className="mb-2 text-sm font-semibold">Discard unsaved edits?</div>
                        <p className="mb-5 text-sm leading-relaxed text-white/55">
                            Your metadata changes have not been saved.
                        </p>
                        <div className="flex justify-end gap-2">
                            <button
                                ref={keepEditingButtonRef}
                                type="button"
                                className="rounded-full px-4 py-2 text-sm text-white/70 transition hover:bg-white/10 hover:text-white"
                                onClick={() => {
                                    setConfirmCloseOpen(false)
                                    onKeepEditing?.()
                                }}
                            >
                                Keep editing
                            </button>
                            <button
                                type="button"
                                className="rounded-full bg-red-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-400"
                                onClick={discardChangesAndClose}
                            >
                                Discard
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
