import { describe, expect, it } from "vitest"
import {
    AXIS_LOCK_PX,
    clamp,
    detectAxis,
    formatDelta,
    formatTime,
    horizontalDragSeconds,
    SEEK_FULL_WIDTH_SECONDS,
    verticalDragDelta,
} from "./gesture-math"

describe("detectAxis", () => {
    it("returns null until movement crosses the lock threshold", () => {
        expect(detectAxis(2, 3)).toBeNull()
        expect(detectAxis(AXIS_LOCK_PX - 1, 0)).toBeNull()
    })

    it("returns horizontal when dx dominates", () => {
        expect(detectAxis(40, 5)).toBe("horizontal")
        expect(detectAxis(-40, -2)).toBe("horizontal")
    })

    it("returns vertical when dy dominates", () => {
        expect(detectAxis(5, 40)).toBe("vertical")
        expect(detectAxis(-2, -40)).toBe("vertical")
    })

    it("breaks ties toward horizontal", () => {
        expect(detectAxis(20, 20)).toBe("vertical") // strictly > comparison; equal → vertical
        expect(detectAxis(21, 20)).toBe("horizontal")
    })
})

describe("verticalDragDelta", () => {
    it("returns 0 for invalid container", () => {
        expect(verticalDragDelta(50, 0)).toBe(0)
    })

    it("clamps to ±1 outside one container height", () => {
        expect(verticalDragDelta(-500, 200)).toBe(1)
        expect(verticalDragDelta(500, 200)).toBe(-1)
    })

    it("returns a proportional fraction otherwise (drag up = positive)", () => {
        expect(verticalDragDelta(-100, 200)).toBeCloseTo(0.5)
        expect(verticalDragDelta(50, 200)).toBeCloseTo(-0.25)
    })
})

describe("horizontalDragSeconds", () => {
    it("maps a full-width drag to SEEK_FULL_WIDTH_SECONDS", () => {
        expect(horizontalDragSeconds(400, 400)).toBe(SEEK_FULL_WIDTH_SECONDS)
        expect(horizontalDragSeconds(-400, 400)).toBe(-SEEK_FULL_WIDTH_SECONDS)
    })

    it("returns 0 for invalid width", () => {
        expect(horizontalDragSeconds(50, 0)).toBe(0)
    })

    it("is proportional to width", () => {
        expect(horizontalDragSeconds(200, 400)).toBeCloseTo(SEEK_FULL_WIDTH_SECONDS / 2)
    })
})

describe("clamp", () => {
    it("returns min/max at extremes", () => {
        expect(clamp(-10, 0, 100)).toBe(0)
        expect(clamp(1000, 0, 100)).toBe(100)
        expect(clamp(50, 0, 100)).toBe(50)
    })
})

describe("formatTime", () => {
    it("formats m:ss for short durations", () => {
        expect(formatTime(0)).toBe("0:00")
        expect(formatTime(7)).toBe("0:07")
        expect(formatTime(65)).toBe("1:05")
    })

    it("formats h:mm:ss for long durations", () => {
        expect(formatTime(3661)).toBe("1:01:01")
    })

    it("guards against negatives and NaN", () => {
        expect(formatTime(-5)).toBe("0:00")
        expect(formatTime(Number.NaN)).toBe("0:00")
    })
})

describe("formatDelta", () => {
    it("renders + for forward deltas", () => {
        expect(formatDelta(10)).toBe("+0:10")
    })

    it("renders − for backward deltas", () => {
        expect(formatDelta(-65)).toBe("−1:05")
    })
})
