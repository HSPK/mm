import { useEffect, useMemo } from "react"
import { AlertCircle, Bell, CheckCircle2, Info, Loader2, X } from "lucide-react"
import { createPortal } from "react-dom"
import { jobsRepo, type Job } from "@/api/jobs"
import { notify, useNotificationStore, type AppNotification } from "@/stores/notifications"
import { cn } from "@/lib/utils"

const icons = {
    info: Info,
    success: CheckCircle2,
    error: AlertCircle,
    task: Loader2,
}

export function NotificationViewport() {
    const notifications = useNotificationStore((state) => state.notifications)
    const dismiss = useNotificationStore((state) => state.dismiss)
    const clearHistory = useNotificationStore((state) => state.clearHistory)
    const centerOpen = useNotificationStore((state) => state.centerOpen)
    const closeCenter = useNotificationStore((state) => state.closeCenter)

    useEffect(() => {
        void restoreActiveJobs()
    }, [])

    const cards = useMemo(
        () => notifications.filter((item) => !item.dismissed).slice(0, 3),
        [notifications],
    )

    if (typeof document === "undefined") return null

    return createPortal(
        <>
            <div className="pointer-events-none fixed bottom-4 right-4 z-[10030] flex w-[22rem] max-w-[calc(100vw-2rem)] flex-col items-end gap-2">
                {cards.map((notification) => (
                    <NotificationCard
                        key={notification.id}
                        notification={notification}
                        onDismiss={() => dismiss(notification.id)}
                    />
                ))}
            </div>

            {centerOpen && (
                <div className="fixed inset-0 z-[10040] flex items-center justify-center bg-black/40 p-4" onClick={closeCenter}>
                    <section
                        role="dialog"
                        aria-modal="true"
                        aria-label="Notification center"
                        onClick={(event) => event.stopPropagation()}
                        className="flex max-h-[78vh] w-full max-w-xl flex-col overflow-hidden rounded-3xl bg-background shadow-2xl"
                    >
                        <div className="flex items-center justify-between border-b border-border px-5 py-4">
                            <div>
                                <h2 className="text-lg font-bold">Notification center</h2>
                                <p className="text-sm text-muted-foreground">{notifications.length} notification(s)</p>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    onClick={clearHistory}
                                    className="rounded-full px-3 py-1.5 text-sm font-semibold text-muted-foreground hover:bg-secondary hover:text-foreground"
                                >
                                    Clear
                                </button>
                                <button
                                    type="button"
                                    onClick={closeCenter}
                                    className="flex h-9 w-9 items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
                                    aria-label="Close notification center"
                                >
                                    <X className="h-4 w-4" />
                                </button>
                            </div>
                        </div>
                        <div className="min-h-0 flex-1 overflow-y-auto p-3">
                            {notifications.length === 0 ? (
                                <div className="py-16 text-center text-sm text-muted-foreground">No notifications.</div>
                            ) : notifications.map((notification) => (
                                <NotificationHistoryRow key={notification.id} notification={notification} />
                            ))}
                        </div>
                    </section>
                </div>
            )}
        </>,
        document.body,
    )
}

async function restoreActiveJobs() {
    const restoredJobIds = new Set<string>()
    for (const notification of useNotificationStore.getState().notifications) {
        if (!notification.jobId || notification.status !== "active") continue
        restoredJobIds.add(notification.jobId)
        void pollJob(notification.jobId, notification.id)
    }
    const jobs = [
        ...(await jobsRepo.list(20, "queued").catch(() => [])),
        ...(await jobsRepo.list(20, "running").catch(() => [])),
        ...(await jobsRepo.list(20, "canceling").catch(() => [])),
    ]
    for (const job of jobs) {
        if (restoredJobIds.has(job.id)) continue
        const exists = useNotificationStore.getState().notifications.some((item) => item.jobId === job.id)
        if (exists) continue
        const id = notify.task(job.title || "Background job", job.message)
        notify.update(id, { jobId: job.id, detail: job.detail, progress: job.progress })
        void pollJob(job.id, id)
    }
}

async function pollJob(jobId: string, notificationId: number) {
    while (true) {
        const job = await jobsRepo.job(jobId).catch(() => null)
        if (!job) return
        updateNotificationFromJob(notificationId, job)
        if (["done", "error", "canceled"].includes(job.status)) return
        await new Promise((resolve) => window.setTimeout(resolve, 1000))
    }
}

function updateNotificationFromJob(notificationId: number, job: Job) {
    notify.update(notificationId, {
        jobId: job.id,
        kind: job.status === "error" ? "error" : job.status === "done" ? "success" : "task",
        status: job.status === "error" ? "error" : job.status === "done" || job.status === "canceled" ? "done" : "active",
        title: job.title,
        message: job.message,
        detail: job.detail,
        progress: job.progress,
    })
}

export function NotificationCenterButton() {
    const notifications = useNotificationStore((state) => state.notifications)
    const openCenter = useNotificationStore((state) => state.openCenter)
    const active = notifications.some((notification) => notification.status === "active")
    const unread = notifications.filter((notification) => !notification.dismissed).length

    return (
        <button
            type="button"
            onClick={openCenter}
            className="group flex h-11 items-center justify-center gap-3 rounded-2xl px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground sm:justify-start"
            aria-label="Open notification center"
        >
            <Bell className={cn("h-5 w-5 shrink-0", active && "animate-pulse text-primary")} strokeWidth={2.15} />
            <span className="hidden min-w-0 flex-1 truncate text-left sm:block">Notifications</span>
            {unread > 0 && (
                <span className="hidden rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-semibold text-primary-foreground sm:inline-flex">
                    {unread}
                </span>
            )}
        </button>
    )
}

function NotificationCard({
    notification,
    onDismiss,
}: {
    notification: AppNotification
    onDismiss: () => void
}) {
    const Icon = icons[notification.kind]
    return (
        <div className="pointer-events-auto w-full rounded-2xl border border-border bg-popover p-4 shadow-2xl">
            <div className="flex items-start gap-3">
                <div className={cn(
                    "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                    notification.status === "error" ? "bg-destructive/10 text-destructive" : "bg-primary/10 text-primary",
                )}>
                    <Icon className={cn("h-4 w-4", notification.status === "active" && "animate-spin")} />
                </div>
                <div className="min-w-0 flex-1">
                    <div className="font-semibold">{notification.title}</div>
                    {notification.message && <div className="mt-0.5 text-sm text-muted-foreground">{notification.message}</div>}
                    {notification.detail && <div className="mt-1 truncate font-mono text-xs text-muted-foreground">{notification.detail}</div>}
                    {notification.status === "active" && (
                        <div className="mt-3 flex items-center gap-2">
                            <div className="h-1 flex-1 overflow-hidden rounded-full bg-secondary">
                                <div
                                    className="h-full rounded-full bg-primary transition-all"
                                    style={{ width: `${Math.max(8, Math.min(notification.progress ?? 10, 100))}%` }}
                                />
                            </div>
                            <span className="w-9 text-right text-[11px] font-semibold tabular-nums text-muted-foreground">
                                {Math.round(notification.progress ?? 0)}%
                            </span>
                        </div>
                    )}
                </div>
                <button
                    type="button"
                    onClick={onDismiss}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
                    aria-label="Dismiss notification"
                >
                    <X className="h-4 w-4" />
                </button>
            </div>
        </div>
    )
}

function NotificationHistoryRow({ notification }: { notification: AppNotification }) {
    const Icon = icons[notification.kind]
    return (
        <div className="flex gap-3 rounded-2xl px-3 py-3 hover:bg-secondary/35">
            <Icon
                className={cn(
                    "mt-0.5 h-4 w-4 shrink-0",
                    notification.status === "error" ? "text-destructive" : "text-primary",
                    notification.status === "active" && "animate-spin",
                )}
            />
            <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                    <div className="truncate font-semibold">{notification.title}</div>
                    <time className="shrink-0 text-xs text-muted-foreground">
                        {new Date(notification.createdAt).toLocaleTimeString()}
                    </time>
                </div>
                {notification.message && <p className="mt-0.5 text-sm text-muted-foreground">{notification.message}</p>}
                {notification.detail && <p className="mt-1 truncate font-mono text-xs text-muted-foreground">{notification.detail}</p>}
                {notification.status === "active" && (
                    <div className="mt-2 flex items-center gap-2">
                        <div className="h-1 flex-1 overflow-hidden rounded-full bg-secondary">
                            <div
                                className="h-full rounded-full bg-primary transition-all"
                                style={{ width: `${Math.max(8, Math.min(notification.progress ?? 10, 100))}%` }}
                            />
                        </div>
                        <span className="w-9 text-right text-[11px] font-semibold tabular-nums text-muted-foreground">
                            {Math.round(notification.progress ?? 0)}%
                        </span>
                    </div>
                )}
                {notification.jobId && (
                    <div className="mt-2 flex gap-2">
                        {notification.status === "active" && (
                            <button
                                type="button"
                                onClick={() => void cancelJob(notification.jobId!)}
                                className="rounded-full bg-secondary px-2.5 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                            >
                                Cancel
                            </button>
                        )}
                        {notification.status === "error" && (
                            <button
                                type="button"
                                onClick={() => void retryJob(notification.jobId!)}
                                className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary"
                            >
                                Retry
                            </button>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}

async function cancelJob(jobId: string) {
    const job = await jobsRepo.cancel(jobId)
    const notification = useNotificationStore.getState().notifications.find((item) => item.jobId === jobId)
    if (!notification) return
    updateNotificationFromJob(notification.id, job)
}

async function retryJob(jobId: string) {
    const job = await jobsRepo.retry(jobId)
    const id = notify.task(job.title || "Background job", job.message)
    notify.update(id, { jobId: job.id, detail: job.detail, progress: job.progress })
    void pollJob(job.id, id)
}
