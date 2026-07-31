import { useEffect, useState } from "react"
import { playerRepo, type VideoState } from "@/api/player"

export interface VideoUserState {
    favorite: boolean
    watched: boolean
    notes: string
    progress: number
    duration: number
    updatedAt: number
}

const EMPTY_STATE: VideoUserState = {
    favorite: false,
    watched: false,
    notes: "",
    progress: 0,
    duration: 0,
    updatedAt: 0,
}

const stateCache = new Map<string, VideoUserState>()
const listeners = new Set<() => void>()
const pendingPatches = new Map<string, Partial<VideoUserState>>()
const patchTimers = new Map<string, number>()

export function useVideoUserState(playbackId: string) {
    const [state, setState] = useState<VideoUserState>(() => readVideoState(playbackId))

    useEffect(() => {
        setState(readVideoState(playbackId))
        const listener = () => setState(readVideoState(playbackId))
        listeners.add(listener)
        return () => {
            listeners.delete(listener)
        }
    }, [playbackId])

    const patchState = (patch: Partial<VideoUserState>) => {
        const next = { ...readVideoState(playbackId), ...patch }
        stateCache.set(playbackId, next)
        notifyVideoStateListeners()
        schedulePatch(playbackId, patch)
    }

    function schedulePatch(playbackId: string, patch: Partial<VideoUserState>) {
        pendingPatches.set(playbackId, { ...(pendingPatches.get(playbackId) ?? {}), ...patch })
        const existing = patchTimers.get(playbackId)
        if (existing != null) window.clearTimeout(existing)
        patchTimers.set(playbackId, window.setTimeout(() => {
            patchTimers.delete(playbackId)
            const nextPatch = pendingPatches.get(playbackId)
            pendingPatches.delete(playbackId)
            if (!nextPatch) return
            void playerRepo.updateVideoState({ playback_id: playbackId, ...nextPatch })
                .then((value) => {
                    stateCache.set(playbackId, normalizeVideoState(value))
                    notifyVideoStateListeners()
                })
                .catch(() => undefined)
        }, 80))
    }

    return {
        state,
        setFavorite: (favorite: boolean) => patchState({ favorite }),
    }
}

export function readVideoState(playbackId: string | null | undefined): VideoUserState {
    return playbackId ? stateCache.get(playbackId) ?? EMPTY_STATE : EMPTY_STATE
}

export async function loadVideoStates() {
    const states = await playerRepo.videoStates()
    stateCache.clear()
    for (const state of states) {
        stateCache.set(state.playback_id, normalizeVideoState(state))
    }
    notifyVideoStateListeners()
}

function normalizeVideoState(state: VideoState): VideoUserState {
    return {
        favorite: state.favorite,
        watched: state.watched,
        notes: state.notes,
        progress: state.progress,
        duration: state.duration,
        updatedAt: Date.parse(state.updated_at) || 0,
    }
}

function notifyVideoStateListeners() {
    for (const listener of listeners) listener()
}
