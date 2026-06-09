import { Check } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { themes, useThemeStore, type ThemeDef } from "@/stores/theme"
import { cn } from "@/lib/utils"

interface Props {
    /** Render without the Card wrapper (for use inside ListGroup). */
    inline?: boolean
}

export function ThemePickerCard({ inline }: Props = {}) {
    const { themeId, setTheme } = useThemeStore()
    const lightThemes = themes.filter((t) => t.mode === "light")
    const darkThemes = themes.filter((t) => t.mode === "dark")

    const body = (
        <>
            <ThemeGroup
                label="Light"
                themes={lightThemes}
                activeId={themeId}
                onSelect={setTheme}
                swatchBackground={() => "#ffffff"}
            />
            <ThemeGroup
                label="Dark"
                themes={darkThemes}
                activeId={themeId}
                onSelect={setTheme}
                swatchBackground={(t) => t.colors.background}
            />
        </>
    )

    if (inline) {
        return <div className="space-y-5">{body}</div>
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Appearance</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">{body}</CardContent>
        </Card>
    )
}

interface ThemeGroupProps {
    label: string
    themes: ThemeDef[]
    activeId: string
    onSelect: (id: string) => void
    swatchBackground: (theme: ThemeDef) => string
}

function ThemeGroup({ label, themes, activeId, onSelect, swatchBackground }: ThemeGroupProps) {
    return (
        <div>
            <p className="text-[11px] uppercase tracking-wider font-medium text-muted-foreground/80 mb-3">{label}</p>
            <div className="grid grid-cols-4 gap-3">
                {themes.map((t) => (
                    <ThemeSwatch
                        key={t.id}
                        theme={t}
                        active={activeId === t.id}
                        onSelect={onSelect}
                        background={swatchBackground(t)}
                    />
                ))}
            </div>
        </div>
    )
}

interface ThemeSwatchProps {
    theme: ThemeDef
    active: boolean
    onSelect: (id: string) => void
    background: string
}

function ThemeSwatch({ theme, active, onSelect, background }: ThemeSwatchProps) {
    // Strip the redundant "Light · " prefix that's repeated in every label.
    const compactLabel = theme.label.replace(/^Light · /, "")
    return (
        <button
            onClick={() => onSelect(theme.id)}
            className={cn(
                "relative flex flex-col items-center gap-2 rounded-xl p-2.5 transition-all duration-200",
                active
                    ? "bg-primary/12 ring-2 ring-primary"
                    : "hover:bg-secondary/40",
            )}
        >
            <div className="relative">
                <div
                    className="h-10 w-10 rounded-full elevation-1"
                    style={{ background: `linear-gradient(135deg, ${background} 50%, ${theme.preview} 50%)` }}
                />
                {active && (
                    <div className="absolute -bottom-0.5 -right-0.5 h-4 w-4 rounded-full bg-primary flex items-center justify-center elevation-1">
                        <Check className="h-2.5 w-2.5 text-primary-foreground" strokeWidth={3} />
                    </div>
                )}
            </div>
            <span className={cn(
                "text-[11px] font-medium",
                active ? "text-primary" : "text-muted-foreground",
            )}>
                {compactLabel}
            </span>
        </button>
    )
}
