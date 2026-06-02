import { Calendar, Camera, MapPin, Sparkles, Tag, type LucideIcon } from "lucide-react"

import type { AlbumItem, SectionDef, SectionId, SmartAlbum, SmartAlbumsResponse } from "@/api/types"
import { resolveIcon } from "@/lib/icons"

type AlbumSectionKey = Exclude<keyof SmartAlbumsResponse, "library">

interface SectionConfig {
    id: SectionId
    key: AlbumSectionKey
    icon: LucideIcon
    title: string
    previewCount: number
}

const SECTION_CONFIG: SectionConfig[] = [
    { id: "tags", key: "tags", icon: Tag, title: "Tags", previewCount: 8 },
    { id: "cameras", key: "cameras", icon: Camera, title: "Cameras", previewCount: 6 },
    { id: "festivals", key: "festivals", icon: Sparkles, title: "Festivals", previewCount: 8 },
    { id: "years", key: "years", icon: Calendar, title: "Years", previewCount: 9 },
    { id: "places", key: "places", icon: MapPin, title: "Places", previewCount: 6 },
]

export type OpenAlbum = (filters: Record<string, unknown>, label?: string) => void

export function toAlbumItem(album: SmartAlbum, openAlbum: OpenAlbum): AlbumItem {
    return {
        key: album.key,
        icon: resolveIcon(album.icon),
        title: album.title,
        subtitle: album.subtitle,
        count: album.count,
        coverId: album.cover_id,
        onClick: () => openAlbum(album.filters, album.title),
        color: album.color,
        searchText: album.search_text || album.title,
    }
}

export function buildAlbumItems(data: SmartAlbumsResponse | null, openAlbum: OpenAlbum) {
    const libraryItems = (data?.library ?? []).map((album) => toAlbumItem(album, openAlbum))
    const sections: SectionDef[] = SECTION_CONFIG
        .map(({ key, ...section }) => ({
            ...section,
            items: (data?.[key] ?? []).map((album) => toAlbumItem(album, openAlbum)),
        }))
        .filter((section) => section.items.length > 0)

    return { libraryItems, sections }
}
