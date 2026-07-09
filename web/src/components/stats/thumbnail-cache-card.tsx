import { useCallback, useEffect, useState } from "react"
import { Film, Image, RefreshCw, WandSparkles } from "lucide-react"
import { libraryRepo, type ThumbnailStatus, type ThumbnailTypeStatus } from "@/api/library"
import { jobsRepo, type Job } from "@/api/jobs"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { formatBytes } from "@/lib/format"
import { notify } from "@/stores/notifications"

export function ThumbnailCacheCard() {
    const [status, setStatus] = useState<ThumbnailStatus | null>(null)
    const [loading, setLoading] = useState<string | null>(null)
    const [statusText, setStatusText] = useState<{ state: "idle" | "done" | "error"; text?: string }>({ state: "idle" })

    const load = useCallback(async () => {
        try {
            setStatus(await libraryRepo.getThumbnailStatus())
        } catch (err) {
            setStatusText({
                state: "error",
                text: err instanceof Error ? err.message : "Could not load thumbnail status",
            })
        }
    }, [])

    useEffect(() => {
        const id = window.setTimeout(() => { void load() }, 0)
        return () => window.clearTimeout(id)
    }, [load])

    const build = async (mode: "missing" | "failed") => {
        setLoading(mode)
        setStatusText({ state: "idle" })
        const notificationId = notify.task("Thumbnails queued", mode === "failed" ? "Regenerating failed thumbnails" : "Generating missing thumbnails")
        try {
            const job = await jobsRepo.createThumbnailJob({
                videosOnly: mode === "failed",
                failedOnly: mode === "failed",
                force: mode === "failed",
            })
            const result = await pollJob(job.id, notificationId)
            if (result.status === "error") throw new Error(result.error || result.message)
            setStatusText({ state: "done", text: result.message })
            await load()
        } catch (err) {
            notify.update(notificationId, {
                kind: "error",
                status: "error",
                title: "Thumbnails failed",
                message: err instanceof Error ? err.message : "Thumbnail build failed",
                progress: 100,
            })
            setStatusText({
                state: "error",
                text: err instanceof Error ? err.message : "Thumbnail build failed",
            })
        } finally {
            setLoading(null)
        }
    }
    const imageStats = status?.by_type.find((item) => item.media_type === "photo")
    const videoStats = status?.by_type.find((item) => item.media_type === "video")

    return (
        <Card>
            <CardContent className="space-y-4 pt-5">
                <div className="flex items-start gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-primary/15 text-primary">
                        <Film className="h-4 w-4" />
                    </div>
                    <div>
                        <h3 className="text-[15px] font-semibold">Thumbnail cache</h3>
                        <p className="mt-0.5 text-[13px] text-muted-foreground">
                            Image and video thumbnails are generated server-side and cached on disk.
                        </p>
                    </div>
                </div>

                <div className="grid gap-2 sm:grid-cols-4">
                    <Stat label="ffmpeg" value={status?.ffmpeg_available ? "Available" : "Missing"} />
                    <Stat label="Cached files" value={(status?.file_count ?? 0).toLocaleString()} />
                    <Stat label="Failed" value={(status?.failed_count ?? 0).toLocaleString()} danger={(status?.failed_count ?? 0) > 0} />
                    <Stat label="Cache size" value={formatBytes(status?.total_size ?? 0)} />
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                    <TypeStatsCard
                        icon={Image}
                        title="Images"
                        stats={imageStats}
                    />
                    <TypeStatsCard
                        icon={Film}
                        title="Videos"
                        stats={videoStats}
                    />
                </div>

                <p className="truncate text-[12px] text-muted-foreground">
                    Cache: <span className="font-mono text-foreground/70">{status?.cache_dir ?? "..."}</span>
                </p>

                {!status?.ffmpeg_available && (
                    <p className="rounded-2xl bg-destructive/10 px-3 py-2 text-[13px] text-destructive">
                        ffmpeg is not installed. Video thumbnail generation is disabled until ffmpeg is available.
                    </p>
                )}

                <div className="flex flex-wrap justify-end gap-2">
                    <ActionStatus state={statusText.state} text={statusText.text} />
                    <Button
                        size="sm"
                        variant="tinted"
                        disabled={!status}
                        loading={loading === "missing"}
                        onClick={() => void build("missing")}
                    >
                        <WandSparkles className="h-4 w-4" />
                        Generate missing thumbnails
                    </Button>
                    <Button
                        size="sm"
                        variant="plain"
                        disabled={!status?.ffmpeg_available || (status?.failed_count ?? 0) === 0}
                        loading={loading === "failed"}
                        onClick={() => void build("failed")}
                    >
                        <RefreshCw className="h-4 w-4" />
                        Regenerate failed thumbnails
                    </Button>
                </div>
            </CardContent>
        </Card>
    )
}

async function pollJob(jobId: string, notificationId: number): Promise<Job> {
    while (true) {
        const job = await jobsRepo.job(jobId)
        notify.update(notificationId, {
            kind: job.status === "error" ? "error" : job.status === "done" ? "success" : "task",
            status: job.status === "error" ? "error" : job.status === "done" ? "done" : "active",
            jobId: job.id,
            title: job.title,
            message: job.message,
            detail: job.detail,
            progress: job.progress,
        })
        if (job.status === "done" || job.status === "error") return job
        await new Promise((resolve) => window.setTimeout(resolve, 1000))
    }
}

function TypeStatsCard({
    icon: Icon,
    title,
    stats,
}: {
    icon: typeof Image
    title: string
    stats?: ThumbnailTypeStatus
}) {
    const cached = stats?.cached_files ?? 0
    const expected = stats?.expected_files ?? 0
    const pct = expected > 0 ? Math.round(cached / expected * 100) : 0
    return (
        <div className="rounded-3xl bg-secondary/35 p-4">
            <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-background text-primary">
                    <Icon className="h-4 w-4" />
                </div>
                <div>
                    <p className="text-sm font-semibold">{title}</p>
                    <p className="text-[12px] text-muted-foreground">
                        {(stats?.media_count ?? 0).toLocaleString()} media file(s)
                    </p>
                </div>
            </div>
            <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-background">
                <div
                    className="h-full rounded-full bg-primary transition-[width]"
                    style={{ width: `${pct}%` }}
                />
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-[12px]">
                <MiniStat label="Cached" value={`${cached.toLocaleString()}/${expected.toLocaleString()}`} />
                <MiniStat label="Ready" value={`${pct}%`} />
                <MiniStat
                    label="Failed"
                    value={(stats?.failed_count ?? 0).toLocaleString()}
                    danger={(stats?.failed_count ?? 0) > 0}
                />
            </div>
        </div>
    )
}

function ActionStatus({ state, text }: { state: "idle" | "done" | "error"; text?: string }) {
    if (state === "idle") return null
    return (
        <span
            title={text}
            className={state === "error"
                ? "mr-auto self-center rounded-full bg-destructive/10 px-2.5 py-1 text-[11px] font-semibold text-destructive"
                : "mr-auto self-center rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary"
            }
        >
            {state === "error" ? "Failed" : "Done"}
        </span>
    )
}

function MiniStat({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
    return (
        <div>
            <p className="text-muted-foreground">{label}</p>
            <p className={danger ? "font-semibold text-destructive" : "font-semibold"}>{value}</p>
        </div>
    )
}

function Stat({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
    return (
        <div className="rounded-2xl bg-secondary/45 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
            <p className={danger ? "mt-1 font-semibold text-destructive" : "mt-1 font-semibold"}>
                {value}
            </p>
        </div>
    )
}
