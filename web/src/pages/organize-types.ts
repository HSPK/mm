import type {
    OrganizerCandidate,
    OrganizerItem,
    OrganizerMatchResult,
    OrganizerRenamePlan,
} from "@/api/organizer"

export type OrganizerKind = "movies" | "tv" | "music"
export type StatusValue = "yes" | "partial" | "no" | "na"
export type ScrapeTarget = "missing" | "current" | "missing-metadata" | "missing-lyrics"

export interface ScrapeApplyOptions {
    missingOnly: boolean
    sequentialRows?: boolean
    language?: string
}

export interface MetadataEditValues {
    title: string
    originalTitle: string
    year: number | null
    rating: number | null
    premiered: string
    certification: string
    runtime: number | null
    genres: string
    status: string
    studios: string
    countries: string
    tagline: string
    plot: string
    tags: string
    cast: string
    writeNfo: boolean
}

export interface OrganizerKindSession {
    recursive: boolean
    source: string
    query?: string
    order?: "name" | "year" | "incomplete"
    scanned: boolean
    items: OrganizerItem[]
    matches: OrganizerMatchResult[]
    selectedCandidates: Record<string, OrganizerCandidate>
    selectedKey: string | null
    selectedKeys: string[]
    renamePlan: OrganizerRenamePlan | null
    renamePlanKey: string | null
}

export interface OrganizerSessionState {
    activeKind: OrganizerKind
    sessions: Record<OrganizerKind, OrganizerKindSession>
}

export interface MediaRow {
    key: string
    kind: OrganizerKind
    title: string
    subtitle: string
    depth: number
    expandable: boolean
    expanded: boolean
    season?: number | null
    track?: number | null
    year: number | null
    rating: number | null
    ratingSource: string
    isNew: boolean
    metadata: StatusValue
    images: StatusValue
    subtitles: StatusValue
    lyrics: StatusValue
    files: OrganizerItem[]
    candidate: OrganizerCandidate | null
    candidates: OrganizerCandidate[]
}
