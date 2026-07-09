import { create } from "zustand"
import { notify } from "@/stores/notifications"

export type ToastVariant = "default" | "success" | "error"

export interface Toast {
    id: number
    message: string
    variant: ToastVariant
    duration: number
}

interface ToastState {
    toasts: Toast[]
    push: (message: string, opts?: { variant?: ToastVariant; duration?: number }) => number
    dismiss: (id: number) => void
    clear: () => void
}

let nextId = 1

export const useToastStore = create<ToastState>((set) => ({
    toasts: [],
    push: (message, opts) => {
        const id = nextId++
        const variant = opts?.variant ?? "default"
        const toast: Toast = {
            id,
            message,
            variant,
            duration: opts?.duration ?? 2600,
        }
        set((state) => ({ toasts: [...state.toasts, toast] }))
        if (variant === "error") notify.error("Error", message)
        else if (variant === "success") notify.success("Done", message)
        else notify.info("Notice", message)
        return id
    },
    dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) })),
    clear: () => set({ toasts: [] }),
}))

export const toast = {
    show: (message: string, opts?: { variant?: ToastVariant; duration?: number }) =>
        useToastStore.getState().push(message, opts),
    success: (message: string, duration?: number) =>
        useToastStore.getState().push(message, { variant: "success", duration }),
    error: (message: string, duration?: number) =>
        useToastStore.getState().push(message, { variant: "error", duration }),
    dismiss: (id: number) => useToastStore.getState().dismiss(id),
}
