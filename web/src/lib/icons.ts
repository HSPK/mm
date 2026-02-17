import {
    Images,
    Camera,
    MapPin,
    Calendar,
    HelpCircle,
    Trash2,
    Star,
    Film,
    Image,
    Tag,
    Sparkles,
    type LucideIcon,
} from "lucide-react"

/** Map icon string names from backend to LucideIcon components */
const ICON_MAP: Record<string, LucideIcon> = {
    images: Images,
    image: Image,
    film: Film,
    star: Star,
    "trash-2": Trash2,
    tag: Tag,
    camera: Camera,
    sparkles: Sparkles,
    calendar: Calendar,
    "help-circle": HelpCircle,
    "map-pin": MapPin,
}

export function resolveIcon(name?: string): LucideIcon {
    return (name && ICON_MAP[name]) || Images
}
