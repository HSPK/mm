import { create } from "zustand"
import { config, clampThumbSize } from "@/lib/config"

export type ViewMode = "justified" | "grid"
export type DateGroupMode = "day" | "month"

interface ViewPrefsState {
    viewMode: ViewMode
    dateGroupMode: DateGroupMode
    thumbSize: number
    setViewMode: (mode: ViewMode) => void
    setDateGroupMode: (mode: DateGroupMode) => void
    setThumbSize: (size: number) => void
}

function safeRead(key: string): string | null {
    try {
        return localStorage.getItem(key)
    } catch {
        return null
    }
}

function safeWrite(key: string, value: string): void {
    try {
        localStorage.setItem(key, value)
    } catch {
        // localStorage may be unavailable in some embedded contexts; ignore.
    }
}

function initialViewMode(): ViewMode {
    return safeRead(config.viewPrefs.viewModeKey) === "grid" ? "grid" : "justified"
}

function initialDateGroupMode(): DateGroupMode {
    return safeRead(config.viewPrefs.dateGroupModeKey) === "day" ? "day" : "month"
}

function initialThumbSize(): number {
    const stored = Number(safeRead(config.viewPrefs.thumbSizeKey)) || config.thumbSize.default
    return clampThumbSize(stored)
}

export const useViewPrefsStore = create<ViewPrefsState>((set) => ({
    viewMode: initialViewMode(),
    dateGroupMode: initialDateGroupMode(),
    thumbSize: initialThumbSize(),
    setViewMode: (mode) => {
        safeWrite(config.viewPrefs.viewModeKey, mode)
        set({ viewMode: mode })
    },
    setDateGroupMode: (mode) => {
        safeWrite(config.viewPrefs.dateGroupModeKey, mode)
        set({ dateGroupMode: mode })
    },
    setThumbSize: (size) => {
        const clamped = clampThumbSize(size)
        safeWrite(config.viewPrefs.thumbSizeKey, String(clamped))
        set({ thumbSize: clamped })
    },
}))
