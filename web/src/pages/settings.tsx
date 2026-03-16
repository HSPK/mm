import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Save, Check, LogOut, ChevronLeft, FolderOpen, Database, Loader2 } from "lucide-react"
import { useThemeStore, themes } from "@/stores/theme"
import { useAuthStore } from "@/stores/auth"
import { useMediaStore } from "@/stores/media"
import { api } from "@/api/client"
import { cn } from "@/lib/utils"

interface LibraryInfo {
    db_path: string
    name: string
}

export default function SettingsPage() {
    const navigate = useNavigate()

    const { themeId, setTheme } = useThemeStore()
    const user = useAuthStore((s) => s.user)
    const logout = useAuthStore((s) => s.logout)
    const fetchMedia = useMediaStore((s) => s.fetchMedia)

    const initial = (user?.display_name ?? user?.username ?? "U")[0].toUpperCase()

    // ── Library switching state ──
    const [currentLibrary, setCurrentLibrary] = useState<LibraryInfo | null>(null)
    const [recentLibraries, setRecentLibraries] = useState<LibraryInfo[]>([])
    const [newLibraryPath, setNewLibraryPath] = useState("")
    const [switching, setSwitching] = useState(false)
    const [switchError, setSwitchError] = useState<string | null>(null)

    useEffect(() => {
        api.get<LibraryInfo>("/library").then((r) => setCurrentLibrary(r.data)).catch(() => { })
        api.get<LibraryInfo[]>("/library/recent").then((r) => setRecentLibraries(r.data)).catch(() => { })
    }, [])

    const handleSwitchLibrary = async (dbPath: string) => {
        if (!dbPath.trim()) return
        setSwitching(true)
        setSwitchError(null)
        try {
            const res = await api.post<LibraryInfo & { message: string }>("/library/switch", { db_path: dbPath })
            setCurrentLibrary(res.data)
            setNewLibraryPath("")
            // Refresh recent list
            api.get<LibraryInfo[]>("/library/recent").then((r) => setRecentLibraries(r.data)).catch(() => { })
            // Reload media with new library
            fetchMedia(true)
        } catch (err: any) {
            setSwitchError(err.response?.data?.detail || err.message || "Failed to switch library")
        } finally {
            setSwitching(false)
        }
    }

    // ── Library config (import template etc.) ──
    const [importTemplate, setImportTemplate] = useState("")
    const [configSaving, setConfigSaving] = useState(false)
    const [configSaved, setConfigSaved] = useState(false)

    useEffect(() => {
        api.get<Record<string, string>>("/library/config")
            .then((r) => {
                if (r.data.import_template) setImportTemplate(r.data.import_template)
            })
            .catch(() => { })
    }, [currentLibrary])

    const handleSaveConfig = async () => {
        setConfigSaving(true)
        setConfigSaved(false)
        try {
            await api.put("/library/config", { import_template: importTemplate })
            setConfigSaved(true)
            setTimeout(() => setConfigSaved(false), 2000)
        } catch {
            // ignore
        } finally {
            setConfigSaving(false)
        }
    }

    const handleLogout = () => {
        logout()
        navigate("/login", { replace: true })
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
                        <CardTitle className="text-lg">Library</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-5">
                        {/* Current library */}
                        {currentLibrary && (
                            <div className="flex items-center gap-3 p-3 rounded-lg bg-primary/5 border border-primary/20">
                                <Database className="h-5 w-5 text-primary shrink-0" />
                                <div className="min-w-0 flex-1">
                                    <p className="text-sm font-semibold truncate">{currentLibrary.name}</p>
                                    <p className="text-xs text-muted-foreground truncate">{currentLibrary.db_path}</p>
                                </div>
                                <span className="text-[10px] font-medium text-primary bg-primary/10 px-2 py-0.5 rounded-full">Active</span>
                            </div>
                        )}

                        {/* Recent libraries */}
                        {recentLibraries.length > 1 && (
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Recent Libraries</label>
                                <div className="space-y-1.5">
                                    {recentLibraries
                                        .filter((lib) => lib.db_path !== currentLibrary?.db_path)
                                        .map((lib) => (
                                            <button
                                                key={lib.db_path}
                                                onClick={() => handleSwitchLibrary(lib.db_path)}
                                                disabled={switching}
                                                className="w-full flex items-center gap-3 p-2.5 rounded-lg border border-border hover:border-primary/30 hover:bg-muted/50 transition-all text-left"
                                            >
                                                <FolderOpen className="h-4 w-4 text-muted-foreground shrink-0" />
                                                <div className="min-w-0 flex-1">
                                                    <p className="text-sm font-medium truncate">{lib.name}</p>
                                                    <p className="text-[11px] text-muted-foreground truncate">{lib.db_path}</p>
                                                </div>
                                            </button>
                                        ))}
                                </div>
                            </div>
                        )}

                        {/* Switch to new library */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Open Library</label>
                            <p className="text-xs text-muted-foreground">
                                Enter a server-side path to a library directory (containing mm.db) or a .db file.
                            </p>
                            <div className="flex gap-2">
                                <Input
                                    value={newLibraryPath}
                                    onChange={(e) => setNewLibraryPath(e.target.value)}
                                    placeholder="/path/to/library or /path/to/mm.db"
                                    onKeyDown={(e) => e.key === "Enter" && handleSwitchLibrary(newLibraryPath)}
                                />
                                <Button
                                    onClick={() => handleSwitchLibrary(newLibraryPath)}
                                    disabled={switching || !newLibraryPath.trim()}
                                    size="sm"
                                    className="shrink-0"
                                >
                                    {switching ? <Loader2 className="h-4 w-4 animate-spin" /> : "Switch"}
                                </Button>
                            </div>
                            {switchError && (
                                <p className="text-xs text-destructive">{switchError}</p>
                            )}
                        </div>

                        {/* Divider */}
                        <div className="border-t border-border" />

                        {/* Directory structure template */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Import Directory Structure</label>
                            <p className="text-xs text-muted-foreground">
                                Template for organizing imported media into folders.
                                Variables: <code className="text-[11px]">{"{year}"}</code>, <code className="text-[11px]">{"{month}"}</code>, <code className="text-[11px]">{"{day}"}</code>, <code className="text-[11px]">{"{camera}"}</code>, <code className="text-[11px]">{"{type}"}</code>, <code className="text-[11px]">{"{ext}"}</code>, <code className="text-[11px]">{"{original_name}"}</code>
                            </p>
                            <Input
                                value={importTemplate}
                                onChange={(e) => setImportTemplate(e.target.value)}
                                placeholder="{year}/{year}-{month:02d}-{day:02d}/{original_name}{ext}"
                                className="font-mono text-sm"
                            />
                            <p className="text-[11px] text-muted-foreground">
                                Preview: <span className="font-mono text-foreground/70">
                                    {importTemplate
                                        .replaceAll("{year}", "2024")
                                        .replaceAll("{month:02d}", "03")
                                        .replaceAll("{month}", "3")
                                        .replaceAll("{day:02d}", "15")
                                        .replaceAll("{day}", "15")
                                        .replaceAll("{camera}", "Sony A7IV")
                                        .replaceAll("{type}", "photo")
                                        .replaceAll("{ext}", ".jpg")
                                        .replaceAll("{original_name}", "DSC_0001")}
                                </span>
                            </p>
                        </div>

                        <div className="flex justify-end pt-1">
                            <Button onClick={handleSaveConfig} disabled={configSaving} size="sm">
                                {configSaved ? (
                                    <><Check className="mr-2 h-4 w-4" /> Saved</>
                                ) : configSaving ? (
                                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>
                                ) : (
                                    <><Save className="mr-2 h-4 w-4" /> Save</>
                                )}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
