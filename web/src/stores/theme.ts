import { create } from "zustand"

export interface ThemeColors {
    background: string
    foreground: string
    card: string
    cardForeground: string
    popover: string
    popoverForeground: string
    primary: string
    primaryForeground: string
    secondary: string
    secondaryForeground: string
    muted: string
    mutedForeground: string
    accent: string
    accentForeground: string
    destructive: string
    border: string
    ring: string
}

export interface ThemeDef {
    id: string
    label: string
    /** Small preview color shown in picker */
    preview: string
    /** "dark" | "light" — controls overlay colors in UI */
    mode: "dark" | "light"
    colors: ThemeColors
}

// ─── Dark Themes ──────────────────────────────────────────

const darkThemes: ThemeDef[] = [
    {
        id: "midnight",
        label: "Midnight",
        preview: "#3b82f6",
        mode: "dark",
        colors: {
            background: "#09090b",
            foreground: "#fafafa",
            card: "#0a0a0a",
            cardForeground: "#fafafa",
            popover: "#0a0a0a",
            popoverForeground: "#fafafa",
            primary: "#3b82f6",
            primaryForeground: "#ffffff",
            secondary: "#27272a",
            secondaryForeground: "#fafafa",
            muted: "#27272a",
            mutedForeground: "#a1a1aa",
            accent: "#27272a",
            accentForeground: "#fafafa",
            destructive: "#ef4444",
            border: "#27272a",
            ring: "#3b82f6",
        },
    },
    {
        id: "rose",
        label: "Rosé",
        preview: "#f43f5e",
        mode: "dark",
        colors: {
            background: "#0c0a09",
            foreground: "#fafaf9",
            card: "#0c0a09",
            cardForeground: "#fafaf9",
            popover: "#0c0a09",
            popoverForeground: "#fafaf9",
            primary: "#f43f5e",
            primaryForeground: "#ffffff",
            secondary: "#292524",
            secondaryForeground: "#fafaf9",
            muted: "#292524",
            mutedForeground: "#a8a29e",
            accent: "#292524",
            accentForeground: "#fafaf9",
            destructive: "#ef4444",
            border: "#292524",
            ring: "#f43f5e",
        },
    },
    {
        id: "emerald",
        label: "Emerald",
        preview: "#10b981",
        mode: "dark",
        colors: {
            background: "#0a0a0b",
            foreground: "#f0fdf4",
            card: "#0a0a0b",
            cardForeground: "#f0fdf4",
            popover: "#0a0a0b",
            popoverForeground: "#f0fdf4",
            primary: "#10b981",
            primaryForeground: "#ffffff",
            secondary: "#1c1c22",
            secondaryForeground: "#f0fdf4",
            muted: "#1c1c22",
            mutedForeground: "#94a3b8",
            accent: "#1c1c22",
            accentForeground: "#f0fdf4",
            destructive: "#ef4444",
            border: "#1e1e24",
            ring: "#10b981",
        },
    },
    {
        id: "violet",
        label: "Violet",
        preview: "#8b5cf6",
        mode: "dark",
        colors: {
            background: "#09090b",
            foreground: "#fafafa",
            card: "#0a0a0c",
            cardForeground: "#fafafa",
            popover: "#0a0a0c",
            popoverForeground: "#fafafa",
            primary: "#8b5cf6",
            primaryForeground: "#ffffff",
            secondary: "#1e1b2e",
            secondaryForeground: "#fafafa",
            muted: "#1e1b2e",
            mutedForeground: "#a1a1aa",
            accent: "#1e1b2e",
            accentForeground: "#fafafa",
            destructive: "#ef4444",
            border: "#23203a",
            ring: "#8b5cf6",
        },
    },
    {
        id: "amber",
        label: "Amber",
        preview: "#f59e0b",
        mode: "dark",
        colors: {
            background: "#0c0a09",
            foreground: "#fafaf9",
            card: "#0c0a09",
            cardForeground: "#fafaf9",
            popover: "#0c0a09",
            popoverForeground: "#fafaf9",
            primary: "#f59e0b",
            primaryForeground: "#0c0a09",
            secondary: "#292524",
            secondaryForeground: "#fafaf9",
            muted: "#292524",
            mutedForeground: "#a8a29e",
            accent: "#292524",
            accentForeground: "#fafaf9",
            destructive: "#ef4444",
            border: "#292524",
            ring: "#f59e0b",
        },
    },
    {
        id: "cyan",
        label: "Cyan",
        preview: "#06b6d4",
        mode: "dark",
        colors: {
            background: "#080b0e",
            foreground: "#ecfeff",
            card: "#080b0e",
            cardForeground: "#ecfeff",
            popover: "#080b0e",
            popoverForeground: "#ecfeff",
            primary: "#06b6d4",
            primaryForeground: "#ffffff",
            secondary: "#172a31",
            secondaryForeground: "#ecfeff",
            muted: "#172a31",
            mutedForeground: "#94a3b8",
            accent: "#172a31",
            accentForeground: "#ecfeff",
            destructive: "#ef4444",
            border: "#1a2e36",
            ring: "#06b6d4",
        },
    },
]

// ─── Light Themes ─────────────────────────────────────────

const lightThemes: ThemeDef[] = [
    {
        id: "light",
        label: "Light",
        preview: "#3b82f6",
        mode: "light",
        colors: {
            background: "#ffffff",
            foreground: "#09090b",
            card: "#ffffff",
            cardForeground: "#09090b",
            popover: "#ffffff",
            popoverForeground: "#09090b",
            primary: "#3b82f6",
            primaryForeground: "#ffffff",
            secondary: "#f4f4f5",
            secondaryForeground: "#18181b",
            muted: "#f4f4f5",
            mutedForeground: "#71717a",
            accent: "#f4f4f5",
            accentForeground: "#18181b",
            destructive: "#ef4444",
            border: "#e4e4e7",
            ring: "#3b82f6",
        },
    },
    {
        id: "light-rose",
        label: "Blush",
        preview: "#f43f5e",
        mode: "light",
        colors: {
            background: "#fffbfb",
            foreground: "#1c1917",
            card: "#ffffff",
            cardForeground: "#1c1917",
            popover: "#ffffff",
            popoverForeground: "#1c1917",
            primary: "#f43f5e",
            primaryForeground: "#ffffff",
            secondary: "#fef2f2",
            secondaryForeground: "#1c1917",
            muted: "#f5f5f4",
            mutedForeground: "#78716c",
            accent: "#fef2f2",
            accentForeground: "#1c1917",
            destructive: "#ef4444",
            border: "#e7e5e4",
            ring: "#f43f5e",
        },
    },
    {
        id: "light-emerald",
        label: "Mint",
        preview: "#10b981",
        mode: "light",
        colors: {
            background: "#fbfefc",
            foreground: "#0f172a",
            card: "#ffffff",
            cardForeground: "#0f172a",
            popover: "#ffffff",
            popoverForeground: "#0f172a",
            primary: "#10b981",
            primaryForeground: "#ffffff",
            secondary: "#f0fdf4",
            secondaryForeground: "#0f172a",
            muted: "#f1f5f9",
            mutedForeground: "#64748b",
            accent: "#f0fdf4",
            accentForeground: "#0f172a",
            destructive: "#ef4444",
            border: "#e2e8f0",
            ring: "#10b981",
        },
    },
    {
        id: "light-violet",
        label: "Lavender",
        preview: "#8b5cf6",
        mode: "light",
        colors: {
            background: "#fcfbff",
            foreground: "#09090b",
            card: "#ffffff",
            cardForeground: "#09090b",
            popover: "#ffffff",
            popoverForeground: "#09090b",
            primary: "#8b5cf6",
            primaryForeground: "#ffffff",
            secondary: "#f5f3ff",
            secondaryForeground: "#18181b",
            muted: "#f4f4f5",
            mutedForeground: "#71717a",
            accent: "#f5f3ff",
            accentForeground: "#18181b",
            destructive: "#ef4444",
            border: "#e4e4e7",
            ring: "#8b5cf6",
        },
    },
]

export const themes: ThemeDef[] = [...lightThemes, ...darkThemes]

// ─── Apply to :root ───────────────────────────────────────

function applyTheme(theme: ThemeDef) {
    const { colors, mode } = theme
    const root = document.documentElement
    root.style.setProperty("--color-background", colors.background)
    root.style.setProperty("--color-foreground", colors.foreground)
    root.style.setProperty("--color-card", colors.card)
    root.style.setProperty("--color-card-foreground", colors.cardForeground)
    root.style.setProperty("--color-popover", colors.popover)
    root.style.setProperty("--color-popover-foreground", colors.popoverForeground)
    root.style.setProperty("--color-primary", colors.primary)
    root.style.setProperty("--color-primary-foreground", colors.primaryForeground)
    root.style.setProperty("--color-secondary", colors.secondary)
    root.style.setProperty("--color-secondary-foreground", colors.secondaryForeground)
    root.style.setProperty("--color-muted", colors.muted)
    root.style.setProperty("--color-muted-foreground", colors.mutedForeground)
    root.style.setProperty("--color-accent", colors.accent)
    root.style.setProperty("--color-accent-foreground", colors.accentForeground)
    root.style.setProperty("--color-destructive", colors.destructive)
    root.style.setProperty("--color-border", colors.border)
    root.style.setProperty("--color-input", colors.border)
    root.style.setProperty("--color-ring", colors.ring)
    // Theme mode class for conditional styling
    root.dataset.theme = mode
    if (mode === "dark") {
        root.classList.add("dark")
        root.classList.remove("light")
    } else {
        root.classList.add("light")
        root.classList.remove("dark")
    }
    // Update meta theme-color
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) meta.setAttribute("content", colors.background)
}

// ─── Store ────────────────────────────────────────────────

interface ThemeState {
    themeId: string
    setTheme: (id: string) => void
}

const savedId = localStorage.getItem("uom-theme") || "midnight"

export const useThemeStore = create<ThemeState>((set) => ({
    themeId: savedId,
    setTheme: (id: string) => {
        const theme = themes.find((t) => t.id === id)
        if (!theme) return
        localStorage.setItem("uom-theme", id)
        applyTheme(theme)
        set({ themeId: id })
    },
}))

// Apply saved theme immediately on import
const initial = themes.find((t) => t.id === savedId) ?? themes[0]
applyTheme(initial)
