import { beforeEach, describe, expect, it } from "vitest"
import {
    markShortcutsSeen,
    shouldAutoShowShortcuts,
} from "./shortcuts-preferences"

beforeEach(() => {
    localStorage.clear()
})

describe("shortcuts auto-show", () => {
    it("auto-shows on first call", () => {
        expect(shouldAutoShowShortcuts()).toBe(true)
    })

    it("does not auto-show after markShortcutsSeen", () => {
        markShortcutsSeen()
        expect(shouldAutoShowShortcuts()).toBe(false)
    })
})
