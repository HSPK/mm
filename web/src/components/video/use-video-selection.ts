import { useCallback } from "react"
import { useLocation, useNavigate, useSearchParams } from "react-router-dom"

const KEY_PARAM = "v"

interface VideoDetailState {
    videoDetail?: boolean
}

/**
 * Tracks the open video detail through an internal-id search param so the
 * detail view lives in the URL (survives refresh, works with browser
 * back/forward) without exposing a filesystem path: `?v=<playback_id>` for the
 * selected movie or show. Opening pushes a history entry; closing pops it when
 * we arrived from the list, else strips the param.
 */
export function useVideoSelection() {
    const location = useLocation()
    const navigate = useNavigate()
    const [searchParams, setSearchParams] = useSearchParams()
    const selectedKey = searchParams.get(KEY_PARAM)

    const buildParams = useCallback((key: string | null) => {
        const next = new URLSearchParams(searchParams)
        if (key == null) next.delete(KEY_PARAM)
        else next.set(KEY_PARAM, key)
        return next
    }, [searchParams])

    const select = useCallback((key: string) => {
        if (selectedKey === key) return
        setSearchParams(buildParams(key), {
            replace: selectedKey != null,
            state: { videoDetail: true } satisfies VideoDetailState,
        })
    }, [buildParams, selectedKey, setSearchParams])

    const clear = useCallback(() => {
        if (selectedKey == null) return
        const openedFromList = Boolean((location.state as VideoDetailState | null)?.videoDetail)
        if (openedFromList) navigate(-1)
        else setSearchParams(buildParams(null), { replace: true, state: null })
    }, [buildParams, location.state, navigate, selectedKey, setSearchParams])

    return { selectedKey, select, clear }
}
