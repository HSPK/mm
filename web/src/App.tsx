import { HashRouter, Routes, Route, Navigate } from "react-router-dom"
import { lazy, Suspense, useEffect } from "react"
import type { ReactNode } from "react"
import { useAuthStore } from "@/stores/auth"
import AppLayout from "@/layouts/app-layout"
import LoginPage from "@/pages/login"
import { NotificationViewport } from "@/components/ui/notifications"
import { Spinner } from "@/components/ui/spinner"

// Secondary pages are lazy-loaded — they're only reachable via overflow menus,
// so the main Library + Albums tabs can ship in a smaller initial bundle.
const DashboardPage = lazy(() => import("@/pages/dashboard"))
const SettingsPage = lazy(() => import("@/pages/settings"))
const AdminUsersPage = lazy(() => import("@/pages/admin-users"))
const MapPage = lazy(() => import("@/pages/map"))
const OrganizePage = lazy(() => import("@/pages/organize"))
const ImportPage = lazy(() => import("@/pages/import"))
const MoviesPage = lazy(() => import("@/pages/movies"))
const TvSeriesPage = lazy(() => import("@/pages/tv-series"))
const MusicPage = lazy(() => import("@/pages/music"))

function PageLoading() {
    return <div className="flex h-screen items-center justify-center"><Spinner /></div>
}

function lazyRoute(node: ReactNode) {
    return <Suspense fallback={<PageLoading />}>{node}</Suspense>
}

function RequireAuth({ children }: { children: ReactNode }) {
    const token = useAuthStore((s) => s.token)
    const user = useAuthStore((s) => s.user)
    const loading = useAuthStore((s) => s.loading)
    const fetchUser = useAuthStore((s) => s.fetchUser)
    useEffect(() => {
        if (token && !user) void fetchUser()
    }, [fetchUser, token, user])

    if (!token) return <Navigate to="/login" replace />
    if (loading || !user) return <PageLoading />
    return <>{children}</>
}

export default function App() {
    return (
        <>
            <HashRouter>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route
                        element={
                            <RequireAuth>
                                <AppLayout />
                            </RequireAuth>
                        }
                    >
                        <Route path="/" element={<></>} />
                        <Route path="/albums" element={<></>} />
                        <Route path="/movies" element={lazyRoute(<MoviesPage />)} />
                        <Route path="/tv" element={lazyRoute(<TvSeriesPage />)} />
                        <Route path="/music" element={lazyRoute(<MusicPage />)} />
                        <Route path="/dashboard" element={lazyRoute(<DashboardPage />)} />
                        <Route path="/map" element={lazyRoute(<MapPage />)} />
                        <Route path="/organize" element={lazyRoute(<OrganizePage />)} />
                        <Route path="/import" element={lazyRoute(<ImportPage />)} />
                        <Route path="/settings" element={lazyRoute(<SettingsPage />)} />
                        <Route path="/profile" element={<Navigate to="/settings?section=account" replace />} />
                        <Route path="/admin/users" element={lazyRoute(<AdminUsersPage />)} />
                    </Route>
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </HashRouter>
            <NotificationViewport />
        </>
    )
}
