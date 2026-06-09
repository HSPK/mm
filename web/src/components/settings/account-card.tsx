import { LogOut } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuthStore } from "@/stores/auth"
import { useLogoutRedirect } from "@/hooks/use-logout-redirect"
import { getUserDisplayName, getUserInitial } from "@/lib/user"

export function AccountCard() {
    const user = useAuthStore((s) => s.user)
    const handleLogout = useLogoutRedirect()
    const initial = getUserInitial(user)

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">Account</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/15 text-lg font-bold text-primary border border-primary/20">
                        {initial}
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold truncate">{getUserDisplayName(user)}</p>
                        {user?.display_name && user?.username && (
                            <p className="text-xs text-muted-foreground truncate">@{user.username}</p>
                        )}
                    </div>
                </div>
                <div className="pt-2 border-t border-border">
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-2 text-sm text-destructive hover:text-destructive/80 transition-colors"
                    >
                        <LogOut className="h-4 w-4" />
                        Sign Out
                    </button>
                </div>
            </CardContent>
        </Card>
    )
}
