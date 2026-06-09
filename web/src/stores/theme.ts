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

// ─── Dark Themes (Apple HIG palette) ──────────────────────
// Colors drawn from Apple Human Interface Guidelines system colors.
// Backgrounds use systemBackground / secondarySystemBackground;
// accents are the system colors (Blue, Pink, Green, Indigo, Orange, Teal).

const DARK_NEUTRALS = {
    background: "#000000",
    foreground: "#f5f5f7",
    card: "#1c1c1e",
    cardForeground: "#f5f5f7",
    popover: "#1c1c1e",
    popoverForeground: "#f5f5f7",
    secondary: "#2c2c2e",
    secondaryForeground: "#f5f5f7",
    muted: "#1c1c1e",
    mutedForeground: "#98989d",
    accent: "#2c2c2e",
    accentForeground: "#f5f5f7",
    destructive: "#ff453a",
    border: "rgba(255,255,255,0.08)",
}

const LIGHT_NEUTRALS = {
    background: "#f2f2f7",
    foreground: "#000000",
    card: "#ffffff",
    cardForeground: "#000000",
    popover: "#ffffff",
    popoverForeground: "#000000",
    secondary: "#e5e5ea",
    secondaryForeground: "#000000",
    muted: "#f2f2f7",
    mutedForeground: "#6b6b70",
    accent: "#e5e5ea",
    accentForeground: "#000000",
    destructive: "#ff3b30",
    border: "rgba(60,60,67,0.18)",
}

function darkTheme(
    id: string,
    label: string,
    primary: string,
    primaryFg: string = "#ffffff",
): ThemeDef {
    return {
        id,
        label,
        preview: primary,
        mode: "dark",
        colors: { ...DARK_NEUTRALS, primary, primaryForeground: primaryFg, ring: primary },
    }
}

function lightTheme(
    id: string,
    label: string,
    primary: string,
    primaryFg: string = "#ffffff",
): ThemeDef {
    return {
        id,
        label,
        preview: primary,
        mode: "light",
        colors: { ...LIGHT_NEUTRALS, primary, primaryForeground: primaryFg, ring: primary },
    }
}

const darkThemes: ThemeDef[] = [
    darkTheme("midnight", "Blue", "#0a84ff"),
    darkTheme("rose", "Pink", "#ff375f"),
    darkTheme("emerald", "Green", "#30d158"),
    darkTheme("violet", "Indigo", "#5e5ce6"),
    darkTheme("amber", "Orange", "#ff9f0a", "#000000"),
    darkTheme("cyan", "Teal", "#64d2ff", "#000000"),
]

// ─── Light Themes (Apple HIG palette) ─────────────────────

const lightThemes: ThemeDef[] = [
    lightTheme("light", "Light · Blue", "#007aff"),
    lightTheme("light-rose", "Light · Pink", "#ff2d55"),
    lightTheme("light-emerald", "Light · Green", "#34c759"),
    lightTheme("light-violet", "Light · Indigo", "#5856d6"),
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

const savedId = localStorage.getItem("mm-theme") || "midnight"

export const useThemeStore = create<ThemeState>((set) => ({
    themeId: savedId,
    setTheme: (id: string) => {
        const theme = themes.find((t) => t.id === id)
        if (!theme) return
        localStorage.setItem("mm-theme", id)
        applyTheme(theme)
        set({ themeId: id })
    },
}))

// Apply saved theme immediately on import
const initial = themes.find((t) => t.id === savedId) ?? themes[0]
applyTheme(initial)
