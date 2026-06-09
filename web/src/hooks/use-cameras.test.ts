import { act, renderHook } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { useCameras } from "./use-cameras"

vi.mock("@/api/catalog", () => ({
    catalogRepo: {
        listCameras: vi.fn(async () => [
            { make: "Sony", model: "A7R V", count: 12 },
        ]),
        listSmartAlbums: vi.fn(),
    },
}))

describe("useCameras", () => {
    it("populates state after fetch resolves", async () => {
        const { result } = renderHook(() => useCameras())
        expect(result.current).toEqual([])
        await act(async () => {
            await Promise.resolve()
        })
        expect(result.current.length).toBeGreaterThan(0)
        expect(result.current[0].make).toBe("Sony")
    })
})
