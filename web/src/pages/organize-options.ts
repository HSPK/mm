import { Film, Music, Tv } from "lucide-react"
import type { OrganizerKind } from "./organize-types"

export const organizerKindOptions: Array<{
    kind: OrganizerKind
    label: string
    icon: typeof Film
}> = [
    { kind: "movies", label: "Movies", icon: Film },
    { kind: "tv", label: "TV Series", icon: Tv },
    { kind: "music", label: "Music", icon: Music },
]

export function optionForKind(kind: OrganizerKind) {
    return organizerKindOptions.find((option) => option.kind === kind)
        ?? organizerKindOptions[0]
}

export function folderOpenIcon(kind: OrganizerKind) {
    return optionForKind(kind).icon
}
