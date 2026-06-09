import {
    Calendar,
    Camera,
    Film,
    HelpCircle,
    Image,
    Images,
    MapPin,
    Sparkles,
    Star,
    Tag,
    Trash2,
    type LucideIcon,
} from "lucide-react"

const registry = new Map<string, LucideIcon>()

export function registerIcon(name: string, icon: LucideIcon): void {
    registry.set(name, icon)
}

export function resolveIcon(name?: string): LucideIcon {
    if (name) {
        const found = registry.get(name)
        if (found) return found
    }
    return Images
}

// Built-in seed registry. Backend currently only emits these names; add new
// ones by calling `registerIcon` near the consumer (e.g. albums page) rather
// than editing this list.
const seed: Record<string, LucideIcon> = {
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

for (const [name, icon] of Object.entries(seed)) {
    registerIcon(name, icon)
}
