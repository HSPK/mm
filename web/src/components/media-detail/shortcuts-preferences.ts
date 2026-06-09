const STORAGE_KEY = "mm-viewer-shortcuts-seen"

export function shouldAutoShowShortcuts(): boolean {
    try {
        return !localStorage.getItem(STORAGE_KEY)
    } catch {
        return false
    }
}

export function markShortcutsSeen(): void {
    try {
        localStorage.setItem(STORAGE_KEY, "1")
    } catch {
        /* localStorage may be unavailable */
    }
}
