import type { OrganizerCandidate, OrganizerItem } from "@/api/organizer"
import type { MediaRow } from "./organize-types"

export function actionKey(rows: MediaRow[]) {
    return rows.map((row) => row.key).sort().join("|")
}

export function toggleKey(keys: string[], key: string) {
    return keys.includes(key) ? keys.filter((item) => item !== key) : [...keys, key]
}

export function itemSelectionKey(item: OrganizerItem) {
    return item.item_uid ?? item.path
}

export function selectedCandidateMap(rows: MediaRow[]) {
    const result: Record<string, OrganizerCandidate> = {}
    for (const row of rows) {
        if (!row.candidate) continue
        for (const file of row.files) {
            result[itemSelectionKey(file)] = row.candidate
        }
    }

    return result
}

export function visibleRangeKeys(rows: MediaRow[], anchorKey: string | null, targetKey: string) {
    const targetIndex = rows.findIndex((row) => row.key === targetKey)
    const anchorIndex = anchorKey ? rows.findIndex((row) => row.key === anchorKey) : -1
    if (targetIndex < 0) return []
    if (anchorIndex < 0) return [targetKey]
    const start = Math.min(anchorIndex, targetIndex)
    const end = Math.max(anchorIndex, targetIndex)
    return rows.slice(start, end + 1).map((row) => row.key)
}
