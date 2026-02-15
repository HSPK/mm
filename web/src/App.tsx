import { HashRouter, Routes, Route, Navigate } from "react-router-dom"
import { useAuthStore } from "@/stores/auth"
import AppLayout from "@/layouts/app-layout"
import LoginPage from "@/pages/login"
import DashboardPage from "@/pages/dashboard"
import SettingsPage from "@/pages/settings"
import ProfilePage from "@/pages/profile"
import type { ReactNode } from "react"

function RequireAuth({ children }: { children: ReactNode }) {
    const token = useAuthStore((s) => s.token)
    if (!token) return <Navigate to="/login" replace />
    return <>{children}</>
}

export default function App() {
    return (
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
                    <Route path="/dashboard" element={<DashboardPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/profile" element={<ProfilePage />} />
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </HashRouter>
    )
}
