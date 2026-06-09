import { describe, expect, it } from "vitest"
import { addBoundedId } from "./bounded-set"

describe("addBoundedId", () => {
    it("returns the same Set instance when id is already present", () => {
        const s = new Set([1, 2, 3])
        const out = addBoundedId(s, 2)
        expect(out).toBe(s)
    })

    it("inserts new ids up to the limit", () => {
        const s = new Set<number>()
        const out = addBoundedId(s, 1, 3)
        expect([...out]).toEqual([1])
    })

    it("evicts the oldest entry when over the limit", () => {
        const s = new Set([1, 2, 3])
        const out = addBoundedId(s, 4, 3)
        expect([...out]).toEqual([2, 3, 4])
    })

    it("evicts multiple oldest if needed (uses default limit 32)", () => {
        let s = new Set<number>()
        for (let i = 0; i < 35; i++) s = addBoundedId(s, i)
        expect(s.size).toBe(32)
        expect(s.has(0)).toBe(false)
        expect(s.has(34)).toBe(true)
    })
})
