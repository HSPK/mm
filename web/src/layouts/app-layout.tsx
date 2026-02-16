import { NavLink, Outlet, useLocation } from "react-router-dom"
import {
    Images,
    FolderHeart,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useRef, useState, useEffect, useLayoutEffect, useCallback } from "react"
import { FloatingSearchBar } from "@/components/floating-search-bar"
import MediaLibraryPage from "@/pages/media-library"
import AlbumsPage from "@/pages/albums"

const navItems = [
    { to: "/", label: "Library", icon: Images },
    { to: "/albums", label: "Albums", icon: FolderHeart },
]

const TAB_ROUTES = ["/", "/albums"]

function getActiveIndex(pathname: string) {
    // Exact match for "/", prefix match for others
    const idx = navItems.findIndex((item) =>
        item.to === "/" ? pathname === "/" : pathname.startsWith(item.to),
    )
    return idx === -1 ? 0 : idx
}

export default function AppLayout() {
    const location = useLocation()
    const navRef = useRef<HTMLElement>(null)
    const itemRefs = useRef<(HTMLAnchorElement | null)[]>([])
    const [indicator, setIndicator] = useState({ left: 0, width: 0 })
    const isTabRoute = TAB_ROUTES.includes(location.pathname)
    const activeTabIndex = getActiveIndex(location.pathname)

    // ─── Per-tab scroll containers (state for reactivity) ──
    const [libraryScrollEl, setLibraryScrollEl] = useState<HTMLDivElement | null>(null)
    const [albumsScrollEl, setAlbumsScrollEl] = useState<HTMLDivElement | null>(null)
    const [outletScrollEl, setOutletScrollEl] = useState<HTMLDivElement | null>(null)

    const activeScrollEl = isTabRoute
        ? (activeTabIndex === 0 ? libraryScrollEl : albumsScrollEl)
        : outletScrollEl

    // ─── Auto-hide both navs on scroll ─────────────────────
    const [navVisible, setNavVisible] = useState(true)
    const lastScrollY = useRef(0)

    useEffect(() => {
        const el = activeScrollEl
        if (!el) return
        lastScrollY.current = el.scrollTop
        setNavVisible(true)
        const handle = () => {
            const y = el.scrollTop
            if (y > lastScrollY.current && y > 60) {
                setNavVisible(false)
            } else {
                setNavVisible(true)
            }
            lastScrollY.current = y
        }
        el.addEventListener("scroll", handle, { passive: true })
        return () => el.removeEventListener("scroll", handle)
    }, [activeScrollEl])

    // ─── Nav indicator ─────────────────────────────────────
    const updateIndicator = useCallback(() => {
        const el = itemRefs.current[activeTabIndex]
        const nav = navRef.current
        if (el && nav) {
            const navRect = nav.getBoundingClientRect()
            const elRect = el.getBoundingClientRect()
            setIndicator({
                left: elRect.left - navRect.left,
                width: elRect.width,
            })
        }
    }, [activeTabIndex])

    useLayoutEffect(() => {
        updateIndicator()
    }, [updateIndicator])

    useEffect(() => {
        window.addEventListener("resize", updateIndicator)
        return () => window.removeEventListener("resize", updateIndicator)
    }, [updateIndicator])

    // ─── Tab transition styles ─────────────────────────────
    const getTabStyle = (tabIndex: number): React.CSSProperties => {
        if (!isTabRoute) {
            return { opacity: 0, visibility: 'hidden', pointerEvents: 'none' }
        }
        const isActive = activeTabIndex === tabIndex
        const direction = tabIndex < activeTabIndex ? -1 : 1
        if (isActive) {
            return {
                opacity: 1,
                transform: 'translateX(0)',
                visibility: 'visible',
                pointerEvents: 'auto',
                transition: 'opacity 300ms ease, transform 300ms ease, visibility 0s 0ms',
            }
        }
        return {
            opacity: 0,
            transform: `translateX(${direction * 1.5}rem)`,
            visibility: 'hidden',
            pointerEvents: 'none',
            transition: 'opacity 250ms ease, transform 250ms ease, visibility 0s 250ms',
        }
    }

    return (
        <div className="flex h-screen flex-col overflow-hidden bg-background">
            {/* Floating search bar — only on tab routes */}
            {isTabRoute && <FloatingSearchBar scrollContainer={activeScrollEl} />}

            {/* Content area — tabs always mounted, Outlet for non-tab routes */}
            <div className="flex-1 relative overflow-hidden">
                {/* Tab: Library */}
                <div
                    ref={setLibraryScrollEl}
                    className="absolute inset-0 overflow-y-auto pt-16"
                    style={getTabStyle(0)}
                >
                    <MediaLibraryPage />
                </div>

                {/* Tab: Albums */}
                <div
                    ref={setAlbumsScrollEl}
                    className="absolute inset-0 overflow-y-auto pt-16"
                    style={getTabStyle(1)}
                >
                    <AlbumsPage />
                </div>

                {/* Non-tab routes (dashboard, settings, profile) */}
                <div
                    ref={setOutletScrollEl}
                    className={cn(
                        "absolute inset-0 overflow-y-auto bg-background z-10",
                        isTabRoute && "invisible pointer-events-none",
                    )}
                >
                    <Outlet />
                </div>
            </div>

            {/* Floating bottom navigation — only on tab routes, auto-hides on scroll */}
            <div
                className={cn(
                    "fixed bottom-4 left-0 right-0 z-30 flex justify-center transition-transform duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)]",
                    isTabRoute && navVisible ? "translate-y-0" : "translate-y-[calc(100%+2rem)]",
                )}
                style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
            >
                <nav
                    ref={navRef}
                    className="relative flex items-center gap-1 px-2 py-2 bg-background/80 backdrop-blur-xl border border-border/60 shadow-2xl shadow-black/10 rounded-full"
                >
                    {/* Sliding active indicator */}
                    <div
                        className="absolute top-2 h-[calc(100%-1rem)] rounded-full bg-primary/12 transition-all duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)]"
                        style={{ left: indicator.left, width: indicator.width }}
                    />

                    {navItems.map((item, i) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            end={item.to === "/"}
                            ref={(el) => { itemRefs.current[i] = el }}
                            className={({ isActive }) =>
                                cn(
                                    "relative z-10 flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-full text-[10px] font-medium transition-colors duration-200",
                                    isActive
                                        ? "text-primary"
                                        : "text-muted-foreground/50 hover:text-foreground/70",
                                )
                            }
                        >
                            <item.icon className="h-[1.15rem] w-[1.15rem]" />
                            <span>{item.label}</span>
                        </NavLink>
                    ))}
                </nav>
            </div>
        </div>
    )
}
