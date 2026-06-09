import { HashRouter, Routes, Route, Navigate } from "react-router-dom"
import { lazy, Suspense, useEffect } from "react"
import type { ReactNode } from "react"
import { useAuthStore } from "@/stores/auth"
import AppLayout from "@/layouts/app-layout"
import LoginPage from "@/pages/login"
import { ToastViewport } from "@/components/ui/toast"
import { Spinner } from "@/components/ui/spinner"

// Secondary pages are lazy-loaded — they're only reachable via overflow menus,
// so the main Library + Albums tabs can ship in a smaller initial bundle.
const DashboardPage = lazy(() => import("@/pages/dashboard"))
const SettingsPage = lazy(() => import("@/pages/settings"))
const ProfilePage = lazy(() => import("@/pages/profile"))
const TagsPage = lazy(() => import("@/pages/tags"))
const DuplicatesPage = lazy(() => import("@/pages/duplicates"))
const AdminUsersPage = lazy(() => import("@/pages/admin-users"))
const MapPage = lazy(() => import("@/pages/map"))

function PageLoading() {
    return <div className="flex h-screen items-center justify-center"><Spinner /></div>
}

function lazyRoute(node: ReactNode) {
    return <Suspense fallback={<PageLoading />}>{node}</Suspense>
}

function RequireAuth({ children }: { children: ReactNode }) {
    const token = useAuthStore((s) => s.token)
    const user = useAuthStore((s) => s.user)
    const fetchUser = useAuthStore((s) => s.fetchUser)
    useEffect(() => {
        if (token && !user) void fetchUser()
    }, [fetchUser, token, user])

    if (!token) return <Navigate to="/login" replace />
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
                        <Route path="/dashboard" element={lazyRoute(<DashboardPage />)} />
                        <Route path="/map" element={lazyRoute(<MapPage />)} />
                        <Route path="/settings" element={lazyRoute(<SettingsPage />)} />
                        <Route path="/profile" element={lazyRoute(<ProfilePage />)} />
                        <Route path="/tags" element={lazyRoute(<TagsPage />)} />
                        <Route path="/duplicates" element={lazyRoute(<DuplicatesPage />)} />
                        <Route path="/admin/users" element={lazyRoute(<AdminUsersPage />)} />
                    </Route>
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </HashRouter>
            <ToastViewport />
        </>
    )
}
