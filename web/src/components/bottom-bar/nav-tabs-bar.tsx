import { NavLink } from "react-router-dom"
import type { MutableRefObject, RefObject } from "react"
import { cn } from "@/lib/utils"
import { navItems } from "@/components/navigation/nav-items"

interface NavTabsBarProps {
    navRef: RefObject<HTMLElement | null>
    itemRefs: MutableRefObject<(HTMLAnchorElement | null)[]>
    indicator: { left: number; width: number }
}

export function NavTabsBar({ navRef, itemRefs, indicator }: NavTabsBarProps) {
    return (
        <nav
            ref={navRef}
            className="relative flex items-center gap-1 px-1.5 py-1.5 material-thick rounded-full elevation-3 border border-border/60"
        >
            <div
                className="absolute top-1.5 h-[calc(100%-0.75rem)] rounded-full bg-primary/15 transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]"
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
                                : "text-muted-foreground/60 hover:text-foreground/80",
                        )
                    }
                >
                    <item.icon className="h-[1.15rem] w-[1.15rem]" strokeWidth={2.25} />
                    <span>{item.label}</span>
                </NavLink>
            ))}
        </nav>
    )
}
