import type { components } from "./schema"

type Schemas = components["schemas"]

// ─── Request bodies ──────────────────────────────────────
// Auto-synced from FastAPI via `bun run gen:api`.

export type LoginBody = Schemas["LoginBody"]
export type CreateAlbumBody = Schemas["CreateAlbumBody"]
export type AlbumMediaBody = Schemas["AlbumMediaBody"]
export type RatingBody = Schemas["RatingBody"]
export type TagsBody = Schemas["TagsBody"]
export type UpdateMetadataBody = Schemas["UpdateMetadataBody"]
export type BatchDeleteBody = Schemas["BatchDeleteBody"]
export type BatchTagBody = Schemas["BatchTagBody"]
export type BatchRatingBody = Schemas["BatchRatingBody"]
export type SwitchLibraryBody = Schemas["SwitchLibraryBody"]

// ─── Response shapes ─────────────────────────────────────
// All response models are typed by the server now (every route declares
// response_model=...). These aliases mean changing the wire format anywhere
// shows up as a TypeScript error here.

export type Media = Schemas["MediaBrief"]
export type MediaMetadata = Schemas["MediaMetadata"]
export type MediaTag = Schemas["MediaTag"]
export type MediaDetail = Schemas["MediaDetail"]
export type PaginatedMedia = Schemas["PaginatedMedia"]
export type RatingResponse = Schemas["RatingResponse"]
export type BatchAffected = Schemas["BatchAffected"]
export type StatusMessage = Schemas["StatusMessage"]

export type User = Schemas["UserSummary"]
export type LoginResponse = Schemas["LoginResponse"]
export type AuthStatus = Schemas["AuthStatus"]

export type AlbumSummary = Schemas["AlbumSummary"]
export type CreatedAlbum = Schemas["CreatedAlbum"]
export type AlbumActionResponse = Schemas["AlbumActionResponse"]

export type LibraryInfo = Schemas["LibraryInfo"]
export type SwitchLibraryResponse = Schemas["SwitchLibraryResponse"]

export type SmartAlbum = Schemas["SmartAlbumEntry"]
export type SmartAlbumsResponse = Schemas["SmartAlbumsResponse"]

export type CameraStats = Schemas["CameraStats"]
export type TagStats = Schemas["TagStats"]
export type LibraryStats = Schemas["LibraryStats"]
export type TimelineEntry = Schemas["TimelineEntry"]
export type TypeDistribution = Schemas["TypeDistribution"]
export type DuplicateGroup = Schemas["DuplicateGroup"]
export type GeoPoint = Schemas["GeoPoint"]

export type UserDetail = Schemas["UserDetail"]
export type SmartAlbumDefinition = Schemas["SmartAlbumDefinition"]
export type SmartAlbumResetResult = Schemas["SmartAlbumResetResult"]
export type StatusOk = Schemas["StatusOk"]

export type BatchMetadataBody = Schemas["BatchMetadataBody"]

// ─── Legacy token shape kept for compatibility ───────────
// Used by some auth flows that pre-date LoginResponse. Will be removed once
// all call sites use LoginResponse.token instead.
export interface Token {
    access_token: string
    token_type: string
}

// ─── Tag (compat with existing UI) ───────────────────────
// `Tag` is shaped like the /tags endpoint payload — alias of TagStats.
export type Tag = Schemas["TagStats"]

// ─── UI-only types (not wire payloads) ───────────────────
// These describe what the UI builds locally, not what the server sends.

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
