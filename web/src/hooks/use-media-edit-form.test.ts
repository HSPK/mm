import { act, renderHook } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import type { MediaDetail } from "@/api/types"
import { useMediaEditForm } from "./use-media-edit-form"

function makeDetail(overrides: Partial<MediaDetail> = {}): MediaDetail {
    return {
        id: 1,
        path: "/a/b.jpg",
        filename: "b.jpg",
        extension: ".jpg",
        media_type: "photo",
        file_size: 1000,
        file_hash: "h",
        rating: 0,
        scanned_at: null,
        metadata: {
            date_taken: null,
            camera_make: null,
            camera_model: "Sony",
            lens_model: null,
            focal_length: null,
            aperture: null,
            shutter_speed: null,
            iso: null,
            width: 100,
            height: 100,
            duration: null,
            gps_lat: null,
            gps_lon: null,
            orientation: 1,
        },
        tags: [],
        ...overrides,
    }
}

describe("useMediaEditForm", () => {
    it("seeds the form from detail.metadata", () => {
        const detail = makeDetail()
        const { result } = renderHook(() => useMediaEditForm(detail, false))
        expect(result.current.form.camera_model).toBe("Sony")
    })

    it("isDirty stays false until isEditing is true", () => {
        const detail = makeDetail()
        const { result, rerender } = renderHook(
            ({ editing }: { editing: boolean }) => useMediaEditForm(detail, editing),
            { initialProps: { editing: false } },
        )
        act(() => result.current.setField("camera_model", "Canon"))
        expect(result.current.isDirty).toBe(false)
        rerender({ editing: true })
        expect(result.current.isDirty).toBe(true)
    })

    it("setField updates a single field", () => {
        const detail = makeDetail()
        const { result } = renderHook(() => useMediaEditForm(detail, true))
        act(() => result.current.setField("iso", 400))
        expect(result.current.form.iso).toBe(400)
        expect(result.current.isDirty).toBe(true)
    })

    it("resetToDetail restores the pristine form", () => {
        const detail = makeDetail()
        const { result } = renderHook(() => useMediaEditForm(detail, true))
        act(() => result.current.setField("camera_model", "Canon"))
        expect(result.current.isDirty).toBe(true)
        act(() => result.current.resetToDetail())
        expect(result.current.isDirty).toBe(false)
        expect(result.current.form.camera_model).toBe("Sony")
    })

    it("re-seeds when detail object changes", () => {
        const initial = makeDetail()
        const { result, rerender } = renderHook(
            ({ d }: { d: MediaDetail }) => useMediaEditForm(d, true),
            { initialProps: { d: initial } },
        )
        expect(result.current.form.camera_model).toBe("Sony")
        const updated = makeDetail({
            metadata: { ...initial.metadata!, camera_model: "Fujifilm" },
        })
        rerender({ d: updated })
        expect(result.current.form.camera_model).toBe("Fujifilm")
    })
})
