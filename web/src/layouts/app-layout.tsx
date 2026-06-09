import { useRef, useState, useEffect, useLayoutEffect, useCallback, type TouchEvent } from "react"
import { Outlet, useLocation, useNavigate } from "react-router-dom"
import { cn } from "@/lib/utils"
import { FloatingSearchBar } from "@/components/floating-search-bar"
import { useMediaQueryStore } from "@/stores/media-query"
import { useSelectionStore } from "@/stores/media-selection"
import { useAlbumSectionStore } from "@/stores/album-section"
import { BottomBar } from "@/components/bottom-bar"
import { navItems } from "@/components/navigation/nav-items"
import MediaLibraryPage from "@/pages/media-library"
import AlbumsPage from "@/pages/albums"

const TAB_ROUTES = ["/", "/albums"]

function getActiveIndex(pathname: string) {
    const idx = navItems.findIndex((item) =>
        item.to === "/" ? pathname === "/" : pathname.startsWith(item.to),
    )
    return idx === -1 ? 0 : idx
}

function isInteractiveSwipeTarget(target: EventTarget | null) {
    return target instanceof HTMLElement
        && !!target.closest('button, a, input, textarea, select, [role="button"]')
}

export default function AppLayout() {
    const location = useLocation()
    const navRef = useRef<HTMLElement>(null)
    const itemRefs = useRef<(HTMLAnchorElement | null)[]>([])
    const [indicator, setIndicator] = useState({ left: 0, width: 0 })
    const isTabRoute = TAB_ROUTES.includes(location.pathname)
    const activeTabIndex = getActiveIndex(location.pathname)

    const libraryScrollRef = useRef<HTMLDivElement | null>(null)
    const [libraryScrollEl, setLibraryScrollEl] = useState<HTMLDivElement | null>(null)
    const [albumsScrollEl, setAlbumsScrollEl] = useState<HTMLDivElement | null>(null)
    const [outletScrollEl, setOutletScrollEl] = useState<HTMLDivElement | null>(null)
    const setLibraryScrollNode = useCallback((el: HTMLDivElement | null) => {
        libraryScrollRef.current = el
        setLibraryScrollEl(el)
    }, [])

    const { activeLabel: currentLabel, filters, resetFilters } = useMediaQueryStore()
    const { selectionMode, exitSelectionMode } = useSelectionStore()
    const isDeletedView = filters.deleted
    useEffect(() => {
        if (isTabRoute) return
        if (selectionMode) exitSelectionMode()
        if (isDeletedView) resetFilters()
    }, [exitSelectionMode, isDeletedView, isTabRoute, resetFilters, selectionMode])

    const prevLabelRef = useRef(currentLabel)
    useEffect(() => {
        if (currentLabel === prevLabelRef.current) return
        prevLabelRef.current = currentLabel
        if (currentLabel && libraryScrollRef.current) {
            libraryScrollRef.current.scrollTop = 0
        }
    }, [currentLabel])

    const activeScrollEl = isTabRoute
        ? (activeTabIndex === 0 ? libraryScrollEl : albumsScrollEl)
        : outletScrollEl

    const activeViewKey = isTabRoute ? `tab:${activeTabIndex}` : `route:${location.pathname}`
    const [navVisibility, setNavVisibility] = useState({ key: activeViewKey, visible: true })
    const navVisible = navVisibility.key === activeViewKey ? navVisibility.visible : true
    const lastScrollY = useRef(0)

    useEffect(() => {
        const el = activeScrollEl
        if (!el) return
        lastScrollY.current = el.scrollTop
        const handle = () => {
            const y = el.scrollTop
            setNavVisibility({ key: activeViewKey, visible: !(y > lastScrollY.current && y > 60) })
            lastScrollY.current = y
        }
        el.addEventListener("scroll", handle, { passive: true })
        return () => el.removeEventListener("scroll", handle)
    }, [activeScrollEl, activeViewKey])

    const updateIndicator = useCallback(() => {
        const el = itemRefs.current[activeTabIndex]
        const nav = navRef.current
        if (!el || !nav) return
        const navRect = nav.getBoundingClientRect()
        const elRect = el.getBoundingClientRect()
        setIndicator({
            left: elRect.left - navRect.left,
            width: elRect.width,
        })
    }, [activeTabIndex])

    useLayoutEffect(() => {
        updateIndicator()
    }, [updateIndicator])

    useEffect(() => {
        window.addEventListener("resize", updateIndicator)
        return () => window.removeEventListener("resize", updateIndicator)
    }, [updateIndicator])

    const navigate = useNavigate()
    const inAlbumView = currentLabel
    const albumSectionLabel = useAlbumSectionStore((s) => s.label)
    const mediaDetailOpen = new URLSearchParams(location.search).has("media")
    const swipeDisabled = !!inAlbumView || !!albumSectionLabel || mediaDetailOpen || selectionMode || isDeletedView
    const touchRef = useRef<{ startX: number; startY: number; startTime: number } | null>(null)
    const [swipeOffset, setSwipeOffset] = useState(0)
    const [swiping, setSwiping] = useState(false)

    const resetSwipe = useCallback(() => {
        touchRef.current = null
        setSwipeOffset(0)
        setSwiping(false)
    }, [])

    const handleTouchStart = useCallback((e: TouchEvent) => {
        if (swipeDisabled || isInteractiveSwipeTarget(e.target)) return
        const t = e.touches[0]
        touchRef.current = { startX: t.clientX, startY: t.clientY, startTime: Date.now() }
        setSwipeOffset(0)
        setSwiping(false)
    }, [swipeDisabled])

    const handleTouchMove = useCallback((e: TouchEvent) => {
        if (!touchRef.current) return
        const t = e.touches[0]
        const dx = t.clientX - touchRef.current.startX
        const dy = t.clientY - touchRef.current.startY

        if (!swiping && Math.abs(dy) > Math.abs(dx)) {
            resetSwipe()
            return
        }
        if (!swiping && Math.abs(dx) > 10) {
            setSwiping(true)
        }

        if (swiping || Math.abs(dx) > 10) {
            const maxLeft = activeTabIndex === 0 ? 0 : -Infinity
            const maxRight = activeTabIndex === navItems.length - 1 ? 0 : Infinity
            const clamped = Math.max(Math.min(dx, maxRight === Infinity ? dx : 0), maxLeft === -Infinity ? dx : 0)
            setSwipeOffset(
                (activeTabIndex === 0 && dx > 0) || (activeTabIndex === navItems.length - 1 && dx < 0)
                    ? dx * 0.2
                    : clamped,
            )
        }
    }, [activeTabIndex, resetSwipe, swiping])

    const handleTouchEnd = useCallback(() => {
        if (!touchRef.current || !swiping) {
            resetSwipe()
            return
        }

        const threshold = window.innerWidth * 0.25
        const velocity = Math.abs(swipeOffset) / (Date.now() - touchRef.current.startTime) * 1000
        if (swipeOffset > threshold || (swipeOffset > 30 && velocity > 500)) {
            if (activeTabIndex > 0) {
                navigate(navItems[activeTabIndex - 1].to)
            }
        } else if (swipeOffset < -threshold || (swipeOffset < -30 && velocity > 500)) {
            if (activeTabIndex < navItems.length - 1) {
                navigate(navItems[activeTabIndex + 1].to)
            }
        }

        resetSwipe()
    }, [activeTabIndex, navigate, resetSwipe, swipeOffset, swiping])

    const hasFilterTags = !!(currentLabel || isDeletedView ||
        filters.type || filters.camera ||
        filters.date_from || filters.date_to ||
        filters.min_rating ||
        (filters.lat != null && filters.lon != null) ||
        filters.search
    )
    const hasAlbumSectionTags = !!albumSectionLabel

    return (
        <div className="flex h-screen flex-col overflow-hidden bg-background">
            {isTabRoute && <FloatingSearchBar scrollContainer={activeScrollEl} />}

            <div className="flex-1 relative overflow-hidden">
                {isTabRoute && (
                    <div
                        className="absolute inset-0 flex"
                        style={{
                            transform: `translateX(calc(${-activeTabIndex * 100}% + ${swiping ? swipeOffset : 0}px))`,
                            transition: swiping ? "none" : "transform 300ms ease",
                            willChange: "transform",
                        }}
                        onTouchStart={handleTouchStart}
                        onTouchMove={handleTouchMove}
                        onTouchEnd={handleTouchEnd}
                        onTouchCancel={resetSwipe}
                    >
                        <div
                            ref={setLibraryScrollNode}
                            className={cn("w-full h-full shrink-0 overflow-y-auto", hasFilterTags ? "pt-[5.5rem]" : "pt-16")}
                            aria-hidden={activeTabIndex !== 0}
                            inert={activeTabIndex === 0 ? undefined : true}
                        >
                            <MediaLibraryPage />
                        </div>
                        <div
                            ref={setAlbumsScrollEl}
                            className={cn("w-full h-full shrink-0 overflow-y-auto", hasAlbumSectionTags ? "pt-[5.5rem]" : "pt-16")}
                            aria-hidden={activeTabIndex !== 1}
                            inert={activeTabIndex === 1 ? undefined : true}
                        >
                            <AlbumsPage />
                        </div>
                    </div>
                )}

                {!isTabRoute && (
                    <div
                        ref={setOutletScrollEl}
                        className="absolute inset-0 overflow-y-auto bg-background z-10"
                    >
                        <Outlet />
                    </div>
                )}
            </div>

            <BottomBar
                isTabRoute={isTabRoute}
                navVisible={navVisible}
                navRef={navRef}
                itemRefs={itemRefs}
                indicator={indicator}
            />
        </div>
    )
}
