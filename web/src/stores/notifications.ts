import { create } from "zustand"

export type NotificationKind = "info" | "success" | "error" | "task"
export type NotificationStatus = "active" | "done" | "error"

export interface AppNotification {
    id: number
    kind: NotificationKind
    status: NotificationStatus
    title: string
    message: string
    detail?: string
    progress?: number
    jobId?: string
    createdAt: number
    updatedAt: number
    dismissed: boolean
}

interface NotificationState {
    notifications: AppNotification[]
    centerOpen: boolean
    push: (input: NotificationInput) => number
    update: (id: number, patch: NotificationPatch) => void
    dismiss: (id: number) => void
    clearHistory: () => void
    openCenter: () => void
    closeCenter: () => void
}

interface NotificationInput {
    kind?: NotificationKind
    status?: NotificationStatus
    title: string
    message?: string
    detail?: string
    progress?: number
}

type NotificationPatch = Partial<Pick<AppNotification, "kind" | "status" | "title" | "message" | "detail" | "progress" | "dismissed" | "jobId">>

const NOTIFICATION_STORAGE_KEY = "mm-notifications-v1"
const REFRESH_INTERRUPTED_MESSAGE = "The page was refreshed before this task finished."

function loadNotifications() {
    if (typeof window === "undefined") return []
    try {
        const raw = window.localStorage.getItem(NOTIFICATION_STORAGE_KEY)
        if (!raw) return []
        const parsed = JSON.parse(raw) as AppNotification[]
        return parsed.map((notification) => {
            if (notification.jobId && notification.message === REFRESH_INTERRUPTED_MESSAGE) {
                return {
                    ...notification,
                    kind: "task" as const,
                    status: "active" as const,
                    title: notification.title.replace(/ interrupted$/, ""),
                    message: "Restoring task status…",
                    dismissed: false,
                    updatedAt: Date.now(),
                }
            }
            return {
                ...notification,
            }
        })
    } catch {
        return []
    }
}

function saveNotifications(notifications: AppNotification[]) {
    if (typeof window === "undefined") return
    window.localStorage.setItem(
        NOTIFICATION_STORAGE_KEY,
        JSON.stringify(notifications.slice(0, 100)),
    )
}

const initialNotifications = loadNotifications()
saveNotifications(initialNotifications)
let nextId = Math.max(0, ...initialNotifications.map((notification) => notification.id)) + 1

export const useNotificationStore = create<NotificationState>((set) => ({
    notifications: initialNotifications,
    centerOpen: false,
    push: (input) => {
        const now = Date.now()
        const id = nextId++
        const notification: AppNotification = {
            id,
            kind: input.kind ?? "info",
            status: input.status ?? (input.kind === "error" ? "error" : "done"),
            title: input.title,
            message: input.message ?? "",
            detail: input.detail,
            progress: input.progress,
            createdAt: now,
            updatedAt: now,
            dismissed: false,
        }
        set((state) => {
            const notifications = [notification, ...state.notifications].slice(0, 100)
            saveNotifications(notifications)
            return { notifications }
        })
        return id
    },
    update: (id, patch) => {
        set((state) => {
            const notifications = state.notifications.map((notification) =>
                notification.id === id
                    ? { ...notification, ...patch, updatedAt: Date.now() }
                    : notification,
            )
            saveNotifications(notifications)
            return { notifications }
        })
    },
    dismiss: (id) => {
        set((state) => {
            const notifications = state.notifications.map((notification) =>
                notification.id === id ? { ...notification, dismissed: true } : notification,
            )
            saveNotifications(notifications)
            return { notifications }
        })
    },
    clearHistory: () => {
        saveNotifications([])
        set({ notifications: [] })
    },
    openCenter: () => set({ centerOpen: true }),
    closeCenter: () => set({ centerOpen: false }),
}))

export const notify = {
    info: (title: string, message?: string) =>
        useNotificationStore.getState().push({ kind: "info", title, message }),
    success: (title: string, message?: string) =>
        useNotificationStore.getState().push({ kind: "success", status: "done", title, message }),
    error: (title: string, message?: string) =>
        useNotificationStore.getState().push({ kind: "error", status: "error", title, message }),
    task: (title: string, message?: string) =>
        useNotificationStore.getState().push({ kind: "task", status: "active", title, message, progress: 0 }),
    update: (id: number, patch: NotificationPatch) =>
        useNotificationStore.getState().update(id, patch),
    dismiss: (id: number) => useNotificationStore.getState().dismiss(id),
}
