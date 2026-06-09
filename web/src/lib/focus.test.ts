import { describe, expect, it } from "vitest"
import { getFocusableElements, trapFocus } from "./focus"

function makeRoot(): HTMLElement {
    const root = document.createElement("div")
    root.innerHTML = `<button id="a">a</button><button id="b">b</button><button id="c">c</button>`
    document.body.appendChild(root)
    return root
}

describe("getFocusableElements", () => {
    it("returns [] for null root", () => {
        expect(getFocusableElements(null)).toEqual([])
    })

    it("returns visible focusable elements", () => {
        const root = makeRoot()
        const found = getFocusableElements(root)
        expect(found.length).toBe(3)
    })
})

describe("trapFocus", () => {
    function tabEvent(shift = false): KeyboardEvent {
        const e = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true })
        Object.defineProperty(e, "shiftKey", { value: shift })
        return e
    }

    it("ignores non-Tab keys", () => {
        const root = makeRoot()
        const e = new KeyboardEvent("keydown", { key: "Escape" })
        expect(trapFocus(e, root)).toBe(false)
    })

    it("wraps from last to first on Tab", () => {
        const root = makeRoot()
        const last = root.querySelector<HTMLButtonElement>("#c")!
        const first = root.querySelector<HTMLButtonElement>("#a")!
        last.focus()
        trapFocus(tabEvent(false), root)
        expect(document.activeElement).toBe(first)
    })

    it("wraps from first to last on Shift+Tab", () => {
        const root = makeRoot()
        const last = root.querySelector<HTMLButtonElement>("#c")!
        const first = root.querySelector<HTMLButtonElement>("#a")!
        first.focus()
        trapFocus(tabEvent(true), root)
        expect(document.activeElement).toBe(last)
    })
})
