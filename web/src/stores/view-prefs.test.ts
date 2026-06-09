import { beforeEach, describe, expect, it } from "vitest"
import { useViewPrefsStore } from "./view-prefs"

beforeEach(() => {
    localStorage.clear()
    useViewPrefsStore.setState({
        viewMode: "justified",
        dateGroupMode: "month",
        thumbSize: 220,
    })
})

describe("useViewPrefsStore", () => {
    it("setViewMode persists to localStorage and updates state", () => {
        useViewPrefsStore.getState().setViewMode("grid")
        expect(useViewPrefsStore.getState().viewMode).toBe("grid")
        expect(localStorage.getItem("mm-view-mode")).toBe("grid")
    })

    it("setDateGroupMode persists to localStorage", () => {
        useViewPrefsStore.getState().setDateGroupMode("day")
        expect(localStorage.getItem("mm-date-group-mode")).toBe("day")
    })

    it("setThumbSize clamps to [min, max] and persists", () => {
        useViewPrefsStore.getState().setThumbSize(10000)
        expect(useViewPrefsStore.getState().thumbSize).toBe(400)
        expect(localStorage.getItem("mm-thumb-size")).toBe("400")

        useViewPrefsStore.getState().setThumbSize(10)
        expect(useViewPrefsStore.getState().thumbSize).toBe(80)
    })
})
