import { useCallback, useRef, useState } from "react"
import { jobsRepo, type Job } from "@/api/jobs"
import { notify } from "@/stores/notifications"

export const ACTIVE_JOB_STATUSES = new Set(["queued", "running", "canceling"])
export const TERMINAL_JOB_STATUSES = new Set(["done", "error", "canceled", "completed_with_errors"])

export function isActiveOrganizerJob(status: string) {
    return ACTIVE_JOB_STATUSES.has(status)
}

export function isTerminalOrganizerJob(status: string) {
    return TERMINAL_JOB_STATUSES.has(status)
}

export function useOrganizerJob() {
    const [activeCommands, setActiveCommands] = useState<Set<string>>(new Set())
    const activeRef = useRef(new Set<string>())

    const runJob = useCallback(async (
        command: string,
        queuedTitle: string,
        queuedMessage: string,
        create: (idempotencyKey: string) => Promise<Job>,
    ) => {
        if (activeRef.current.has(command)) return null
        activeRef.current.add(command)
        setActiveCommands(new Set(activeRef.current))
        const notificationId = notify.task(queuedTitle, queuedMessage)
        try {
            const job = await create(newIdempotencyKey())
            return await pollJob(job, notificationId)
        } catch (error) {
            notify.update(notificationId, {
                kind: "error",
                status: "error",
                title: `${queuedTitle.replace(" queued", "")} failed`,
                message: error instanceof Error ? error.message : "Could not start organizer job",
                progress: 100,
            })
            return null
        } finally {
            activeRef.current.delete(command)
            setActiveCommands(new Set(activeRef.current))
        }
    }, [])

    return {
        activeCommands,
        isCommandActive: (command: string) => activeCommands.has(command),
        runJob,
    }
}

async function pollJob(initial: Job, notificationId: number) {
    let job = initial
    while (true) {
        notify.update(notificationId, notificationForJob(job))
        if (isTerminalOrganizerJob(job.status)) return job
        await new Promise((resolve) => window.setTimeout(resolve, 900))
        job = await jobsRepo.job(job.id)
    }
}

function notificationForJob(job: Job) {
    const partial = job.status === "completed_with_errors"
    const failed = job.status === "error" || job.status === "canceled"
    return {
        kind: failed ? "error" : partial ? "info" : job.status === "done" ? "success" : "task",
        status: failed ? "error" : isTerminalOrganizerJob(job.status) ? "done" : "active",
        jobId: job.id,
        title: partial ? `${job.title} completed with errors` : job.title,
        message: job.message,
        detail: job.detail,
        progress: job.progress,
    } as const
}

function newIdempotencyKey() {
    return typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `organizer-${Date.now()}-${Math.random().toString(36).slice(2)}`
}
