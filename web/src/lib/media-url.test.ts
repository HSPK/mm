import { describe, expect, it } from "vitest"
import { createMediaUrlBuilder } from "./media-url"

describe("createMediaUrlBuilder", () => {
    const u = createMediaUrlBuilder("/api")

    it("builds file urls", () => {
        expect(u.file(42)).toBe("/api/media/42/file")
    })

    it("builds preview urls", () => {
        expect(u.preview(7)).toBe("/api/media/7/preview")
    })

    it("builds thumbnail urls with optional size", () => {
        expect(u.thumbnail(1)).toBe("/api/media/1/thumbnail")
        expect(u.thumbnail(1, "md")).toBe("/api/media/1/thumbnail?size=md")
    })

    it("image() points to the cached preview endpoint", () => {
        expect(u.image(9)).toBe(u.preview(9))
    })

    it("respects a custom base url", () => {
        const v = createMediaUrlBuilder("https://x.test/v1")
        expect(v.file(1)).toBe("https://x.test/v1/media/1/file")
    })
})
