export interface Media {
    id: number
    filename: string
    extension: string
    media_type: string
    file_size: number
    rating: number
    width?: number
    height?: number
    date_taken?: string | null
    camera_model?: string | null
    duration?: number | null
    gps_lat?: number | null
    gps_lon?: number | null
    location_label?: string | null
    location_city?: string | null
    location_country?: string | null
    deleted_at?: string | null
}

export interface MediaMetadata {
    date_taken: string | null
    camera_make: string | null
    camera_model: string | null
    lens_model: string | null
    focal_length: number | null
    aperture: number | null
    shutter_speed: string | null
    iso: number | null
    width: number | null
    height: number | null
    duration: number | null
    gps_lat: number | null
    gps_lon: number | null
    location_label?: string | null
    location_country?: string | null
    location_city?: string | null
    orientation: number | null
}

export interface MediaTag {
    name: string
    source: string
    confidence: number | null
}

export interface MediaDetail {
    id: number
    path: string
    filename: string
    extension: string
    media_type: string
    file_size: number
    file_hash: string
    rating: number
    scanned_at: string | null
    metadata: MediaMetadata | null
    tags: MediaTag[]
}

export interface PaginatedMedia {
    items: Media[]
    total: number
    page: number
    per_page: number
    pages: number
}

export interface Token {
    access_token: string
    token_type: string
}

export interface LoginBody {
    username: string
    password: string
}

export interface Tag {
    name: string
    count: number
}

export interface User {
    id: number
    username: string
    display_name: string
    is_admin: boolean
}

// ─── Smart Albums ─────────────────────────────────────────

export interface SmartAlbum {
    key: string
    title: string
    subtitle?: string
    count?: number
    cover_id?: number | null
    icon?: string
    color?: string
    filters: Record<string, unknown>
    search_text?: string
    festival_id?: string
}

export interface SmartAlbumsResponse {
    library: SmartAlbum[]
    tags: SmartAlbum[]
    cameras: SmartAlbum[]
    festivals: SmartAlbum[]
    years: SmartAlbum[]
    places: SmartAlbum[]
}

export type SectionId = "tags" | "cameras" | "festivals" | "years" | "places"

export interface AlbumItem {
    key: string
    icon: import("lucide-react").LucideIcon
    title: string
    subtitle?: string
    count?: number
    coverId?: number | null
    onClick: () => void
    color?: string
    searchText: string
}

export interface SectionDef {
    id: SectionId
    icon: import("lucide-react").LucideIcon
    title: string
    items: AlbumItem[]
    previewItems?: AlbumItem[]
    previewCount: number
}
