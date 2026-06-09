import { useState } from "react"
import { mediaRepo } from "@/api/media"
import type { MediaDetail } from "@/api/types"

export interface UseMediaTagMutationsOpts {
    mediaId: number
    detail: MediaDetail | null
    setDetail: React.Dispatch<React.SetStateAction<MediaDetail | null>>
    onMutated?: () => void
    notify: (message: string) => void
}

export interface MediaTagMutations {
    addInput: string
    setAddInput: (value: string) => void
    submitting: boolean
    removingTag: string | null
    addTag: () => Promise<void>
    removeTag: (name: string) => Promise<void>
}

export function useMediaTagMutations(opts: UseMediaTagMutationsOpts): MediaTagMutations {
    const [addInput, setAddInput] = useState("")
    const [submitting, setSubmitting] = useState(false)
    const [removingTag, setRemovingTag] = useState<string | null>(null)

    const addTag = async () => {
        const name = addInput.trim()
        if (!name || !opts.detail || submitting) return
        const normalized = name.toLocaleLowerCase()
        if (opts.detail.tags.some((t) => t.name.toLocaleLowerCase() === normalized)) {
            setAddInput("")
            return
        }
        setSubmitting(true)
        try {
            await mediaRepo.addTags(opts.mediaId, [name])
            opts.setDetail((d) =>
                d ? { ...d, tags: [...d.tags, { name, source: "manual", confidence: null }] } : d,
            )
            setAddInput("")
            opts.onMutated?.()
        } catch {
            opts.notify("Failed to add tag")
        } finally {
            setSubmitting(false)
        }
    }

    const removeTag = async (name: string) => {
        if (!opts.detail || removingTag) return
        setRemovingTag(name)
        try {
            await mediaRepo.removeTag(opts.mediaId, name)
            opts.setDetail((d) =>
                d ? { ...d, tags: d.tags.filter((t) => t.name !== name) } : d,
            )
            opts.onMutated?.()
        } catch {
            opts.notify("Failed to remove tag")
        } finally {
            setRemovingTag(null)
        }
    }

    return { addInput, setAddInput, submitting, removingTag, addTag, removeTag }
}
