import { useState } from "react"
import { mediaRepo } from "@/api/media"
import type { Media } from "@/api/types"

export interface UseMediaViewerActionsOpts {
    currentItem: Media | undefined
    currentIndex: number
    items: Media[]
    inTrash: boolean
    onClose: () => void
    onDelete?: (id: number) => void
    onActiveChange?: (id: number) => void
    setActiveMediaId: (id: number) => void
    setDisplayMediaId: (id: number) => void
    notify: (message: string) => void
}

export interface MediaViewerActions {
    downloading: boolean
    deleting: boolean
    confirmDeleteOpen: boolean
    openDeleteConfirm: () => void
    closeDeleteConfirm: () => void
    download: () => Promise<void>
    confirmDelete: () => Promise<void>
}

export function useMediaViewerActions(opts: UseMediaViewerActionsOpts): MediaViewerActions {
    const [downloading, setDownloading] = useState(false)
    const [deleting, setDeleting] = useState(false)
    const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)

    const openDeleteConfirm = () => {
        if (!opts.currentItem || deleting) return
        setConfirmDeleteOpen(true)
    }

    const closeDeleteConfirm = () => {
        if (!deleting) setConfirmDeleteOpen(false)
    }

    const download = async () => {
        if (!opts.currentItem || downloading) return
        setDownloading(true)
        try {
            const blob = await mediaRepo.downloadBlob(opts.currentItem.id)
            const url = URL.createObjectURL(blob)
            const anchor = document.createElement("a")
            anchor.href = url
            anchor.download = opts.currentItem.filename
            document.body.appendChild(anchor)
            anchor.click()
            document.body.removeChild(anchor)
            URL.revokeObjectURL(url)
        } catch {
            opts.notify("Download failed")
        } finally {
            setDownloading(false)
        }
    }

    const confirmDelete = async () => {
        const item = opts.currentItem
        if (!item || deleting) return
        setDeleting(true)
        try {
            const fallback = opts.currentIndex < opts.items.length - 1
                ? opts.items[opts.currentIndex + 1]
                : opts.items[opts.currentIndex - 1]
            await mediaRepo.deleteOne(item.id, opts.inTrash ? { permanent: true } : undefined)
            setConfirmDeleteOpen(false)
            if (!fallback) {
                opts.onDelete?.(item.id)
                opts.onClose()
            } else {
                opts.onActiveChange?.(fallback.id)
                opts.setActiveMediaId(fallback.id)
                if (fallback.media_type === "video") opts.setDisplayMediaId(fallback.id)
                opts.onDelete?.(item.id)
            }
        } catch {
            setConfirmDeleteOpen(false)
            opts.notify("Delete failed")
        } finally {
            setDeleting(false)
        }
    }

    return {
        downloading,
        deleting,
        confirmDeleteOpen,
        openDeleteConfirm,
        closeDeleteConfirm,
        download,
        confirmDelete,
    }
}
