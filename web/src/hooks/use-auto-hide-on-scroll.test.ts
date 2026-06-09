import { act, renderHook } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { useAutoHideOnScroll } from "./use-auto-hide-on-scroll"

function makeScrollEl(): HTMLElement {
    const el = document.createElement("div")
    let value = 0
    Object.defineProperty(el, "scrollTop", {
        configurable: true,
        get: () => value,
        set: (next: number) => { value = next },
    })
    document.body.appendChild(el)
    return el
}

function setScroll(el: HTMLElement, value: number) {
    el.scrollTop = value
    el.dispatchEvent(new Event("scroll"))
}

describe("useAutoHideOnScroll", () => {
    it("starts visible", () => {
        const el = makeScrollEl()
        const { result } = renderHook(() => useAutoHideOnScroll(el, false))
        expect(result.current.visible).toBe(true)
    })

    it("stays visible when pinned even after scroll-down", () => {
        const el = makeScrollEl()
        const { result } = renderHook(() => useAutoHideOnScroll(el, true))
        act(() => {
            setScroll(el, 200)
        })
        expect(result.current.visible).toBe(true)
    })

    it("hides on scroll-down past the threshold", () => {
        const el = makeScrollEl()
        const { result } = renderHook(() => useAutoHideOnScroll(el, false))
        act(() => {
            setScroll(el, 200)
        })
        expect(result.current.visible).toBe(false)
    })

    it("reappears on scroll-up", () => {
        const el = makeScrollEl()
        const { result } = renderHook(() => useAutoHideOnScroll(el, false))
        act(() => {
            setScroll(el, 200)
        })
        act(() => {
            setScroll(el, 150)
        })
        expect(result.current.visible).toBe(true)
    })

    it("does nothing without a container", () => {
        const { result } = renderHook(() => useAutoHideOnScroll(null, false))
        expect(result.current.visible).toBe(true)
    })
})
