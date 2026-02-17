import type { Media } from "@/api/types"

// ─── Date formatting ──────────────────────────────────────

/** Short date: "Jan 15, 2024" */
export function fmtDateShort(iso: string | null | undefined) {
    if (!iso) return ""
    const d = new Date(iso)
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

/** Format for month grouping: "2024 · 01" */
export function fmtMonthGroup(iso: string) {
    const d = new Date(iso)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, "0")
    return `${year} · ${month}`
}

/** Get month key for grouping: "2024-01" */
export function getMonthKey(iso: string) {
    const d = new Date(iso)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
}

/** Format for day grouping: "2024 · 01 · 15" */
export function fmtDayGroup(iso: string) {
    const d = new Date(iso)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, "0")
    const day = String(d.getDate()).padStart(2, "0")
    return `${year} · ${month} · ${day}`
}

/** Get day key for grouping: "2024-01-15" */
export function getDayKey(iso: string) {
    const d = new Date(iso)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
}

/** Format video duration: seconds → "1:05" */
export function fmtDuration(seconds: number | null | undefined) {
    if (!seconds) return null
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}:${s.toString().padStart(2, "0")}`
}

// ─── Date grouping ────────────────────────────────────────

export interface DateGroup {
    key: string
    label: string
    items: Media[]
}

/** Group items by month for date-sorted views */
export function groupByMonth(items: Media[]): DateGroup[] {
    const map = new Map<string, { label: string; items: Media[] }>()
    for (const item of items) {
        if (item.date_taken) {
            const key = getMonthKey(item.date_taken)
            const existing = map.get(key)
            if (existing) {
                existing.items.push(item)
            } else {
                map.set(key, { label: fmtMonthGroup(item.date_taken), items: [item] })
            }
        } else {
            const key = "no-date"
            const existing = map.get(key)
            if (existing) {
                existing.items.push(item)
            } else {
                map.set(key, { label: "No Date", items: [item] })
            }
        }
    }
    return Array.from(map.entries()).map(([key, { label, items }]) => ({ key, label, items }))
}

/** Group items by day for date-sorted views */
export function groupByDay(items: Media[]): DateGroup[] {
    const map = new Map<string, { label: string; items: Media[] }>()
    for (const item of items) {
        if (item.date_taken) {
            const key = getDayKey(item.date_taken)
            const existing = map.get(key)
            if (existing) {
                existing.items.push(item)
            } else {
                map.set(key, { label: fmtDayGroup(item.date_taken), items: [item] })
            }
        } else {
            const key = "no-date"
            const existing = map.get(key)
            if (existing) {
                existing.items.push(item)
            } else {
                map.set(key, { label: "No Date", items: [item] })
            }
        }
    }
    return Array.from(map.entries()).map(([key, { label, items }]) => ({ key, label, items }))
}
