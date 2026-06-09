import { Star, Tag } from "lucide-react"
import { describe, expect, it } from "vitest"
import { registerIcon, resolveIcon } from "./icons"

describe("icon registry", () => {
    it("resolves seeded names", () => {
        expect(resolveIcon("tag")).toBe(Tag)
        expect(resolveIcon("star")).toBe(Star)
    })

    it("falls back to a default for unknown / missing names", () => {
        const fallback = resolveIcon("definitely-not-a-real-icon")
        expect(fallback).toBeDefined()
        expect(resolveIcon(undefined)).toBe(fallback)
    })

    it("supports registering new icons at runtime", () => {
        const Custom = (() => null) as unknown as typeof Tag
        registerIcon("test:custom", Custom)
        expect(resolveIcon("test:custom")).toBe(Custom)
    })
})
