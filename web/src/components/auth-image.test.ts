import { describe, expect, it } from "vitest"
import { config } from "@/lib/config"
import { resolveAuthImageSrc } from "@/lib/auth-image-url"

describe("resolveAuthImageSrc", () => {
    it("prefixes API-relative media paths once", () => {
        expect(resolveAuthImageSrc("/media/1/thumbnail")).toBe("/api/media/1/thumbnail")
        expect(resolveAuthImageSrc("/api/organizer/artwork/thumb/item/1"))
            .toBe("/api/organizer/artwork/thumb/item/1")
    })

    it("uses the configured API origin for cross-origin API paths", () => {
        const original = config.apiBaseUrl
        config.apiBaseUrl = "https://media.example.test/api"
        try {
            expect(resolveAuthImageSrc("/api/media/1/thumbnail"))
                .toBe("https://media.example.test/api/media/1/thumbnail")
        } finally {
            config.apiBaseUrl = original
        }
    })
})
