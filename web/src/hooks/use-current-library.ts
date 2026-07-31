import axios from "axios"
import { useCallback, useEffect, useState } from "react"
import { libraryRepo, type LibraryInfo } from "@/api/library"
import { resetMusicRuntime } from "@/components/player/music-runtime"
import { useMediaQueryStore } from "@/stores/media-query"
import { useAuthStore } from "@/stores/auth"

export interface UseCurrentLibraryResult {
    current: LibraryInfo | null
    recent: LibraryInfo[]
    switching: boolean
    error: string | null
    switchTo: (dbPath: string) => Promise<void>
}

export function useCurrentLibrary(): UseCurrentLibraryResult {
    const fetchMedia = useMediaQueryStore((s) => s.fetchMedia)
    const fetchUser = useAuthStore((state) => state.fetchUser)
    const [current, setCurrent] = useState<LibraryInfo | null>(null)
    const [recent, setRecent] = useState<LibraryInfo[]>([])
    const [switching, setSwitching] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const refresh = useCallback(() => {
        libraryRepo.getCurrent().then(setCurrent).catch(() => { })
        libraryRepo.listRecent().then(setRecent).catch(() => { })
    }, [])

    useEffect(() => {
        refresh()
    }, [refresh])

    const switchTo = useCallback(async (dbPath: string) => {
        if (!dbPath.trim()) return
        setSwitching(true)
        setError(null)
        try {
            const res = await libraryRepo.switchTo(dbPath)
            resetMusicRuntime()
            setCurrent(res)
            libraryRepo.listRecent().then(setRecent).catch(() => { })
            await fetchUser()
            if (!useAuthStore.getState().token) return
            fetchMedia(true)
        } catch (err: unknown) {
            const detail = axios.isAxiosError<{ detail?: string }>(err) ? err.response?.data?.detail : null
            const message = err instanceof Error ? err.message : null
            setError(detail || message || "Failed to switch library")
        } finally {
            setSwitching(false)
        }
    }, [fetchMedia, fetchUser])

    return { current, recent, switching, error, switchTo }
}
