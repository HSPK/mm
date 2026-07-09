import { useCallback, useEffect, useMemo, useState } from "react"
import { Camera, FileImage, Film, HardDrive, Images, RefreshCw, Tag } from "lucide-react"
import { statsRepo } from "@/api/stats"
import type { CameraStats, LibraryStats, TagStats, TimelineEntry } from "@/api/types"
import { Card, CardContent } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { Spinner } from "@/components/ui/spinner"
import { ThumbnailCacheCard } from "@/components/stats/thumbnail-cache-card"
import { formatBytes } from "@/lib/format"
import {
    aggregateTimelineEntries,
    timelineBins,
    timelineWindowSize,
    type TimelineBin,
} from "@/lib/timeline-bins"

export default function DashboardPage() {
    const [stats, setStats] = useState<LibraryStats | null>(null)
    const [timeline, setTimeline] = useState<TimelineEntry[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const load = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const [s, t] = await Promise.all([statsRepo.overview(), statsRepo.timeline()])
            setStats(s)
            setTimeline(t)
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load stats")
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        const id = window.setTimeout(() => { void load() }, 0)
        return () => window.clearTimeout(id)
    }, [load])

    return (
        <div>
            <PageHeader
                title="Stats"
                back
                actions={
                    <button
                        type="button"
                        onClick={() => void load()}
                        aria-label="Refresh"
                        disabled={loading}
                        className="flex items-center justify-center h-9 w-9 rounded-full hover:bg-secondary transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    </button>
                }
            />

            <div className="p-6 max-w-5xl mx-auto space-y-6">
                {!stats && loading && (
                    <div className="py-16 flex justify-center"><Spinner /></div>
                )}

                {!stats && error && (
                    <EmptyState
                        title="Couldn’t load stats"
                        description={error}
                        action={{ label: "Retry", onClick: () => void load(), variant: "primary" }}
                    />
                )}

                {stats && <DashboardBody stats={stats} timeline={timeline} />}
            </div>
        </div>
    )
}

function DashboardBody({ stats, timeline }: { stats: LibraryStats; timeline: TimelineEntry[] }) {
    const dist = stats.type_distribution
    const totalForBars = Math.max(1, dist.photo + dist.video + dist.audio)
    return (
        <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <SummaryCard icon={Images} label="Total" value={stats.total_files.toLocaleString()} color="text-primary" />
                <SummaryCard icon={HardDrive} label="Storage" value={formatBytes(stats.total_size)} color="text-emerald-500" />
                <SummaryCard icon={FileImage} label="Photos" value={dist.photo.toLocaleString()} color="text-blue-500" />
                <SummaryCard icon={Film} label="Videos" value={dist.video.toLocaleString()} color="text-orange-500" />
            </div>

            <Card>
                <CardContent className="pt-6 space-y-3">
                    <h2 className="text-sm font-semibold tracking-wide text-muted-foreground/80 uppercase">By type</h2>
                    <TypeBar label="Photos" count={dist.photo} total={totalForBars} color="bg-blue-500" />
                    <TypeBar label="Videos" count={dist.video} total={totalForBars} color="bg-orange-500" />
                    {dist.audio > 0 && (
                        <TypeBar label="Audio" count={dist.audio} total={totalForBars} color="bg-purple-500" />
                    )}
                </CardContent>
            </Card>

            <TimelineSection entries={timeline} />

            <ThumbnailCacheCard />

            {stats.cameras.length > 0 && (
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-2 mb-4">
                            <Camera className="h-4 w-4 text-muted-foreground/70" />
                            <h2 className="text-sm font-semibold tracking-wide text-muted-foreground/80 uppercase">Top cameras</h2>
                        </div>
                        <CameraList cameras={stats.cameras.slice(0, 12)} />
                    </CardContent>
                </Card>
            )}

            {stats.tags.length > 0 && (
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-2 mb-4">
                            <Tag className="h-4 w-4 text-muted-foreground/70" />
                            <h2 className="text-sm font-semibold tracking-wide text-muted-foreground/80 uppercase">Top tags</h2>
                        </div>
                        <TagCloud tags={stats.tags.slice(0, 30)} />
                    </CardContent>
                </Card>
            )}
        </>
    )
}

interface SummaryCardProps {
    icon: typeof Images
    label: string
    value: string
    color: string
}

function SummaryCard({ icon: Icon, label, value, color }: SummaryCardProps) {
    return (
        <Card>
            <CardContent className="pt-5 pb-4">
                <Icon className={`h-5 w-5 ${color}`} />
                <p className="text-xs uppercase tracking-wider text-muted-foreground/70 mt-2">{label}</p>
                <p className="text-xl font-semibold tabular-nums mt-0.5">{value}</p>
            </CardContent>
        </Card>
    )
}

function TypeBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
    const pct = Math.round((count / total) * 100)
    return (
        <div>
            <div className="flex items-baseline justify-between text-sm mb-1.5">
                <span className="text-foreground/80">{label}</span>
                <span className="text-muted-foreground tabular-nums">
                    {count.toLocaleString()} <span className="text-xs">({pct}%)</span>
                </span>
            </div>
            <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                <div className={`h-full ${color} transition-[width] duration-500`} style={{ width: `${pct}%` }} />
            </div>
        </div>
    )
}

function CameraList({ cameras }: { cameras: CameraStats[] }) {
    const max = Math.max(...cameras.map((c) => c.count), 1)
    return (
        <ul className="space-y-2">
            {cameras.map((cam) => {
                const name = [cam.make, cam.model].filter(Boolean).join(" ").trim() || "Unknown"
                const pct = (cam.count / max) * 100
                return (
                    <li key={`${cam.make}|${cam.model}`}>
                        <div className="flex justify-between text-sm mb-1">
                            <span className="truncate pr-3">{name}</span>
                            <span className="text-muted-foreground tabular-nums">{cam.count.toLocaleString()}</span>
                        </div>
                        <div className="h-1 rounded-full bg-secondary overflow-hidden">
                            <div className="h-full bg-primary/80" style={{ width: `${pct}%` }} />
                        </div>
                    </li>
                )
            })}
        </ul>
    )
}

function TagCloud({ tags }: { tags: TagStats[] }) {
    return (
        <div className="flex flex-wrap gap-2">
            {tags.map((tag) => {
                return (
                    <span
                        key={tag.name}
                        className="inline-flex items-center gap-1.5 rounded-full bg-secondary/60 px-2.5 py-1 text-xs font-medium text-foreground/85 transition-colors hover:bg-secondary"
                    >
                        <span className="max-w-40 truncate">{tag.name}</span>
                        <span className="text-[11px] text-muted-foreground tabular-nums">{tag.count}</span>
                    </span>
                )
            })}
        </div>
    )
}

function TimelineSection({ entries }: { entries: TimelineEntry[] }) {
    const [bin, setBin] = useState<TimelineBin>("month")
    const binned = useMemo(() => aggregateTimelineEntries(entries, bin), [bin, entries])
    if (binned.length === 0) return null

    return (
        <Card>
            <CardContent className="pt-6">
                <div className="mb-4 flex items-center justify-between gap-3">
                    <h2 className="text-sm font-semibold tracking-wide text-muted-foreground/80 uppercase">Timeline</h2>
                    <div className="inline-flex rounded-full bg-secondary/60 p-0.5">
                        {timelineBins.map((value) => (
                            <button
                                key={value}
                                type="button"
                                aria-pressed={bin === value}
                                onClick={() => setBin(value)}
                                className={`h-7 rounded-full px-3 text-xs font-medium capitalize transition-colors ${bin === value
                                    ? "bg-background text-foreground shadow-sm"
                                    : "text-muted-foreground hover:text-foreground"
                                }`}
                            >
                                {value}
                            </button>
                        ))}
                    </div>
                </div>
                <TimelineChart entries={binned} bin={bin} />
            </CardContent>
        </Card>
    )
}

function TimelineChart({ entries, bin }: { entries: TimelineEntry[]; bin: TimelineBin }) {
    if (entries.length === 0) return null
    const recent = entries.slice(-timelineWindowSize(bin))
    const max = Math.max(...recent.map((e) => e.count), 1)
    return (
        <div>
            <div className="flex items-end gap-1 h-32" role="img" aria-label="Media count per period">
                {recent.map((entry) => {
                    const h = (entry.count / max) * 100
                    const label = timelineHoverLabel(entry.period, bin)
                    return (
                        <div
                            key={entry.period}
                            className="relative flex h-full flex-1 items-end group min-w-0"
                            title={`${label}: ${entry.count.toLocaleString()}`}
                        >
                            <div
                                className="w-full bg-primary/80 hover:bg-primary rounded-t-sm transition-colors"
                                style={{ height: `${h}%`, minHeight: "3px" }}
                            />
                            <div className="absolute -top-12 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                                <span className="flex flex-col items-center gap-0.5 px-2 py-1 rounded bg-foreground text-background text-[10px] font-medium whitespace-nowrap tabular-nums shadow-lg">
                                    <span>{label}</span>
                                    <span className="opacity-75">{entry.count.toLocaleString()} items</span>
                                </span>
                            </div>
                        </div>
                    )
                })}
            </div>
            <div className="flex justify-between text-[10px] text-muted-foreground/60 mt-2 tabular-nums">
                <span>{recent[0]?.period ?? ""}</span>
                <span>{recent[recent.length - 1]?.period ?? ""}</span>
            </div>
        </div>
    )
}

function timelineHoverLabel(period: string, bin: TimelineBin): string {
    if (bin === "year") return `Year ${period}`
    if (bin === "month") return `Month ${period}`
    return `Day ${period}`
}
