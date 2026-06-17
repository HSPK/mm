import { describe, expect, it } from "vitest"
import {
    clampImagePan,
    clampImageScale,
    distance,
    midpoint,
    wheelDeltaToScale,
    zoomAt,
} from "./image-zoom"

describe("image zoom math", () => {
    it("clamps scale", () => {
        expect(clampImageScale(0.2)).toBe(1)
        expect(clampImageScale(99)).toBe(8)
        expect(clampImageScale(2.5)).toBe(2.5)
    })

    it("maps negative wheel delta to zooming in", () => {
        expect(wheelDeltaToScale(1, -80)).toBeGreaterThan(1)
        expect(wheelDeltaToScale(2, 80)).toBeLessThan(2)
    })

    it("keeps pan within viewport-derived bounds", () => {
        expect(clampImagePan({ scale: 2, x: 999, y: -999 }, { width: 400, height: 200 }))
            .toEqual({ scale: 2, x: 200, y: -100 })
    })

    it("resets pan when zoom returns to 1", () => {
        expect(clampImagePan({ scale: 1, x: 10, y: 20 }, { width: 400, height: 200 }))
            .toEqual({ scale: 1, x: 0, y: 0 })
    })

    it("zooms around the focal point", () => {
        const next = zoomAt({ scale: 1, x: 0, y: 0 }, { x: 100, y: 0 }, 2, { width: 400, height: 300 })
        expect(next).toEqual({ scale: 2, x: -100, y: 0 })
    })

    it("computes touch geometry", () => {
        expect(distance({ x: 0, y: 0 }, { x: 3, y: 4 })).toBe(5)
        expect(midpoint({ x: 0, y: 2 }, { x: 4, y: 6 })).toEqual({ x: 2, y: 4 })
    })
})
