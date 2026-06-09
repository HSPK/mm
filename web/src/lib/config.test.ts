import { describe, expect, it } from "vitest"
import { clampThumbSize, config } from "./config"

describe("config", () => {
    it("exposes API base url with /api default", () => {
        expect(config.apiBaseUrl).toBeTruthy()
    })

    it("clamps thumb size within [min, max]", () => {
        expect(clampThumbSize(50)).toBe(config.thumbSize.min)
        expect(clampThumbSize(500)).toBe(config.thumbSize.max)
        expect(clampThumbSize(200)).toBe(200)
    })
})
