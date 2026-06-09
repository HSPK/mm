import { beforeEach, describe, expect, it } from "vitest"
import { useSelectionStore } from "./media-selection"

beforeEach(() => {
    useSelectionStore.setState({
        selectionMode: false,
        selectedIds: new Set<number>(),
    })
})

describe("useSelectionStore", () => {
    it("enter without id starts in selection mode with empty set", () => {
        useSelectionStore.getState().enterSelectionMode()
        const s = useSelectionStore.getState()
        expect(s.selectionMode).toBe(true)
        expect(s.selectedIds.size).toBe(0)
    })

    it("enter with id seeds the selection", () => {
        useSelectionStore.getState().enterSelectionMode(42)
        const s = useSelectionStore.getState()
        expect(s.selectedIds.has(42)).toBe(true)
    })

    it("toggleSelected adds then removes", () => {
        useSelectionStore.getState().enterSelectionMode()
        useSelectionStore.getState().toggleSelected(1)
        expect(useSelectionStore.getState().selectedIds.has(1)).toBe(true)
        useSelectionStore.getState().toggleSelected(2)
        expect(useSelectionStore.getState().selectedIds.size).toBe(2)
        useSelectionStore.getState().toggleSelected(1)
        expect(useSelectionStore.getState().selectedIds.has(1)).toBe(false)
    })

    it("toggleSelected exits selection mode when set becomes empty", () => {
        useSelectionStore.getState().enterSelectionMode(7)
        useSelectionStore.getState().toggleSelected(7)
        expect(useSelectionStore.getState().selectionMode).toBe(false)
    })

    it("selectAllIds replaces the selection", () => {
        useSelectionStore.getState().selectAllIds([10, 20, 30])
        const s = useSelectionStore.getState()
        expect(s.selectionMode).toBe(true)
        expect([...s.selectedIds].sort()).toEqual([10, 20, 30])
    })

    it("pruneRemoved drops ids that are gone", () => {
        useSelectionStore.getState().selectAllIds([1, 2, 3])
        useSelectionStore.getState().pruneRemoved([2])
        expect([...useSelectionStore.getState().selectedIds].sort()).toEqual([1, 3])
    })

    it("exitSelectionMode clears state", () => {
        useSelectionStore.getState().selectAllIds([1, 2])
        useSelectionStore.getState().exitSelectionMode()
        const s = useSelectionStore.getState()
        expect(s.selectionMode).toBe(false)
        expect(s.selectedIds.size).toBe(0)
    })
})
