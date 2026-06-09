import { renderHook } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { useIsTouchDevice } from "./use-is-touch-device"

describe("useIsTouchDevice", () => {
    it("returns true when pointer: coarse matches", () => {
        vi.spyOn(window, "matchMedia").mockImplementation((q) => ({
            matches: q === "(pointer: coarse)",
            media: q,
            onchange: null,
            addEventListener: () => { },
            removeEventListener: () => { },
            addListener: () => { },
            removeListener: () => { },
            dispatchEvent: () => false,
        }) as MediaQueryList)
        const { result } = renderHook(() => useIsTouchDevice())
        expect(result.current).toBe(true)
    })

    it("returns false when pointer: fine and no touch", () => {
        vi.spyOn(window, "matchMedia").mockImplementation((q) => ({
            matches: false,
            media: q,
            onchange: null,
            addEventListener: () => { },
            removeEventListener: () => { },
            addListener: () => { },
            removeListener: () => { },
            dispatchEvent: () => false,
        }) as MediaQueryList)
        Object.defineProperty(navigator, "maxTouchPoints", { configurable: true, value: 0 })
        const { result } = renderHook(() => useIsTouchDevice())
        expect(result.current).toBe(false)
    })
})
