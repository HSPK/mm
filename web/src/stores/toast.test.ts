import { act, renderHook } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { toast, useToastStore } from "@/stores/toast"

beforeEach(() => {
    useToastStore.setState({ toasts: [] })
})

describe("toast store", () => {
    it("push appends a toast and assigns a unique id", () => {
        const id1 = toast.show("hello")
        const id2 = toast.show("world")
        const { toasts } = useToastStore.getState()
        expect(toasts.length).toBe(2)
        expect(id1).not.toBe(id2)
        expect(toasts.map((t) => t.message)).toEqual(["hello", "world"])
    })

    it("variant shortcuts apply correct variant", () => {
        toast.success("yay")
        toast.error("nope")
        const variants = useToastStore.getState().toasts.map((t) => t.variant)
        expect(variants).toEqual(["success", "error"])
    })

    it("dismiss removes a single toast by id", () => {
        const id = toast.show("hello")
        toast.show("world")
        toast.dismiss(id)
        const { toasts } = useToastStore.getState()
        expect(toasts.length).toBe(1)
        expect(toasts[0].message).toBe("world")
    })

    it("auto-dismisses after duration", async () => {
        vi.useFakeTimers()
        toast.show("hi", { duration: 1000 })
        expect(useToastStore.getState().toasts.length).toBe(1)
        await act(async () => {
            vi.advanceTimersByTime(1000)
        })
        expect(useToastStore.getState().toasts.length).toBe(0)
        vi.useRealTimers()
    })

    it("duration=0 keeps the toast sticky", async () => {
        vi.useFakeTimers()
        toast.show("sticky", { duration: 0 })
        await act(async () => {
            vi.advanceTimersByTime(10000)
        })
        expect(useToastStore.getState().toasts.length).toBe(1)
        vi.useRealTimers()
    })

    it("subscriber sees pushed toasts", () => {
        const { result } = renderHook(() => useToastStore((s) => s.toasts))
        expect(result.current).toEqual([])
        act(() => { toast.show("hi") })
        expect(result.current.length).toBe(1)
    })
})
