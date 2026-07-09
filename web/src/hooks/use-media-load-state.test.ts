import { act, renderHook } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { useMediaLoadState } from "./use-media-load-state"

describe("useMediaLoadState", () => {
    it("starts with empty sets and no error", () => {
        const { result } = renderHook(() => useMediaLoadState())
        expect(result.current.loadedMediaIds.size).toBe(0)
        expect(result.current.originalLoadedIds.size).toBe(0)
        expect(result.current.originalFailedIds.size).toBe(0)
        expect(result.current.mediaError).toBeNull()
        expect(result.current.activeMediaIdRef.current).toBeNull()
    })

    it("setActiveMediaId writes through the ref synchronously", () => {
        const { result } = renderHook(() => useMediaLoadState())
        act(() => result.current.setActiveMediaId(42))
        expect(result.current.activeMediaIdRef.current).toBe(42)
    })

    it("markOriginalLoaded inserts into originalLoadedIds", () => {
        const { result } = renderHook(() => useMediaLoadState())
        act(() => result.current.markOriginalLoaded(7))
        expect(result.current.originalLoadedIds.has(7)).toBe(true)
    })

    it("markOriginalUnavailable inserts into originalFailedIds", () => {
        const { result } = renderHook(() => useMediaLoadState())
        act(() => result.current.markOriginalUnavailable(9))
        expect(result.current.originalFailedIds.has(9)).toBe(true)
    })

    it("markMediaError only records when id matches activeMediaIdRef", () => {
        const { result } = renderHook(() => useMediaLoadState())
        act(() => result.current.setActiveMediaId(1))
        act(() => result.current.markMediaError(2, "stale"))
        expect(result.current.mediaError).toBeNull()

        act(() => result.current.markMediaError(1, "actual"))
        expect(result.current.mediaError).toEqual({ id: 1, message: "actual" })
    })

    it("clearForReset wipes mediaError", () => {
        const { result } = renderHook(() => useMediaLoadState())
        act(() => result.current.setActiveMediaId(1))
        act(() => result.current.markMediaError(1, "oh no"))
        expect(result.current.mediaError).not.toBeNull()
        act(() => result.current.clearForReset())
        expect(result.current.mediaError).toBeNull()
    })

    it("markMediaLoaded inserts immediately", () => {
        const { result } = renderHook(() => useMediaLoadState())
        act(() => result.current.markMediaLoaded(3))
        expect(result.current.loadedMediaIds.has(3)).toBe(true)
    })
})
