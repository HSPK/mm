import { create } from "zustand"

interface AlbumSectionState {
    /** Active section id (e.g. "tags", "cameras") — null = main list */
    sectionId: string | null
    /** Display label (e.g. "Tags", "Cameras") */
    label: string | null
    /** Client-side search within section */
    search: string
    enter: (id: string, label: string) => void
    setSearch: (s: string) => void
    exit: () => void
}

export const useAlbumSectionStore = create<AlbumSectionState>((set) => ({
    sectionId: null,
    label: null,
    search: "",
    enter: (id, label) => set({ sectionId: id, label, search: "" }),
    setSearch: (search) => set({ search }),
    exit: () => set({ sectionId: null, label: null, search: "" }),
}))
