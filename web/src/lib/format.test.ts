import { describe, expect, it } from "vitest"
import {
    fmtDateShort,
    fmtDayGroup,
    fmtDuration,
    fmtMonthGroup,
    getDayKey,
    getMonthKey,
    groupByDay,
    groupByMonth,
} from "./format"

describe("fmtDateShort", () => {
    it("returns empty for null/undefined", () => {
        expect(fmtDateShort(null)).toBe("")
        expect(fmtDateShort(undefined)).toBe("")
    })

    it("formats ISO dates to localized short form", () => {
        const out = fmtDateShort("2024-03-15T10:00:00Z")
        expect(out).toMatch(/2024/)
        expect(out).toMatch(/Mar/)
    })
})

describe("fmtDuration", () => {
    it("returns null for falsy seconds", () => {
        expect(fmtDuration(0)).toBeNull()
        expect(fmtDuration(null)).toBeNull()
    })

    it("formats m:ss with zero-padded seconds", () => {
        expect(fmtDuration(65)).toBe("1:05")
        expect(fmtDuration(3.4)).toBe("0:03")
        expect(fmtDuration(125)).toBe("2:05")
    })
})

describe("month/day key helpers", () => {
    const iso = "2024-03-15T10:00:00Z"
    it("getMonthKey returns YYYY-MM", () => {
        expect(getMonthKey(iso)).toMatch(/^\d{4}-\d{2}$/)
    })
    it("getDayKey returns YYYY-MM-DD", () => {
        expect(getDayKey(iso)).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    })
    it("fmtMonthGroup uses 'YYYY · MM'", () => {
        expect(fmtMonthGroup(iso)).toMatch(/^\d{4} · \d{2}$/)
    })
    it("fmtDayGroup uses 'YYYY · MM · DD'", () => {
        expect(fmtDayGroup(iso)).toMatch(/^\d{4} · \d{2} · \d{2}$/)
    })
})

const items = [
    { id: 1, filename: "a.jpg", extension: ".jpg", media_type: "photo", file_size: 1, rating: 0, date_taken: "2024-01-15T10:00:00Z" },
    { id: 2, filename: "b.jpg", extension: ".jpg", media_type: "photo", file_size: 1, rating: 0, date_taken: "2024-01-20T10:00:00Z" },
    { id: 3, filename: "c.jpg", extension: ".jpg", media_type: "photo", file_size: 1, rating: 0, date_taken: "2024-02-01T10:00:00Z" },
    { id: 4, filename: "d.jpg", extension: ".jpg", media_type: "photo", file_size: 1, rating: 0, date_taken: null },
]

describe("groupByMonth", () => {
    it("groups by year/month and uses 'No Date' for missing", () => {
        const groups = groupByMonth(items)
        const labels = groups.map((g) => g.label)
        expect(labels).toContain("No Date")
        expect(groups.find((g) => g.key === "no-date")?.items).toHaveLength(1)
        const janKey = groups.find((g) => g.items.some((i) => i.id === 1))?.key
        expect(janKey).toBe(groups.find((g) => g.items.some((i) => i.id === 2))?.key)
    })
})

describe("groupByDay", () => {
    it("groups by full date", () => {
        const groups = groupByDay(items)
        expect(groups.find((g) => g.items.some((i) => i.id === 1))?.key)
            .not.toBe(groups.find((g) => g.items.some((i) => i.id === 2))?.key)
        expect(groups.find((g) => g.key === "no-date")?.items).toHaveLength(1)
    })
})
