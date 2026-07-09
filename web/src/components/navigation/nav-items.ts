import {
    FolderHeart,
    Images,
    Film,
    Music,
    Settings,
    Tv,
    WandSparkles,
    type LucideIcon,
} from "lucide-react"

export interface NavigationItem {
    to: string
    label: string
    icon: LucideIcon
}

export const navItems: NavigationItem[] = [
    { to: "/", label: "Library", icon: Images },
    { to: "/albums", label: "Albums", icon: FolderHeart },
]

export const sidebarNavSections: { label: string; items: NavigationItem[] }[] = [
    {
        label: "Library",
        items: [
            ...navItems,
        ],
    },
    {
        label: "Media",
        items: [
            { to: "/movies", label: "Movies", icon: Film },
            { to: "/tv", label: "TV Series", icon: Tv },
            { to: "/music", label: "Music", icon: Music },
        ],
    },
    {
        label: "Tools",
        items: [
            { to: "/organize", label: "Organize", icon: WandSparkles },
            { to: "/settings", label: "Settings", icon: Settings },
        ],
    },
]
