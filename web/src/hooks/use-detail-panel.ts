import { useCallback, useEffect, useMemo, useRef } from "react"
import { useLocation, useNavigate, useSearchParams } from "react-router-dom"
import type { Media } from "@/api/types"

interface CloseDetailOptions {
    syncHistory?: boolean
}

/**
 * Manages detail panel state through React Router search params.
 * Opening a photo pushes `?media=<id>`; left/right navigation replaces it.
 */
export function useDetailPanel(items: Media[]) {
    const location = useLocation()
    const navigate = useNavigate()
    const [searchParams, setSearchParams] = useSearchParams()
    const openedFromGridRef = useRef(false)

    const detailId = useMemo(() => {
        const raw = searchParams.get("media")
        if (!raw) return null
        const id = Number(raw)
        return Number.isSafeInteger(id) && id > 0 ? id : null
    }, [searchParams])

    const getNextSearchParams = useCallback((id: number | null) => {
        const next = new URLSearchParams(searchParams)
        if (id == null) next.delete("media")
        else next.set("media", String(id))
        return next
    }, [searchParams])

    const closeDetail = useCallback((options: CloseDetailOptions = {}) => {
        const syncHistory = options.syncHistory ?? true
        if (detailId == null) return

        const canGoBackToList = openedFromGridRef.current || Boolean(location.state?.mediaDetail)
        openedFromGridRef.current = false
        if (syncHistory && canGoBackToList) {
            navigate(-1)
        } else {
            setSearchParams(getNextSearchParams(null), { replace: true, state: null })
        }
    }, [detailId, getNextSearchParams, location.state, navigate, setSearchParams])

    const closeDetailWithoutHistory = useCallback(() => {
        closeDetail({ syncHistory: false })
    }, [closeDetail])

    const closeDetailForNavigation = useCallback(async () => {
        if (detailId == null) return

        const canGoBackToList = openedFromGridRef.current || Boolean(location.state?.mediaDetail)
        openedFromGridRef.current = false
        if (canGoBackToList) {
            navigate(-1)
            await new Promise((resolve) => window.setTimeout(resolve, 0))
        } else {
            setSearchParams(getNextSearchParams(null), { replace: true, state: null })
        }
    }, [detailId, getNextSearchParams, location.state, navigate, setSearchParams])

    const openDetail = useCallback((id: number) => {
        if (detailId === id) return
        openedFromGridRef.current = true
        setSearchParams(getNextSearchParams(id), { replace: false, state: { mediaDetail: true } })
    }, [detailId, getNextSearchParams, setSearchParams])

    const setActiveDetail = useCallback((id: number) => {
        if (detailId === id) return
        setSearchParams(getNextSearchParams(id), {
            replace: true,
            state: openedFromGridRef.current ? { mediaDetail: true } : location.state,
        })
    }, [detailId, getNextSearchParams, location.state, setSearchParams])

    useEffect(() => {
        if (detailId == null) openedFromGridRef.current = false
    }, [detailId])

    const currentIndex = useMemo(
        () => (detailId != null ? items.findIndex((i) => i.id === detailId) : -1),
        [detailId, items],
    )

    return { detailId, currentIndex, openDetail, closeDetail, closeDetailWithoutHistory, closeDetailForNavigation, setActiveDetail }
}
