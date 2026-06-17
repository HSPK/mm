import type { TimelineEntry } from "@/api/types"

export type TimelineBin = "day" | "month" | "year"

export const timelineBins: TimelineBin[] = ["day", "month", "year"]

export function aggregateTimelineEntries(
    entries: TimelineEntry[],
    bin: TimelineBin,
): TimelineEntry[] {
    const buckets = new Map<string, number>()
    for (const entry of entries) {
        if (!isValidTimelinePeriod(entry.period)) continue
        const period = timelinePeriodForBin(entry.period, bin)
        buckets.set(period, (buckets.get(period) ?? 0) + entry.count)
    }
    return [...buckets.entries()]
        .map(([period, count]) => ({ period, count }))
        .sort((a, b) => a.period.localeCompare(b.period))
}

export function timelinePeriodForBin(period: string, bin: TimelineBin): string {
    if (bin === "year") return period.slice(0, 4)
    if (bin === "month") return period.slice(0, 7)
    return period.slice(0, 10)
}

export function timelineWindowSize(bin: TimelineBin): number {
    if (bin === "year") return 24
    if (bin === "month") return 36
    return 60
}

export function isValidTimelinePeriod(period: string): boolean {
    return /^\d{4}-\d{2}-\d{2}$/.test(period) && period >= "1981-01-01"
}
