import { create } from "zustand"

export type ToastVariant = "default" | "success" | "error"

export interface Toast {
    id: number
    message: string
    variant: ToastVariant
    /** Auto-dismiss in ms; 0 = sticky until dismissed. */
    duration: number
}

interface ToastState {
    toasts: Toast[]
    push: (message: string, opts?: { variant?: ToastVariant; duration?: number }) => number
    dismiss: (id: number) => void
    clear: () => void
}

let nextId = 1

export const useToastStore = create<ToastState>((set, get) => ({
    toasts: [],
    push: (message, opts) => {
        const id = nextId++
        const toast: Toast = {
            id,
            message,
            variant: opts?.variant ?? "default",
            duration: opts?.duration ?? 2600,
        }
        set((s) => ({ toasts: [...s.toasts, toast] }))
        if (toast.duration > 0) {
            window.setTimeout(() => get().dismiss(id), toast.duration)
        }
        return id
    },
    dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
    clear: () => set({ toasts: [] }),
}))

/**
 * Imperative helpers — use from event handlers + async logic where calling a
 * React hook isn't an option.
 */
export const toast = {
    show: (message: string, opts?: { variant?: ToastVariant; duration?: number }) =>
        useToastStore.getState().push(message, opts),
    success: (message: string, duration?: number) =>
        useToastStore.getState().push(message, { variant: "success", duration }),
    error: (message: string, duration?: number) =>
        useToastStore.getState().push(message, { variant: "error", duration }),
    dismiss: (id: number) => useToastStore.getState().dismiss(id),
}
