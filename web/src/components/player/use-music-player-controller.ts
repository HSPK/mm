import { useCallback, useEffect, useMemo, useRef, useState, type SyntheticEvent } from "react"
import { api } from "@/api/client"
import { playerRepo } from "@/api/player"
import { currentTrack, usePlayerStore } from "@/stores/player"
import { notify } from "@/stores/notifications"
import {
    type AudioInfoResponse,
    activeLyricLine,
    organizerFileUrl,
    parseLyrics,
    usesCrossOriginApi,
    validDuration,
} from "./music-player-utils"
import { seekAudio } from "./music-player-transport"
import { cacheMusicDuration, cachedMusicDuration } from "./music-media-cache"
import { useEnrichedPlayerTrack, usePrefetchEnrichedPlayerTracks } from "./use-enriched-player-track"

const MUSIC_TAB_ID = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`

export function useMusicPlayerController() {
    const audioRef = useRef<HTMLAudioElement | null>(null)
    const notifiedErrorRef = useRef<string | null>(null)
    const failedEntriesRef = useRef(new Set<string>())
    const successfulPlaybackTimerRef = useRef<number | null>(null)
    const loadedSourceKeyRef = useRef<string | null>(null)
    const ticketRetryEntriesRef = useRef(new Set<string>())
    const playbackChannelRef = useRef<BroadcastChannel | null>(null)
    const queue = usePlayerStore((state) => state.queue)
    const index = usePlayerStore((state) => state.index)
    const shouldPlay = usePlayerStore((state) => state.shouldPlay)
    const transportRequestId = usePlayerStore((state) => state.transportRequestId)
    const playbackStatus = usePlayerStore((state) => state.playbackStatus)
    const currentTime = usePlayerStore((state) => state.currentTime)
    const duration = usePlayerStore((state) => state.duration)
    const volume = usePlayerStore((state) => state.volume)
    const shuffle = usePlayerStore((state) => state.shuffle)
    const repeatMode = usePlayerStore((state) => state.repeatMode)
    const setQueue = usePlayerStore((state) => state.setQueue)
    const selectQueueIndex = usePlayerStore((state) => state.selectQueueIndex)
    const failPlayback = usePlayerStore((state) => state.failPlayback)
    const markPlaybackStatus = usePlayerStore((state) => state.markPlaybackStatus)
    const setTime = usePlayerStore((state) => state.setTime)
    const setDuration = usePlayerStore((state) => state.setDuration)
    const setVolume = usePlayerStore((state) => state.setVolume)
    const toggleShuffle = usePlayerStore((state) => state.toggleShuffle)
    const cycleRepeat = usePlayerStore((state) => state.cycleRepeat)
    const [remoteSource, setRemoteSource] = useState<{
        playbackId: string
        sourceKey: string
        status: "loading" | "ready" | "error"
        url: string
    }>({ playbackId: "", sourceKey: "", status: "loading", url: "" })
    const [sourceRefreshVersion, setSourceRefreshVersion] = useState(0)
    const track = useMemo(() => currentTrack({ queue, index }), [index, queue])
    const trackId = track?.id ?? null
    const sourceKey = track?.queueEntryId ?? null
    const crossOriginApi = usesCrossOriginApi()
    const signedUrl = crossOriginApi && remoteSource.sourceKey === sourceKey
        && remoteSource.status === "ready"
        ? remoteSource.url
        : undefined
    const trackUrl = track?.playbackId && track.playable !== false
        && (!crossOriginApi || signedUrl)
        ? organizerFileUrl(track.playbackId, signedUrl)
        : ""
    const displayDuration = duration > 0
        ? duration
        : track?.duration ?? cachedMusicDuration(track?.playbackId) ?? 0
    const lyricsResource = useEnrichedPlayerTrack(track)
    const lyrics = useMemo(() => parseLyrics(track ? {
        ...track,
        lyrics: lyricsResource.lyrics,
        syncedLyrics: lyricsResource.syncedLyrics,
    } : null), [lyricsResource.lyrics, lyricsResource.syncedLyrics, track])
    const activeLyricIndex = useMemo(
        () => activeLyricLine(lyrics.synced, currentTime),
        [currentTime, lyrics.synced],
    )
    const isPlaying = playbackStatus === "playing"
        || (playbackStatus === "loading" && shouldPlay)
    const skipFailedTrack = useCallback((entryId: string) => {
        skipFailedQueueEntry(audioRef.current, failedEntriesRef.current, entryId)
    }, [])
    const isCurrentMediaEvent = useCallback((audio: HTMLAudioElement) => {
        const active = currentTrack(usePlayerStore.getState())
        if (
            !active
            || active.queueEntryId !== sourceKey
            || loadedSourceKeyRef.current !== sourceKey
        ) return false
        if (!trackUrl || !audio.currentSrc) return true
        return audio.currentSrc === new URL(trackUrl, window.location.href).href
    }, [sourceKey, trackUrl])
    const refreshMediaTicket = useCallback((
        entryId: string,
        playbackId: string | null | undefined,
    ) => {
        if (
            !crossOriginApi
            || !playbackId
            || ticketRetryEntriesRef.current.has(entryId)
        ) return false
        ticketRetryEntriesRef.current.add(entryId)
        loadedSourceKeyRef.current = null
        setRemoteSource({
            playbackId,
            sourceKey: entryId,
            status: "loading",
            url: "",
        })
        setSourceRefreshVersion((version) => version + 1)
        return true
    }, [crossOriginApi])

    const { status: lyricsStatus, retry: retryLyrics } = lyricsResource
    usePrefetchEnrichedPlayerTracks(queue, index)

    useEffect(() => {
        const playbackId = track?.playbackId
        if (!crossOriginApi || !playbackId || !sourceKey || !trackId || track?.playable === false) {
            return
        }
        let cancelled = false
        void playerRepo.audioSource(playbackId).then((source) => {
            if (cancelled) return
            if (!source.directly_supported || source.known_unsupported || !source.url) {
                usePlayerStore.getState().updateTrack(trackId, {
                    playable: false,
                    unavailableReason: source.unsupported_reason || "This audio source is unavailable.",
                })
                return
            }
            setRemoteSource({
                playbackId,
                sourceKey,
                status: "ready",
                url: source.url,
            })
        }).catch(() => {
            if (!cancelled) {
                setRemoteSource({ playbackId, sourceKey, status: "error", url: "" })
            }
        })
        return () => {
            cancelled = true
        }
    }, [
        crossOriginApi,
        sourceKey,
        sourceRefreshVersion,
        track?.playable,
        track?.playbackId,
        trackId,
    ])

    useEffect(() => {
        const audio = audioRef.current
        if (!audio) return
        const state = usePlayerStore.getState()
        const activeTrack = currentTrack(state)
        loadedSourceKeyRef.current = null
        notifiedErrorRef.current = null
        setTime(0)
        setDuration(validDuration(
            activeTrack?.duration ?? cachedMusicDuration(activeTrack?.playbackId) ?? 0,
        ) ?? 0)
        audio.pause()
        if (successfulPlaybackTimerRef.current != null) {
            window.clearTimeout(successfulPlaybackTimerRef.current)
            successfulPlaybackTimerRef.current = null
        }
        if (
            activeTrack?.mimeType
            && typeof audio.canPlayType === "function"
            && audio.canPlayType(activeTrack.mimeType) === ""
        ) {
            audio.removeAttribute("src")
            audio.load()
            state.updateTrack(activeTrack.id, {
                playable: false,
                unavailableReason: `${activeTrack.title} is not supported by this browser.`,
            })
            return
        }
        if (!trackUrl) {
            audio.removeAttribute("src")
            audio.load()
            markPlaybackStatus(activeTrack ? state.shouldPlay ? "loading" : "paused" : "idle")
            return
        }
        const absoluteUrl = new URL(trackUrl, window.location.href).href
        if (audio.src !== absoluteUrl) {
            audio.src = trackUrl
        }
        loadedSourceKeyRef.current = sourceKey
        audio.load()
        markPlaybackStatus(state.shouldPlay ? "loading" : "paused")
    }, [
        markPlaybackStatus,
        setDuration,
        setTime,
        sourceKey,
        trackUrl,
    ])

    useEffect(() => {
        const fallbackDuration = validDuration(track?.duration ?? 0)
        if (duration <= 0 && fallbackDuration != null) setDuration(fallbackDuration)
    }, [duration, setDuration, track?.duration])

    useEffect(() => {
        const audio = audioRef.current
        if (!audio || !trackId || !sourceKey) return
        if (!trackUrl) {
            if (usePlayerStore.getState().playbackStatus !== "error") {
                markPlaybackStatus(shouldPlay ? "loading" : "paused")
            }
            return
        }
        const requestId = transportRequestId
        if (!shouldPlay) {
            audio.pause()
            if (usePlayerStore.getState().playbackStatus !== "error") {
                markPlaybackStatus("paused")
            }
            return
        }
        notifiedErrorRef.current = null
        markPlaybackStatus("loading")
        let cancelled = false
        void audio.play().catch((error: unknown) => {
            const state = usePlayerStore.getState()
            if (
                cancelled
                || state.transportRequestId !== requestId
                || currentTrack(state)?.queueEntryId !== sourceKey
            ) return
            if (refreshMediaTicket(sourceKey, currentTrack(state)?.playbackId)) return
            reportPlaybackFailure(
                notifiedErrorRef,
                sourceKey,
                `${currentTrack(state)?.title ?? "This track"} could not be played.`,
            )
            failPlayback()
            if (!(error instanceof DOMException && error.name === "NotAllowedError")) {
                skipFailedTrack(sourceKey)
            }
        })
        return () => {
            cancelled = true
        }
    }, [
        failPlayback,
        markPlaybackStatus,
        shouldPlay,
        sourceKey,
        trackId,
        trackUrl,
        transportRequestId,
        skipFailedTrack,
        refreshMediaTicket,
    ])

    useEffect(() => {
        const audio = audioRef.current
        if (audio) audio.volume = volume
    }, [volume])

    useEffect(() => {
        if (typeof BroadcastChannel === "undefined") return
        const channel = new BroadcastChannel("mm-music-playback")
        playbackChannelRef.current = channel
        channel.onmessage = (event: MessageEvent<{ type?: string, sender?: string }>) => {
            if (event.data.type !== "playing" || event.data.sender === MUSIC_TAB_ID) return
            const state = usePlayerStore.getState()
            if (state.shouldPlay || state.playbackStatus === "playing") state.requestPause()
        }
        return () => {
            playbackChannelRef.current = null
            channel.close()
        }
    }, [])

    useEffect(() => {
        const playbackId = track?.playbackId
        if (
            !playbackId
            || validDuration(track.duration ?? 0) != null
            || validDuration(cachedMusicDuration(playbackId) ?? 0) != null
        ) return
        const controller = new AbortController()
        void api.get<AudioInfoResponse>("/player/audio/info", {
            params: { playback_id: playbackId },
            signal: controller.signal,
        }).then((response) => {
            const infoDuration = validDuration(response.data.duration ?? 0)
            const state = usePlayerStore.getState()
            if (
                infoDuration != null
                && state.duration <= 0
                && currentTrack(state)?.playbackId === playbackId
            ) {
                cacheMusicDuration(playbackId, infoDuration)
                state.setDuration(infoDuration)
            }
        }).catch(() => undefined)
        return () => controller.abort()
    }, [track?.duration, track?.playbackId])

    const play = useCallback(() => {
        usePlayerStore.getState().requestPlay()
    }, [])

    const pause = useCallback(() => {
        usePlayerStore.getState().requestPause()
    }, [])

    const toggle = useCallback(() => {
        const state = usePlayerStore.getState()
        const active = state.playbackStatus === "playing"
            || (state.playbackStatus === "loading" && state.shouldPlay)
        if (active) state.requestPause()
        else state.requestPlay()
    }, [])

    const seek = useCallback((time: number) => {
        const audio = audioRef.current
        if (!audio) return
        const position = seekAudio(audio, time)
        usePlayerStore.getState().setTime(position)
    }, [])

    const advance = useCallback((reason: "manual" | "ended") => {
        const state = usePlayerStore.getState()
        if (!currentTrack(state)) return
        const transition = state.nextQueue(reason)
        if (transition === "restart") {
            seek(0)
            state.requestPlay()
        } else if (transition === "finish") {
            const audioDuration = validDuration(audioRef.current?.duration ?? 0)
            state.finishPlayback(audioDuration ?? state.duration)
        }
    }, [seek])

    const next = useCallback(() => {
        advance("manual")
    }, [advance])

    const handleEnded = useCallback(() => {
        advance("ended")
    }, [advance])

    useEffect(() => {
        if (!track || !shouldPlay || trackUrl) return
        if (track.playable === false) {
            reportPlaybackFailure(
                notifiedErrorRef,
                track.queueEntryId,
                track.unavailableReason || `${track.title} is not supported by this browser.`,
            )
            failPlayback()
            skipFailedTrack(track.queueEntryId)
        } else if (lyricsStatus === "unavailable") {
            reportPlaybackFailure(
                notifiedErrorRef,
                track.queueEntryId,
                `${track.title} is missing a playback resource.`,
            )
            failPlayback()
            skipFailedTrack(track.queueEntryId)
        } else if (
            crossOriginApi
            && remoteSource.sourceKey === track.queueEntryId
            && remoteSource.status === "error"
        ) {
            reportPlaybackFailure(
                notifiedErrorRef,
                track.queueEntryId,
                `${track.title} could not obtain a secure playback URL.`,
            )
            failPlayback()
            skipFailedTrack(track.queueEntryId)
        }
    }, [
        failPlayback,
        crossOriginApi,
        lyricsStatus,
        remoteSource.sourceKey,
        remoteSource.status,
        shouldPlay,
        skipFailedTrack,
        track,
        trackUrl,
    ])

    const previous = useCallback(() => {
        const state = usePlayerStore.getState()
        if (!currentTrack(state)) return
        const position = audioRef.current?.currentTime ?? state.currentTime
        const transition = state.previousQueue(position)
        if (transition === "restart") {
            seek(0)
            if (!state.shouldPlay) state.requestPlay()
        }
    }, [seek])

    const handleDuration = useCallback((event: SyntheticEvent<HTMLAudioElement>) => {
        if (!isCurrentMediaEvent(event.currentTarget)) return
        const nextDuration = validDuration(event.currentTarget.duration)
        if (nextDuration != null) {
            const state = usePlayerStore.getState()
            cacheMusicDuration(currentTrack(state)?.playbackId, nextDuration)
            state.setDuration(nextDuration)
        }
    }, [isCurrentMediaEvent])

    const handleTimeUpdate = useCallback((event: SyntheticEvent<HTMLAudioElement>) => {
        if (!isCurrentMediaEvent(event.currentTarget)) return
        usePlayerStore.getState().setTime(event.currentTarget.currentTime)
    }, [isCurrentMediaEvent])

    const handlePlay = useCallback((event: SyntheticEvent<HTMLAudioElement>) => {
        if (!isCurrentMediaEvent(event.currentTarget)) return
        usePlayerStore.getState().markPlaybackStatus("loading")
    }, [isCurrentMediaEvent])

    const handlePlaying = useCallback((event: SyntheticEvent<HTMLAudioElement>) => {
        if (!isCurrentMediaEvent(event.currentTarget)) return
        const entryId = currentTrack(usePlayerStore.getState())?.queueEntryId
        playbackChannelRef.current?.postMessage({
            type: "playing",
            sender: MUSIC_TAB_ID,
        })
        usePlayerStore.getState().markPlaybackStatus("playing")
        if (successfulPlaybackTimerRef.current != null) {
            window.clearTimeout(successfulPlaybackTimerRef.current)
        }
        successfulPlaybackTimerRef.current = window.setTimeout(() => {
            if (currentTrack(usePlayerStore.getState())?.queueEntryId === entryId) {
                failedEntriesRef.current.clear()
                if (entryId) ticketRetryEntriesRef.current.delete(entryId)
            }
            successfulPlaybackTimerRef.current = null
        }, 2_000)
    }, [isCurrentMediaEvent])

    const handlePause = useCallback((event: SyntheticEvent<HTMLAudioElement>) => {
        if (!isCurrentMediaEvent(event.currentTarget)) return
        if (successfulPlaybackTimerRef.current != null) {
            window.clearTimeout(successfulPlaybackTimerRef.current)
            successfulPlaybackTimerRef.current = null
        }
        const state = usePlayerStore.getState()
        if (state.playbackStatus !== "error") state.markPlaybackStatus("paused")
    }, [isCurrentMediaEvent])

    const handleWaiting = useCallback((event: SyntheticEvent<HTMLAudioElement>) => {
        if (!isCurrentMediaEvent(event.currentTarget)) return
        const state = usePlayerStore.getState()
        if (state.shouldPlay) state.markPlaybackStatus("loading")
    }, [isCurrentMediaEvent])

    const handleError = useCallback((event: SyntheticEvent<HTMLAudioElement>) => {
        if (!isCurrentMediaEvent(event.currentTarget)) return
        if (successfulPlaybackTimerRef.current != null) {
            window.clearTimeout(successfulPlaybackTimerRef.current)
            successfulPlaybackTimerRef.current = null
        }
        const audio = event.currentTarget
        const state = usePlayerStore.getState()
        const activeTrack = currentTrack(state)
        if (!activeTrack) return
        if (refreshMediaTicket(activeTrack.queueEntryId, activeTrack.playbackId)) return
        const code = audio.error?.code
        reportPlaybackFailure(
            notifiedErrorRef,
            activeTrack.id,
            `${activeTrack.title} could not be played${code ? ` (code ${code})` : ""}.`,
        )
        state.failPlayback()
        skipFailedTrack(activeTrack.queueEntryId)
    }, [
        isCurrentMediaEvent,
        refreshMediaTicket,
        skipFailedTrack,
    ])

    useEffect(() => {
        if (!("mediaSession" in navigator)) return
        if (!track) {
            navigator.mediaSession.metadata = null
            return
        }
        if (typeof MediaMetadata !== "undefined") {
            navigator.mediaSession.metadata = new MediaMetadata({
                title: track.title,
                artist: track.artist,
                album: track.album,
                artwork: track.artworkUrl
                    ? [{ src: track.artworkUrl, sizes: "512x512", type: "image/jpeg" }]
                    : [],
            })
        }
        navigator.mediaSession.setActionHandler("play", play)
        navigator.mediaSession.setActionHandler("pause", pause)
        navigator.mediaSession.setActionHandler("previoustrack", previous)
        navigator.mediaSession.setActionHandler("nexttrack", next)
        navigator.mediaSession.setActionHandler("seekto", (details) => {
            if (details.seekTime != null) seek(details.seekTime)
        })
        navigator.mediaSession.setActionHandler("seekbackward", (details) => {
            seek((audioRef.current?.currentTime ?? 0) - (details.seekOffset ?? 10))
        })
        navigator.mediaSession.setActionHandler("seekforward", (details) => {
            seek((audioRef.current?.currentTime ?? 0) + (details.seekOffset ?? 10))
        })
        return () => {
            navigator.mediaSession.setActionHandler("play", null)
            navigator.mediaSession.setActionHandler("pause", null)
            navigator.mediaSession.setActionHandler("previoustrack", null)
            navigator.mediaSession.setActionHandler("nexttrack", null)
            navigator.mediaSession.setActionHandler("seekto", null)
            navigator.mediaSession.setActionHandler("seekbackward", null)
            navigator.mediaSession.setActionHandler("seekforward", null)
        }
    }, [next, pause, play, previous, seek, track])

    useEffect(() => {
        if (!("mediaSession" in navigator)) return
        navigator.mediaSession.playbackState = playbackStatus === "playing"
            ? "playing"
            : playbackStatus === "paused" || playbackStatus === "error"
                ? "paused"
                : "none"
        if (displayDuration <= 0 || currentTime > displayDuration) return
        try {
            navigator.mediaSession.setPositionState({
                duration: displayDuration,
                playbackRate: audioRef.current?.playbackRate || 1,
                position: Math.min(currentTime, displayDuration),
            })
        } catch {
            // Some browsers expose Media Session without position-state support.
        }
    }, [currentTime, displayDuration, playbackStatus])

    useEffect(() => () => {
        const audio = audioRef.current
        if (!audio) return
        if (successfulPlaybackTimerRef.current != null) {
            window.clearTimeout(successfulPlaybackTimerRef.current)
            successfulPlaybackTimerRef.current = null
        }
        audio.pause()
        audio.removeAttribute("src")
        audio.load()
        if ("mediaSession" in navigator) {
            navigator.mediaSession.metadata = null
            navigator.mediaSession.playbackState = "none"
        }
    }, [])

    return {
        audioRef,
        track,
        queue,
        index,
        currentTime,
        duration: displayDuration,
        volume,
        shuffle,
        repeatMode,
        isPlaying,
        lyrics,
        lyricsStatus,
        retryLyrics,
        activeLyricIndex,
        setQueue,
        selectQueueIndex,
        setVolume,
        toggleShuffle,
        cycleRepeat,
        play,
        pause,
        toggle,
        next,
        previous,
        seek,
        audioHandlers: {
            onTimeUpdate: handleTimeUpdate,
            onDurationChange: handleDuration,
            onLoadedMetadata: handleDuration,
            onPlay: handlePlay,
            onPlaying: handlePlaying,
            onPause: handlePause,
            onWaiting: handleWaiting,
            onError: handleError,
            onEnded: handleEnded,
        },
    }
}

function reportPlaybackFailure(
    notifiedErrorRef: { current: string | null },
    trackId: string,
    message: string,
) {
    if (notifiedErrorRef.current === trackId) return
    notifiedErrorRef.current = trackId
    notify.error("Playback failed", message)
}

function skipFailedQueueEntry(
    audio: HTMLAudioElement | null,
    failedEntries: Set<string>,
    entryId: string,
) {
    failedEntries.add(entryId)
    const state = usePlayerStore.getState()
    if (failedEntries.size >= state.queue.length) return
    window.setTimeout(() => {
        const nextState = usePlayerStore.getState()
        const transition = nextState.nextQueue("manual")
        if (transition === "restart") {
            if (audio) {
                const position = seekAudio(audio, 0)
                nextState.setTime(position)
            }
            nextState.requestPlay()
        } else if (transition === "finish") {
            nextState.finishPlayback(nextState.duration)
        }
    }, 0)
}
