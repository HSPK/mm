import { describe, expect, it } from "vitest"
import { aggregateTimelineEntries, isValidTimelinePeriod, timelineWindowSize } from "./timeline-bins"

describe("timeline bins", () => {
    const entries = [
        { period: "2026-06-17", count: 2 },
        { period: "2026-06-01", count: 3 },
        { period: "2025-12-31", count: 5 },
        { period: "1980-01-01", count: 99 },
    ]

    it("keeps valid day buckets sorted ascending", () => {
        expect(aggregateTimelineEntries(entries, "day")).toEqual([
            { period: "2025-12-31", count: 5 },
            { period: "2026-06-01", count: 3 },
            { period: "2026-06-17", count: 2 },
        ])
    })

    it("aggregates month and year buckets", () => {
        expect(aggregateTimelineEntries(entries, "month")).toEqual([
            { period: "2025-12", count: 5 },
            { period: "2026-06", count: 5 },
        ])
        expect(aggregateTimelineEntries(entries, "year")).toEqual([
            { period: "2025", count: 5 },
            { period: "2026", count: 5 },
        ])
    })

    it("filters placeholder dates", () => {
        expect(isValidTimelinePeriod("1980-01-01")).toBe(false)
        expect(isValidTimelinePeriod("2026-06-17")).toBe(true)
    })

    it("uses denser windows for finer bins", () => {
        expect(timelineWindowSize("day")).toBeGreaterThan(timelineWindowSize("month"))
        expect(timelineWindowSize("month")).toBeGreaterThan(timelineWindowSize("year"))
    })
})
