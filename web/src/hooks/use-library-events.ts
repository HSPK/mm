import { useEffect, useRef } from "react"
import { config } from "@/lib/config"
import { resetMusicRuntime } from "@/components/player/music-runtime"
import { useMediaQueryStore } from "@/stores/media-query"
import { useAuthStore } from "@/stores/auth"

export interface LibraryChangedEvent {
    generation: number
    library_id: string
}

export function useLibraryEvents() {
    const generationRef = useRef<number | null>(null)
    const fetchMedia = useMediaQueryStore((state) => state.fetchMedia)
    const fetchUser = useAuthStore((state) => state.fetchUser)

    useEffect(() => {
        const source = new EventSource(`${config.apiBaseUrl}/library/events`, {
            withCredentials: true,
        })
        source.onmessage = (message) => {
            const event = parseLibraryEvent(message.data)
            if (!event) return
            const previous = generationRef.current
            generationRef.current = event.generation
            if (previous == null || previous === event.generation) return
            resetMusicRuntime()
            void fetchUser().then(() => {
                if (!useAuthStore.getState().token) return
                window.dispatchEvent(new CustomEvent<LibraryChangedEvent>(
                    "mm:library-changed",
                    { detail: event },
                ))
                void fetchMedia(true)
            })
        }
        return () => source.close()
    }, [fetchMedia, fetchUser])
}

function parseLibraryEvent(value: string): LibraryChangedEvent | null {
    try {
        const parsed = JSON.parse(value) as Partial<LibraryChangedEvent>
        if (typeof parsed.generation !== "number") return null
        return {
            generation: parsed.generation,
            library_id: typeof parsed.library_id === "string" ? parsed.library_id : "",
        }
    } catch {
        return null
    }
}
