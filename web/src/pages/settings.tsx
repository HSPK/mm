import { useState } from "react"
import { useNavigate } from "react-router-dom"
import {
    Check,
    Database,
    FolderOpen,
    LogOut,
    Save,
    Server,
    Users,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ListGroup, ListPage, ListRow } from "@/components/ui/list"
import { PageHeader } from "@/components/ui/page-header"
import { ThemePickerCard } from "@/components/settings/theme-picker-card"
import { useAuthStore } from "@/stores/auth"
import { useLogoutRedirect } from "@/hooks/use-logout-redirect"
import { useCurrentLibrary } from "@/hooks/use-current-library"
import { previewImportTemplate, useImportTemplate } from "@/hooks/use-import-template"
import { getUserDisplayName, getUserInitial } from "@/lib/user"
import { Card, CardContent } from "@/components/ui/card"

export default function SettingsPage() {
    const navigate = useNavigate()
    const user = useAuthStore((s) => s.user)
    const handleLogout = useLogoutRedirect()
    const lib = useCurrentLibrary()
    const tmpl = useImportTemplate(lib.current)
    const initial = getUserInitial(user)

    const recent = lib.recent.filter((l) => l.db_path !== lib.current?.db_path)

    return (
        <div className="pb-32 min-h-screen">
            <PageHeader title="Settings" back largeTitle />

            <ListPage>
                {/* ── Account ── */}
                <ListGroup>
                    <li className="list-none">
                        <div className="flex items-center gap-4 px-4 py-4">
                            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/70 text-white text-[22px] font-semibold shrink-0">
                                {initial}
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-[17px] font-semibold truncate">{getUserDisplayName(user)}</p>
                                {user?.display_name && user?.username && (
                                    <p className="text-[13px] text-muted-foreground truncate">@{user.username}</p>
                                )}
                            </div>
                        </div>
                    </li>
                    <ListRow
                        icon={{ icon: <Server className="h-4 w-4" />, tint: "#5856d6" }}
                        label="Profile"
                        chevron
                        onClick={() => navigate("/profile")}
                    />
                    {user?.is_admin && (
                        <ListRow
                            icon={{ icon: <Users className="h-4 w-4" />, tint: "#ff9500" }}
                            label="Manage users"
                            chevron
                            onClick={() => navigate("/admin/users")}
                        />
                    )}
                </ListGroup>

                {/* ── Appearance ── */}
                <ListGroup label="Appearance" footer="Choose a theme — these match Apple's system color palette.">
                    <li className="list-none p-4">
                        <ThemePickerCard inline />
                    </li>
                </ListGroup>

                {/* ── Library ── */}
                <ListGroup label="Library">
                    {lib.current && (
                        <ListRow
                            icon={{ icon: <Database className="h-4 w-4" />, tint: "var(--color-primary)" }}
                            label={lib.current.name}
                            sublabel={lib.current.db_path}
                            trailing={<span className="text-[11px] font-semibold uppercase tracking-wider text-primary">Active</span>}
                        />
                    )}
                    {recent.map((l) => (
                        <ListRow
                            key={l.db_path}
                            icon={<FolderOpen className="h-4 w-4" />}
                            label={l.name}
                            sublabel={l.db_path}
                            chevron
                            onClick={() => lib.switchTo(l.db_path)}
                            disabled={lib.switching}
                        />
                    ))}
                </ListGroup>

                <Card>
                    <CardContent className="pt-5 space-y-4">
                        <OpenLibraryInput
                            switching={lib.switching}
                            error={lib.error}
                            onSwitch={lib.switchTo}
                        />
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="pt-5 space-y-3">
                        <div>
                            <h3 className="text-[15px] font-semibold">Import folder layout</h3>
                            <p className="text-[13px] text-muted-foreground mt-0.5">
                                Template for organizing imported media. Use{" "}
                                <code className="text-[11px] font-mono text-foreground/70">{"{year}, {month}, {day}, {camera}, {type}, {ext}, {original_name}"}</code>.
                            </p>
                        </div>
                        <Input
                            value={tmpl.template}
                            onChange={(e) => tmpl.setTemplate(e.target.value)}
                            placeholder="{year}/{year}-{month:02d}-{day:02d}/{original_name}{ext}"
                            className="font-mono"
                        />
                        <p className="text-[12px] text-muted-foreground">
                            Preview: <span className="font-mono text-foreground/80">{previewImportTemplate(tmpl.template)}</span>
                        </p>
                        <div className="flex justify-end pt-1">
                            <Button onClick={tmpl.save} loading={tmpl.saving} size="sm" variant="tinted">
                                {tmpl.saved ? (
                                    <><Check className="mr-1 h-4 w-4" /> Saved</>
                                ) : tmpl.saving ? (
                                    <>Saving…</>
                                ) : (
                                    <><Save className="mr-1 h-4 w-4" /> Save</>
                                )}
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* ── Sign out ── */}
                <ListGroup>
                    <ListRow
                        icon={{ icon: <LogOut className="h-4 w-4" />, tint: "#ff3b30" }}
                        label="Sign out"
                        destructive
                        onClick={handleLogout}
                    />
                </ListGroup>
            </ListPage>
        </div>
    )
}

function OpenLibraryInput({
    switching,
    error,
    onSwitch,
}: {
    switching: boolean
    error: string | null
    onSwitch: (path: string) => void
}) {
    const [value, setValue] = useState("")
    const submit = () => {
        onSwitch(value)
        setValue("")
    }
    return (
        <div className="space-y-3">
            <div>
                <h3 className="text-[15px] font-semibold">Open another library</h3>
                <p className="text-[13px] text-muted-foreground mt-0.5">
                    Server-side path to a directory containing <code>mm.db</code> or a <code>.db</code> file.
                </p>
            </div>
            <div className="flex gap-2">
                <Input
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    placeholder="/path/to/library"
                    onKeyDown={(e) => e.key === "Enter" && submit()}
                    wrapperClassName="flex-1"
                />
                <Button
                    onClick={submit}
                    disabled={!value.trim()}
                    loading={switching}
                    variant="tinted"
                    className="shrink-0"
                >
                    {switching ? "Switching" : "Switch"}
                </Button>
            </div>
            {error && <p className="text-[12px] text-destructive">{error}</p>}
        </div>
    )
}
