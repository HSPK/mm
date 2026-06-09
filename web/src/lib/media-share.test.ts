import { beforeEach, describe, expect, it, vi } from "vitest"
import { useToastStore } from "@/stores/toast"
import { openOriginal, shareMedia } from "./media-share"

beforeEach(() => {
    useToastStore.setState({ toasts: [] })
    vi.restoreAllMocks()
})

describe("shareMedia", () => {
    it("uses navigator.share when available", async () => {
        const share = vi.fn().mockResolvedValue(undefined)
        Object.defineProperty(navigator, "share", { configurable: true, value: share })
        await shareMedia({ id: 1, filename: "a.jpg" })
        expect(share).toHaveBeenCalledOnce()
        const arg = share.mock.calls[0][0] as { url: string; title: string }
        expect(arg.title).toBe("a.jpg")
        expect(arg.url).toContain("/media/1/file")
    })

    it("falls back to clipboard when share is unavailable", async () => {
        Object.defineProperty(navigator, "share", { configurable: true, value: undefined })
        const writeText = vi.fn().mockResolvedValue(undefined)
        Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } })
        await shareMedia({ id: 7, filename: "b.jpg" })
        expect(writeText).toHaveBeenCalledOnce()
        expect(writeText.mock.calls[0][0]).toContain("/media/7/file")
        expect(useToastStore.getState().toasts[0]?.message).toBe("Link copied to clipboard")
    })

    it("swallows AbortError silently", async () => {
        const err = Object.assign(new Error("aborted"), { name: "AbortError" })
        const share = vi.fn().mockRejectedValue(err)
        Object.defineProperty(navigator, "share", { configurable: true, value: share })
        await shareMedia({ id: 1, filename: "a.jpg" })
        expect(useToastStore.getState().toasts.length).toBe(0)
    })
})

describe("openOriginal", () => {
    it("opens the file url in a new tab with secure rel", () => {
        const open = vi.spyOn(window, "open").mockImplementation(() => null)
        openOriginal({ id: 5, filename: "x.jpg" })
        expect(open).toHaveBeenCalledOnce()
        const [url, target, features] = open.mock.calls[0]
        expect(url).toContain("/media/5/file")
        expect(target).toBe("_blank")
        expect(features).toContain("noopener")
    })
})
