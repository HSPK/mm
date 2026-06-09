import { LayoutDashboard, LogOut, Settings, ShieldCheck } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { useAuthStore } from "@/stores/auth"
import { useMediaQueryStore } from "@/stores/media-query"
import { ListGroup, ListPage, ListRow } from "@/components/ui/list"
import { PageHeader } from "@/components/ui/page-header"
import { useLogoutRedirect } from "@/hooks/use-logout-redirect"
import { getUserDisplayName, getUserInitial } from "@/lib/user"

export default function ProfilePage() {
    const navigate = useNavigate()
    const user = useAuthStore((s) => s.user)
    const total = useMediaQueryStore((s) => s.total)
    const handleLogout = useLogoutRedirect()
    const initial = getUserInitial(user)

    return (
        <div className="pb-24 min-h-screen">
            <PageHeader title="Profile" back largeTitle />

            <ListPage>
                {/* Identity card */}
                <div className="bg-card rounded-2xl elevation-1 p-6 flex flex-col items-center text-center gap-3">
                    <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/70 text-white text-[34px] font-semibold elevation-2">
                        {initial}
                    </div>
                    <div>
                        <h2 className="text-[20px] font-semibold leading-tight">
                            {getUserDisplayName(user)}
                        </h2>
                        {user?.display_name && user?.username && (
                            <p className="text-[14px] text-muted-foreground mt-0.5">@{user.username}</p>
                        )}
                    </div>
                    {user?.is_admin && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-primary/12 px-3 py-1 text-[12px] font-medium text-primary">
                            <ShieldCheck className="h-3.5 w-3.5" strokeWidth={2.25} />
                            Administrator
                        </span>
                    )}
                </div>

                <ListGroup label="Library">
                    <ListRow
                        icon={<LayoutDashboard className="h-4 w-4" />}
                        label="Items"
                        trailing={<span className="font-mono tabular-nums">{total.toLocaleString()}</span>}
                    />
                </ListGroup>

                <ListGroup>
                    <ListRow
                        icon={{ icon: <Settings className="h-4 w-4" />, tint: "#8e8e93" }}
                        label="Settings"
                        chevron
                        onClick={() => navigate("/settings")}
                    />
                </ListGroup>

                <ListGroup>
                    <ListRow
                        icon={{ icon: <LogOut className="h-4 w-4" />, tint: "#ff3b30" }}
                        label="Sign out"
                        destructive
                        onClick={handleLogout}
                    />
                </ListGroup>
            </ListPage>
        </div>
    )
}
