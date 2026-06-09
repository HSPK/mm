import { beforeEach, describe, expect, it } from "vitest"
import {
    createBrowserTokenStorage,
    createMemoryTokenStorage,
} from "./token-storage"

describe("createMemoryTokenStorage", () => {
    it("starts empty by default", () => {
        const s = createMemoryTokenStorage()
        expect(s.get()).toBeNull()
    })

    it("persists set then get", () => {
        const s = createMemoryTokenStorage()
        s.set("abc")
        expect(s.get()).toBe("abc")
        s.clear()
        expect(s.get()).toBeNull()
    })

    it("respects initial value", () => {
        expect(createMemoryTokenStorage("seed").get()).toBe("seed")
    })
})

describe("createBrowserTokenStorage", () => {
    beforeEach(() => {
        localStorage.clear()
    })

    it("reads/writes the localStorage key", () => {
        const s = createBrowserTokenStorage({ storageKey: "k", cookieName: "c" })
        s.set("xyz")
        expect(localStorage.getItem("k")).toBe("xyz")
        expect(document.cookie).toContain("c=xyz")
        expect(s.get()).toBe("xyz")
    })

    it("clears both stores", () => {
        const s = createBrowserTokenStorage({ storageKey: "k", cookieName: "c" })
        s.set("xyz")
        s.clear()
        expect(localStorage.getItem("k")).toBeNull()
        expect(s.get()).toBeNull()
    })
})
