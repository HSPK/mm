import { AlertTriangle } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { mediaRepo } from "@/api/media"
import type { Media, MediaDetail as MediaDetailType, MediaMetadata } from "@/api/types"
import { Spinner } from "@/components/ui/spinner"
import { StarRating } from "@/components/ui/star-rating"
import { useMediaDetail } from "@/hooks/use-media-detail"
import { useMediaEditForm } from "@/hooks/use-media-edit-form"
import { useMediaTagMutations } from "@/hooks/use-media-tag-mutations"
import { useRatingMutation } from "@/hooks/use-rating-mutation"
import { trapFocus } from "@/lib/focus"
import { useMediaQueryStore } from "@/stores/media-query"
import { toast } from "@/stores/toast"
import { DiscardChangesDialog } from "./discard-changes-dialog"
import { InfoDialogHeader } from "./info-dialog-header"
import { MetadataEditor } from "./metadata-editor"
import { MetadataView } from "./metadata-view"
import { TagsSection } from "./tags-section"

interface InfoDialogProps {
    mediaId: number
    open: boolean
    initialEditMode?: boolean
    externalCloseRequested?: boolean
    onClose: () => void
    onNavigate: () => void | Promise<void>
    onDirtyChange?: (dirty: boolean) => void
    onKeepEditing?: () => void
    onDiscardClose?: () => void
}

function toDateTimeLocalValue(value: unknown) {
    return value ? String(value).replace(/Z$/, "").slice(0, 16) : ""
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

function formatScannedDate(value: string | null | undefined) {
    if (!value) return null
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return null
    return date.toLocaleDateString()
}

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
}: InfoDialogProps) {
    const navigate = useNavigate()
    const setFilters = useMediaQueryStore((s) => s.setFilters)
    const updateItem = useMediaQueryStore((s) => s.updateItem)
    const filters = useMediaQueryStore((s) => s.filters)
    const fetchMedia = useMediaQueryStore((s) => s.fetchMedia)

    const { detail, loading, loadError, reload, setDetail } = useMediaDetail(mediaId, open)
    const [isEditing, setIsEditing] = useState(initialEditMode)
    const editForm = useMediaEditForm(detail, isEditing)
    const [saving, setSaving] = useState(false)
    const [confirmCloseOpen, setConfirmCloseOpen] = useState(false)

    const dialogRef = useRef<HTMLDivElement>(null)
    const previousFocusRef = useRef<HTMLElement | null>(null)

    const notify = useCallback((message: string) => { toast.error(message) }, [])

    const setRating = useRatingMutation({ mediaId, setDetail, notify })

    const tags = useMediaTagMutations({
        mediaId,
        detail,
        setDetail,
        notify,
        onMutated: () => {
            if (filters.tag || filters.search) void fetchMedia(true)
        },
    })

    useEffect(() => { setIsEditing(initialEditMode) }, [initialEditMode, open])

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

    const showCloseConfirm = confirmCloseOpen || (externalCloseRequested && editForm.isDirty)
    const visible = open || showCloseConfirm

    const requestClose = useCallback(() => {
        if (saving) return
        if (editForm.isDirty) {
            setConfirmCloseOpen(true)
            return
        }
        onClose()
    }, [editForm.isDirty, onClose, saving])

    const discardChangesAndClose = useCallback(() => {
        setConfirmCloseOpen(false)
        setIsEditing(false)
        editForm.resetToDetail()
        onDirtyChange?.(false)
        if (externalCloseRequested) onDiscardClose?.()
        else onClose()
    }, [editForm, externalCloseRequested, onClose, onDirtyChange, onDiscardClose])

    useEffect(() => {
        onDirtyChange?.(editForm.isDirty)
    }, [editForm.isDirty, onDirtyChange])

    useEffect(() => {
        if (!open) return
        const onKey = (e: KeyboardEvent) => {
            if (showCloseConfirm) {
                if (e.key === "Escape") {
                    setConfirmCloseOpen(false)
                    onKeepEditing?.()
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

    const applyLibraryFilter = useCallback(async (updates: Parameters<typeof setFilters>[0]) => {
        if (editForm.isDirty) {
            setConfirmCloseOpen(true)
            return
        }
        onClose()
        await onNavigate()
        setFilters(updates, { replace: true })
        navigate("/", { replace: true })
    }, [editForm.isDirty, navigate, onClose, onNavigate, setFilters])

    const handleSave = async () => {
        if (!detail) return
        setSaving(true)
        try {
            const payload: Partial<MediaMetadata> = { ...editForm.form }
            const originalDate = detail.metadata?.date_taken ?? null
            if (toDateTimeLocalValue(payload.date_taken) === toDateTimeLocalValue(originalDate)) {
                payload.date_taken = originalDate
            } else if (payload.date_taken) {
                payload.date_taken = toDateTimeLocalValue(payload.date_taken)
            }

            const updated = await mediaRepo.updateMetadata(mediaId, payload)
            setDetail(updated)
            updateItem(mediaId, toMediaPatch(updated))
            setIsEditing(false)
        } catch {
            notify("Failed to save metadata")
        } finally {
            setSaving(false)
        }
    }

    const cancelEdit = () => {
        setConfirmCloseOpen(false)
        setIsEditing(false)
        editForm.resetToDetail()
    }

    const enterEdit = () => {
        if (!detail) return
        setIsEditing(true)
        editForm.resetToDetail()
    }

    if (!visible) return null

    return (
        <div
            className={`fixed inset-0 z-[10003] flex items-center justify-center p-4 transition-all duration-300
                ${visible ? "opacity-100" : "opacity-0 pointer-events-none"}`}
            style={{ backgroundColor: "rgba(0,0,0,0.55)" }}
            onClick={requestClose}
        >
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-label="Media details"
                tabIndex={-1}
                className={`w-full max-w-[420px] max-h-[80vh] rounded-3xl overflow-hidden flex flex-col elevation-3 material-thick transition-all duration-300 ${
                    open ? "scale-100 translate-y-0" : "scale-95 translate-y-4"
                }`}
                onClick={(e) => e.stopPropagation()}
            >
                <InfoDialogHeader
                    isEditing={isEditing}
                    saving={saving}
                    canEdit={Boolean(detail) && !loading && !loadError}
                    onEnterEdit={enterEdit}
                    onCancelEdit={cancelEdit}
                    onSave={handleSave}
                    onClose={requestClose}
                />

                {loading
                    ? <LoadingState />
                    : loadError
                        ? <LoadErrorState message={loadError} onRetry={reload} />
                        : !detail
                            ? <EmptyState />
                            : (
                                <div className="overflow-y-auto overscroll-contain px-5 pb-6 flex-1">
                                    <h3 className="text-foreground font-semibold text-[15px] truncate leading-tight mt-1 select-text">
                                        {detail.filename}
                                    </h3>
                                    <div className="flex items-center gap-2 mt-1.5 flex-wrap text-muted-foreground text-xs select-text">
                                        <span className="uppercase text-[10px] font-bold tracking-wider text-foreground/80 bg-secondary/60 px-1.5 py-0.5 rounded">
                                            {detail.extension.replace(".", "")}
                                        </span>
                                        <span>{(detail.file_size / 1024 / 1024).toFixed(1)} MB</span>
                                        {formatScannedDate(detail.scanned_at) && <span>{formatScannedDate(detail.scanned_at)}</span>}
                                    </div>

                                    <div className="mt-3 mb-4">
                                        <StarRating value={detail.rating} onChange={setRating} interactive size={22} />
                                    </div>

                                    <div className="h-px bg-border" />

                                    {isEditing
                                        ? <MetadataEditor form={editForm.form} onChange={editForm.setField} />
                                        : (
                                            <MetadataView
                                                detail={detail}
                                                onApplyLocationFilter={(lat, lon) =>
                                                    applyLibraryFilter({ lat, lon, radius: 5 })
                                                }
                                            />
                                        )
                                    }

                                    <div className="h-px bg-white/[0.06] mb-4" />

                                    <TagsSection
                                        detail={detail}
                                        addInput={tags.addInput}
                                        onAddInputChange={tags.setAddInput}
                                        submitting={tags.submitting}
                                        removingTag={tags.removingTag}
                                        onAddTag={tags.addTag}
                                        onRemoveTag={tags.removeTag}
                                        onClickTag={(name) => applyLibraryFilter({ tag: name })}
                                    />
                                </div>
                            )
                }
            </div>

            <DiscardChangesDialog
                open={showCloseConfirm}
                onKeepEditing={() => {
                    setConfirmCloseOpen(false)
                    onKeepEditing?.()
                }}
                onDiscard={discardChangesAndClose}
            />
        </div>
    )
}

function LoadingState() {
    return (
        <div className="flex items-center justify-center py-20">
            <Spinner size="md" className="text-white/20" />
        </div>
    )
}

function LoadErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
    return (
        <div className="flex flex-col items-center justify-center px-8 py-16 text-center">
            <AlertTriangle className="mb-3 h-7 w-7 text-red-300/60" />
            <div className="text-sm font-medium text-white/75">{message}</div>
            <button
                type="button"
                onClick={onRetry}
                className="mt-4 rounded-full bg-white/10 px-4 py-2 text-xs font-semibold text-white/75 transition hover:bg-white/15 hover:text-white"
            >
                Retry
            </button>
        </div>
    )
}

function EmptyState() {
    return (
        <div className="flex flex-col items-center justify-center px-8 py-16 text-center">
            <AlertTriangle className="mb-3 h-7 w-7 text-white/30" />
            <div className="text-sm font-medium text-white/60">No details available</div>
        </div>
    )
}
