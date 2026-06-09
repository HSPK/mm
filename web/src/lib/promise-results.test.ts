import { describe, expect, it } from "vitest"
import { fulfilledIds } from "./promise-results"

describe("fulfilledIds", () => {
    it("returns ids whose result was fulfilled in the same order", () => {
        const ids = [1, 2, 3, 4]
        const results: PromiseSettledResult<unknown>[] = [
            { status: "fulfilled", value: "a" },
            { status: "rejected", reason: new Error("nope") },
            { status: "fulfilled", value: "b" },
            { status: "rejected", reason: new Error("nope") },
        ]
        expect(fulfilledIds(ids, results)).toEqual([1, 3])
    })

    it("returns [] when all rejected", () => {
        const ids = [1, 2]
        const results: PromiseSettledResult<unknown>[] = [
            { status: "rejected", reason: 1 },
            { status: "rejected", reason: 2 },
        ]
        expect(fulfilledIds(ids, results)).toEqual([])
    })

    it("returns full ids when all fulfilled", () => {
        const ids = [10, 20]
        const results: PromiseSettledResult<unknown>[] = [
            { status: "fulfilled", value: 1 },
            { status: "fulfilled", value: 2 },
        ]
        expect(fulfilledIds(ids, results)).toEqual([10, 20])
    })
})
