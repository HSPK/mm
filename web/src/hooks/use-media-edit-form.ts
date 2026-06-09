import { useEffect, useMemo, useState } from "react"
import type { MediaDetail, MediaMetadata } from "@/api/types"

export type MetadataForm = Partial<NonNullable<MediaDetail["metadata"]>>

function serialize(value: Partial<MediaMetadata> | null | undefined) {
    return JSON.stringify(value ?? {})
}

export interface UseMediaEditFormResult {
    form: MetadataForm
    isDirty: boolean
    setField: (key: string, value: unknown) => void
    resetToDetail: () => void
    serializedForm: string
}

/**
 * Edit-form state for media metadata. Stays in sync with `detail` whenever the
 * detail document is reloaded, and exposes a `isDirty` flag derived from a
 * stable serialization comparison.
 */
export function useMediaEditForm(
    detail: MediaDetail | null,
    isEditing: boolean,
): UseMediaEditFormResult {
    const [form, setForm] = useState<MetadataForm>({})

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- derived state sync; intentional reset when detail reloads
        setForm(detail?.metadata ?? {})
    }, [detail])

    const serializedForm = serialize(form)

    const isDirty = useMemo(
        () => Boolean(isEditing && detail && serializedForm !== serialize(detail.metadata)),
        [detail, isEditing, serializedForm],
    )

    return {
        form,
        isDirty,
        setField: (key, value) => setForm((prev) => ({ ...prev, [key]: value })),
        resetToDetail: () => setForm(detail?.metadata ?? {}),
        serializedForm,
    }
}
