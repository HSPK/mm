import { useNavigate } from "react-router-dom"
import { useAuthStore } from "@/stores/auth"
import { LogOut, User } from "lucide-react"

export default function ProfilePage() {
    const navigate = useNavigate()
    const logout = useAuthStore((s) => s.logout)
    const user = useAuthStore((s) => s.user)

    const handleLogout = () => {
        logout()
        navigate("/login", { replace: true })
    }

    const initial = (user?.display_name ?? user?.username ?? "U")[0].toUpperCase()

    return (
        <div className="flex flex-col items-center px-6 pt-16 pb-32 space-y-8">
            {/* Avatar */}
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/15 text-3xl font-bold text-primary">
                {initial}
            </div>

            {/* User info */}
            <div className="text-center space-y-1">
                <h1 className="text-xl font-semibold">
                    {user?.display_name || user?.username}
                </h1>
                {user?.display_name && user?.username && (
                    <p className="text-sm text-muted-foreground">@{user.username}</p>
                )}
            </div>

            {/* Actions */}
            <div className="w-full max-w-sm space-y-3">
                <button
                    onClick={handleLogout}
                    className="flex w-full items-center justify-center gap-2 rounded-xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm font-medium text-destructive transition-colors hover:bg-destructive/20"
                >
                    <LogOut className="h-4 w-4" />
                    Logout
                </button>
            </div>
        </div>
    )
}
