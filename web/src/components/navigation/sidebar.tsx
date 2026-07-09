import { NavLink } from "react-router-dom"
import { sidebarNavSections, type NavigationItem } from "@/components/navigation/nav-items"
import { NotificationCenterButton } from "@/components/ui/notifications"
import { cn } from "@/lib/utils"

function SidebarLink({ item }: { item: NavigationItem }) {
    const Icon = item.icon

    return (
        <NavLink
            to={item.to}
            end={item.to === "/"}
            aria-label={item.label}
            className={({ isActive }) =>
                cn(
                    "group flex h-11 items-center justify-center gap-3 rounded-2xl px-3 text-sm font-medium transition-colors sm:justify-start",
                    isActive
                        ? "bg-primary/15 text-primary"
                        : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
                )
            }
        >
            <Icon className="h-5 w-5 shrink-0" strokeWidth={2.15} />
            <span className="hidden truncate sm:block">{item.label}</span>
        </NavLink>
    )
}

export function AppSidebar() {
    return (
        <aside
            className="material-thick flex h-screen w-[4.75rem] shrink-0 flex-col border-r border-border/70 sm:w-64"
            style={{
                paddingTop: "env(safe-area-inset-top, 0px)",
                paddingBottom: "env(safe-area-inset-bottom, 0px)",
            }}
        >
            <div className="flex h-16 items-center justify-center gap-3 px-3 sm:justify-start sm:px-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary text-sm font-bold text-primary-foreground shadow-lg shadow-primary/20">
                    MM
                </div>
                <div className="hidden min-w-0 sm:block">
                    <p className="truncate text-[15px] font-semibold leading-tight">LiteMM</p>
                    <p className="truncate text-[11px] font-medium text-muted-foreground/70">Media manager</p>
                </div>
            </div>

            <nav className="flex-1 space-y-5 overflow-y-auto px-2 pb-3 pt-2 sm:px-3">
                {sidebarNavSections.map((section) => (
                    <div key={section.label} className="space-y-1">
                        <p className="hidden px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/45 sm:block">
                            {section.label}
                        </p>
                        {section.items.map((item) => (
                            <SidebarLink key={item.to} item={item} />
                        ))}
                    </div>
                ))}
            </nav>

            <div className="border-t border-border/70 px-2 py-3 sm:px-3">
                <NotificationCenterButton />
            </div>
        </aside>
    )
}
