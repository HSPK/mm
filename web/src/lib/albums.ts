import { Calendar, Camera, MapPin, Sparkles, Tag, type LucideIcon } from "lucide-react"

import type {
    AlbumItem,
    SectionDef,
    SectionId,
    SmartAlbum,
    SmartAlbumsResponse,
} from "@/api/types"
import { resolveIcon } from "@/lib/icons"

export type AlbumSectionKey = Exclude<keyof SmartAlbumsResponse, "library">

export interface SectionConfig {
    id: SectionId
    key: AlbumSectionKey
    icon: LucideIcon
    title: string
    previewCount: number
}

export type OpenAlbum = (filters: Record<string, unknown>, label?: string) => void

const sections: SectionConfig[] = [
    { id: "tags", key: "tags", icon: Tag, title: "Tags", previewCount: 8 },
    { id: "cameras", key: "cameras", icon: Camera, title: "Cameras", previewCount: 6 },
    { id: "festivals", key: "festivals", icon: Sparkles, title: "Festivals", previewCount: 8 },
    { id: "years", key: "years", icon: Calendar, title: "Years", previewCount: 9 },
    { id: "places", key: "places", icon: MapPin, title: "Places", previewCount: 6 },
]

export function registerAlbumSection(config: SectionConfig): void {
    const existing = sections.findIndex((s) => s.id === config.id)
    if (existing >= 0) sections[existing] = config
    else sections.push(config)
}

export function getAlbumSections(): readonly SectionConfig[] {
    return sections
}

// Pure transform — no click wiring. Callers attach `onClick` via `bindAlbumItem`.
export function toAlbumItemPartial(album: SmartAlbum): Omit<AlbumItem, "onClick"> {
    return {
        key: album.key,
        icon: resolveIcon(album.icon ?? undefined),
        title: album.title,
        subtitle: album.subtitle ?? undefined,
        count: album.count ?? undefined,
        coverId: album.cover_id ?? undefined,
        color: album.color ?? undefined,
        searchText: album.search_text || album.title,
    }
}

export function bindAlbumItem(album: SmartAlbum, openAlbum: OpenAlbum): AlbumItem {
    return {
        ...toAlbumItemPartial(album),
        onClick: () => openAlbum(album.filters ?? {}, album.title),
    }
}

export function buildAlbumItems(data: SmartAlbumsResponse | null, openAlbum: OpenAlbum) {
    const libraryItems = (data?.library ?? []).map((album) => bindAlbumItem(album, openAlbum))
    const sectionDefs: SectionDef[] = sections
        .map(({ key, ...section }) => ({
            ...section,
            items: (data?.[key] ?? []).map((album) => bindAlbumItem(album, openAlbum)),
        }))
        .filter((section) => section.items.length > 0)

    return { libraryItems, sections: sectionDefs }
}
