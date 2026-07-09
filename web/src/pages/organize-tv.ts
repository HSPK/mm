import type { OrganizerItem } from "@/api/organizer"

export function tvSeriesTitle(item: OrganizerItem) {
    const metadataTitle = item.metadata_show_title?.trim()
    if (metadataTitle) return metadataTitle
    return tvSeriesDirectoryTitle(item.path) || item.title || "Untitled"
}

function tvSeriesDirectoryTitle(path: string) {
    const parts = path.split(/[\\/]/)
    parts.pop()
    const last = parts.at(-1) ?? ""
    if (/^(?:s(?:eason)?|series)\s*\d{1,3}$/i.test(last) || /^第\s*\d{1,3}\s*季$/.test(last)) {
        parts.pop()
    }
    return parts.at(-1) ?? ""
}
