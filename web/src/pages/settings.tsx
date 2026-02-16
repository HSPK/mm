import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Save, Check, LogOut, User, ChevronLeft } from "lucide-react"
import { useThemeStore, themes } from "@/stores/theme"
import { useAuthStore } from "@/stores/auth"
import { cn } from "@/lib/utils"

export default function SettingsPage() {
    const navigate = useNavigate()
    const [libraryPath, setLibraryPath] = useState("/mnt/media")
    const [autoScan, setAutoScan] = useState(true)
    const [scanInterval, setScanInterval] = useState("02:00:00")
    const [thumbnailQuality, setThumbnailQuality] = useState(80)

    const { themeId, setTheme } = useThemeStore()
    const user = useAuthStore((s) => s.user)
    const logout = useAuthStore((s) => s.logout)

    const initial = (user?.display_name ?? user?.username ?? "U")[0].toUpperCase()

    const handleLogout = () => {
        logout()
        navigate("/login", { replace: true })
    }

    const handleSave = () => {
        console.log("Saving settings:", { libraryPath, autoScan, scanInterval, thumbnailQuality })
    }

    const lightThemes = themes.filter((t) => t.mode === "light")
    const darkThemes = themes.filter((t) => t.mode === "dark")

    return (
        <div className="pb-32">
            {/* Sticky header */}
            <div className="sticky top-0 z-20 flex items-center gap-3 px-4 h-14 bg-background/80 backdrop-blur-xl border-b border-border/40">
                <button
                    onClick={() => navigate(-1)}
                    className="flex items-center justify-center h-9 w-9 rounded-full hover:bg-secondary transition-colors"
                >
                    <ChevronLeft className="h-5 w-5" />
                </button>
                <h1 className="text-lg font-semibold">Settings</h1>
            </div>

            <div className="p-6 max-w-2xl mx-auto space-y-6">

                {/* ── Account ── */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Account</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center gap-4">
                            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/15 text-lg font-bold text-primary border border-primary/20">
                                {initial}
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-sm font-semibold truncate">{user?.display_name || user?.username}</p>
                                {user?.display_name && user?.username && (
                                    <p className="text-xs text-muted-foreground truncate">@{user.username}</p>
                                )}
                            </div>
                        </div>
                        <div className="pt-2 border-t border-border">
                            <button
                                onClick={handleLogout}
                                className="flex items-center gap-2 text-sm text-destructive hover:text-destructive/80 transition-colors"
                            >
                                <LogOut className="h-4 w-4" />
                                Sign Out
                            </button>
                        </div>
                    </CardContent>
                </Card>

                {/* ── Theme ── */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Appearance</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-5">
                        {/* Light themes */}
                        <div>
                            <p className="text-xs font-medium text-muted-foreground mb-3">Light</p>
                            <div className="grid grid-cols-4 gap-3">
                                {lightThemes.map((t) => (
                                    <button
                                        key={t.id}
                                        onClick={() => setTheme(t.id)}
                                        className={cn(
                                            "relative flex flex-col items-center gap-2 rounded-xl p-3 transition-all duration-200 border",
                                            themeId === t.id
                                                ? "border-primary bg-primary/10"
                                                : "border-border hover:border-primary/30 hover:bg-muted/50",
                                        )}
                                    >
                                        {/* Preview swatch */}
                                        <div className="relative">
                                            <div
                                                className="h-10 w-10 rounded-full shadow-sm"
                                                style={{
                                                    background: `linear-gradient(135deg, #ffffff 50%, ${t.preview} 50%)`,
                                                }}
                                            />
                                            {themeId === t.id && (
                                                <div className="absolute -bottom-0.5 -right-0.5 h-4 w-4 rounded-full bg-primary flex items-center justify-center">
                                                    <Check className="h-2.5 w-2.5 text-primary-foreground" />
                                                </div>
                                            )}
                                        </div>
                                        <span className={cn(
                                            "text-[11px] font-medium",
                                            themeId === t.id ? "text-primary" : "text-muted-foreground",
                                        )}>
                                            {t.label}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Dark themes */}
                        <div>
                            <p className="text-xs font-medium text-muted-foreground mb-3">Dark</p>
                            <div className="grid grid-cols-4 gap-3">
                                {darkThemes.map((t) => (
                                    <button
                                        key={t.id}
                                        onClick={() => setTheme(t.id)}
                                        className={cn(
                                            "relative flex flex-col items-center gap-2 rounded-xl p-3 transition-all duration-200 border",
                                            themeId === t.id
                                                ? "border-primary bg-primary/10"
                                                : "border-border hover:border-primary/30 hover:bg-muted/50",
                                        )}
                                    >
                                        <div className="relative">
                                            <div
                                                className="h-10 w-10 rounded-full shadow-sm"
                                                style={{
                                                    background: `linear-gradient(135deg, ${t.colors.background} 50%, ${t.preview} 50%)`,
                                                }}
                                            />
                                            {themeId === t.id && (
                                                <div className="absolute -bottom-0.5 -right-0.5 h-4 w-4 rounded-full bg-primary flex items-center justify-center">
                                                    <Check className="h-2.5 w-2.5 text-primary-foreground" />
                                                </div>
                                            )}
                                        </div>
                                        <span className={cn(
                                            "text-[11px] font-medium",
                                            themeId === t.id ? "text-primary" : "text-muted-foreground",
                                        )}>
                                            {t.label}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* ── Library ── */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Library Configuration</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-5">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Library Path</label>
                            <Input value={libraryPath} onChange={(e) => setLibraryPath(e.target.value)} />
                        </div>

                        <div className="flex items-center justify-between">
                            <label className="text-sm font-medium">Auto Scan</label>
                            <button
                                type="button"
                                role="switch"
                                aria-checked={autoScan}
                                onClick={() => setAutoScan(!autoScan)}
                                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors ${autoScan ? "bg-primary" : "bg-muted"}`}
                            >
                                <span className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform ${autoScan ? "translate-x-5" : "translate-x-0.5"} mt-0.5`} />
                            </button>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Scan Interval</label>
                            <Input value={scanInterval} onChange={(e) => setScanInterval(e.target.value)} placeholder="HH:MM:SS" />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Thumbnail Quality</label>
                            <Input
                                type="number"
                                min={10}
                                max={100}
                                value={thumbnailQuality}
                                onChange={(e) => setThumbnailQuality(Number(e.target.value))}
                            />
                        </div>

                        <div className="flex justify-end pt-2">
                            <Button onClick={handleSave}>
                                <Save className="mr-2 h-4 w-4" />
                                Save Changes
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
