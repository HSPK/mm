import { create } from "zustand"

interface SelectionState {
    selectionMode: boolean
    selectedIds: Set<number>
    enterSelectionMode: (initialId?: number) => void
    exitSelectionMode: () => void
    toggleSelected: (id: number) => void
    selectAllIds: (ids: number[]) => void
    pruneRemoved: (ids: number[]) => void
}

export const useSelectionStore = create<SelectionState>((set) => ({
    selectionMode: false,
    selectedIds: new Set<number>(),

    enterSelectionMode: (initialId) => {
        const next = new Set<number>()
        if (initialId != null) next.add(initialId)
        set({ selectionMode: true, selectedIds: next })
    },

    exitSelectionMode: () => {
        set({ selectionMode: false, selectedIds: new Set<number>() })
    },

    toggleSelected: (id) => {
        set((s) => {
            const next = new Set(s.selectedIds)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            if (next.size === 0) return { selectionMode: false, selectedIds: next }
            return { selectedIds: next }
        })
    },

    selectAllIds: (ids) => {
        set({ selectionMode: true, selectedIds: new Set(ids) })
    },

    pruneRemoved: (removed) => {
        const toRemove = new Set(removed)
        set((s) => ({
            selectedIds: new Set([...s.selectedIds].filter((id) => !toRemove.has(id))),
        }))
    },
}))
