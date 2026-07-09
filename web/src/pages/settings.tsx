import { useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import {
    Check,
    Database,
    FolderOpen,
    LogOut,
    Save,
    ShieldCheck,
    Users,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ListGroup, ListPage, ListRow } from "@/components/ui/list"
import { PageHeader } from "@/components/ui/page-header"
import { ThemePickerCard } from "@/components/settings/theme-picker-card"
import { OrganizerCard } from "@/components/settings/organizer-card"
import { MediaSourcesCard } from "@/components/settings/media-sources-card"
import { ServerFilePicker } from "@/components/server-file-picker"
import { useAuthStore } from "@/stores/auth"
import { useLogoutRedirect } from "@/hooks/use-logout-redirect"
import { useCurrentLibrary } from "@/hooks/use-current-library"
import { previewImportTemplate, useImportTemplate } from "@/hooks/use-import-template"
import { getUserDisplayName, getUserInitial } from "@/lib/user"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

type SettingsSection = "account" | "appearance" | "library" | "media"

const settingsSections: { key: SettingsSection; label: string }[] = [
    { key: "account", label: "Account" },
    { key: "appearance", label: "Appearance" },
    { key: "library", label: "Library" },
    { key: "media", label: "Media" },
]

export default function SettingsPage() {
    const [searchParams, setSearchParams] = useSearchParams()
    const initialSection = parseSettingsSection(searchParams.get("section"))
    const [activeSection, setActiveSectionState] = useState<SettingsSection>(initialSection)
    const navigate = useNavigate()
    const user = useAuthStore((s) => s.user)
    const handleLogout = useLogoutRedirect()
    const lib = useCurrentLibrary()
    const tmpl = useImportTemplate(lib.current)
    const initial = getUserInitial(user)

    const recent = lib.recent.filter((l) => l.db_path !== lib.current?.db_path)
    const setActiveSection = (section: SettingsSection) => {
        setActiveSectionState(section)
        setSearchParams(section === "library" ? {} : { section }, { replace: true })
    }

    return (
        <div className="pb-32 min-h-screen">
            <PageHeader title="Settings" back />

            <ListPage>
                <SettingsSectionTabs active={activeSection} onChange={setActiveSection} />

                {activeSection === "account" && (
                    <>
                        <div className="bg-card rounded-3xl elevation-1 p-4 flex items-center gap-4">
                            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/70 text-white text-[26px] font-semibold elevation-2">
                                {initial}
                            </div>
                            <div className="min-w-0 flex-1">
                                <h2 className="truncate text-[19px] font-semibold leading-tight">
                                    {getUserDisplayName(user)}
                                </h2>
                                {user?.display_name && user?.username && (
                                    <p className="mt-0.5 truncate text-[14px] text-muted-foreground">@{user.username}</p>
                                )}
                                {user?.is_admin && (
                                    <span className="mt-2 inline-flex items-center gap-1 rounded-full bg-primary/12 px-2.5 py-0.5 text-[11px] font-medium text-primary">
                                        <ShieldCheck className="h-3 w-3" strokeWidth={2.25} />
                                        Administrator
                                    </span>
                                )}
                            </div>
                        </div>

                        {user?.is_admin && (
                            <ListGroup>
                                <ListRow
                                    icon={{ icon: <Users className="h-4 w-4" />, tint: "#ff9500" }}
                                    label="Manage users"
                                    chevron
                                    onClick={() => navigate("/admin/users")}
                                />
                            </ListGroup>
                        )}

                        <ListGroup>
                            <ListRow
                                icon={{ icon: <LogOut className="h-4 w-4" />, tint: "#ff3b30" }}
                                label="Sign out"
                                destructive
                                onClick={handleLogout}
                            />
                        </ListGroup>
                    </>
                )}

                {activeSection === "appearance" && (
                    <ListGroup label="Appearance" footer="Choose a theme — these match Apple's system color palette.">
                        <li className="list-none p-4">
                            <ThemePickerCard inline />
                        </li>
                    </ListGroup>
                )}

                {activeSection === "library" && (
                    <>
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
                    </>
                )}

                {activeSection === "media" && (
                    <>
                        <MediaSourcesCard />
                        <OrganizerCard />
                    </>
                )}
            </ListPage>
        </div>
    )
}

function parseSettingsSection(value: string | null): SettingsSection {
    return settingsSections.some((section) => section.key === value)
        ? (value as SettingsSection)
        : "library"
}

function SettingsSectionTabs({
    active,
    onChange,
}: {
    active: SettingsSection
    onChange: (section: SettingsSection) => void
}) {
    return (
        <div className="sticky top-0 z-10 -mx-1 bg-background py-1">
            <div className="scrollbar-hide flex gap-1 overflow-x-auto rounded-full bg-secondary/55 p-1">
                {settingsSections.map((section) => (
                    <button
                        key={section.key}
                        type="button"
                        onClick={() => onChange(section.key)}
                        className={cn(
                            "h-9 shrink-0 rounded-full px-4 text-sm font-medium transition-colors",
                            active === section.key
                                ? "bg-card text-foreground shadow-sm"
                                : "text-muted-foreground hover:text-foreground",
                        )}
                    >
                        {section.label}
                    </button>
                ))}
            </div>
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
    const [pickerOpen, setPickerOpen] = useState(false)
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
                    readOnly
                    placeholder="/path/to/library"
                    wrapperClassName="flex-1"
                />
                <Button
                    type="button"
                    variant="plain"
                    onClick={() => setPickerOpen(true)}
                    className="shrink-0"
                >
                    Browse
                </Button>
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
            <ServerFilePicker
                open={pickerOpen}
                title="Choose library database or folder"
                select="any"
                initialPath={value}
                onClose={() => setPickerOpen(false)}
                onSelect={(path) => {
                    setValue(path)
                    setPickerOpen(false)
                }}
            />
        </div>
    )
}
