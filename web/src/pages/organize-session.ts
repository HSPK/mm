import type { OrganizerKind, OrganizerKindSession, OrganizerSessionState } from "./organize-types"

export const ORGANIZER_SESSION_KEY = "mm-organizer-view-v5"

export function loadSession(): OrganizerSessionState {
    if (typeof localStorage === "undefined") return emptySession()
    const raw = localStorage.getItem(ORGANIZER_SESSION_KEY)
    if (!raw) return emptySession()
    try {
        const parsed = JSON.parse(raw) as {
            activeKind?: unknown
            sessions?: Partial<Record<OrganizerKind, Pick<OrganizerKindSession, "recursive" | "source" | "query" | "order">>>
        }
        return {
            activeKind: isOrganizerKind(parsed.activeKind) ? parsed.activeKind : "movies",
            sessions: {
                movies: restoreKindSession(parsed.sessions?.movies),
                tv: restoreKindSession(parsed.sessions?.tv),
                music: restoreKindSession(parsed.sessions?.music),
            },
        }
    } catch {
        return emptySession()
    }
}

export function persistedViewState(state: OrganizerSessionState) {
    return {
        activeKind: state.activeKind,
        sessions: {
            movies: pickPersistedKindState(state.sessions.movies),
            tv: pickPersistedKindState(state.sessions.tv),
            music: pickPersistedKindState(state.sessions.music),
        },
    }
}

export function emptyKindSession(): OrganizerKindSession {
    return {
        recursive: true,
        source: "",
        scanned: false,
        items: [],
        matches: [],
        selectedCandidates: {},
        selectedKey: null,
        selectedKeys: [],
        renamePlan: null,
        renamePlanKey: null,
    }
}

function emptySession(): OrganizerSessionState {
    return {
        activeKind: "movies",
        sessions: {
            movies: emptyKindSession(),
            tv: emptyKindSession(),
            music: emptyKindSession(),
        },
    }
}

function pickPersistedKindState(session: OrganizerKindSession) {
    return {
        recursive: session.recursive,
        source: session.source,
        query: session.query,
        order: session.order,
    }
}

function restoreKindSession(saved?: Pick<OrganizerKindSession, "recursive" | "source" | "query" | "order">) {
    return {
        ...emptyKindSession(),
        recursive: saved?.recursive ?? true,
        source: saved?.source ?? "",
        query: saved?.query ?? "",
        order: saved?.order ?? "name",
    }
}

function isOrganizerKind(value: unknown): value is OrganizerKind {
    return value === "movies" || value === "tv" || value === "music"
}
