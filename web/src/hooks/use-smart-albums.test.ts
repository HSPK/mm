import { act, renderHook, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

const listSmartAlbums = vi.fn()

vi.mock("@/api/catalog", () => ({
    catalogRepo: {
        listSmartAlbums: (...args: unknown[]) => listSmartAlbums(...args),
        listCameras: vi.fn(),
    },
}))

describe("useSmartAlbums", () => {
    it("sets data + loading=false on success", async () => {
        listSmartAlbums.mockResolvedValueOnce({
            library: [], tags: [], cameras: [], festivals: [], years: [], places: [],
        })
        const { useSmartAlbums } = await import("./use-smart-albums")
        const { result } = renderHook(() => useSmartAlbums())
        await waitFor(() => expect(result.current.loading).toBe(false))
        expect(result.current.data).not.toBeNull()
        expect(result.current.error).toBeNull()
    })

    it("sets error + null data on failure", async () => {
        listSmartAlbums.mockReset().mockRejectedValueOnce(new Error("nope"))
        const { useSmartAlbums } = await import("./use-smart-albums")
        const { result } = renderHook(() => useSmartAlbums())
        await waitFor(() => expect(result.current.loading).toBe(false))
        expect(result.current.data).toBeNull()
        expect(result.current.error).toBe("Could not load albums")
    })

    it("retry refetches and clears error", async () => {
        listSmartAlbums
            .mockReset()
            .mockRejectedValueOnce(new Error("first"))
            .mockResolvedValueOnce({
                library: [{ key: "lib", title: "All", filters: {} }],
                tags: [], cameras: [], festivals: [], years: [], places: [],
            })
        const { useSmartAlbums } = await import("./use-smart-albums")
        const { result } = renderHook(() => useSmartAlbums())
        await waitFor(() => expect(result.current.error).not.toBeNull())

        act(() => result.current.retry())
        await waitFor(() => expect(result.current.data).not.toBeNull())
        expect(result.current.error).toBeNull()
    })
})
