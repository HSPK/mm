import { describe, expect, it } from "vitest"
import { cn } from "./utils"

describe("cn", () => {
    it("merges class strings", () => {
        expect(cn("a", "b")).toBe("a b")
    })

    it("ignores falsy values", () => {
        expect(cn("a", false, null, undefined, "b")).toBe("a b")
    })

    it("dedupes conflicting tailwind classes", () => {
        expect(cn("p-2", "p-4")).toBe("p-4")
    })
})
