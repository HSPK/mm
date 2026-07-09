import { useEffect, useMemo, useState } from "react"
import { CheckCircle2, ChevronDown, KeyRound, Save, WandSparkles } from "lucide-react"
import { organizerRepo, type OrganizerConfig, type OrganizerSourceStatus } from "@/api/organizer"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { cn } from "@/lib/utils"
import {
    credentialFields,
    defaultScraperFallback,
    formatSourceName,
    languageOptions,
    lyricsSourceOptions,
    scraperOptionsForKind,
} from "./organizer-card-model"

export function OrganizerCard() {
    const [config, setConfig] = useState<OrganizerConfig | null>(null)
    const [language, setLanguage] = useState("zh-CN")
    const [chineseScript, setChineseScript] = useState("simplified")
    const [lyricsSource, setLyricsSource] = useState("lrclib")
    const [templates, setTemplates] = useState<Record<string, string>>({})
    const [defaultScrapers, setDefaultScrapers] = useState<Record<string, string>>({
        movies: "tmdb",
        tv: "tmdb",
        music: "musicbrainz",
    })
    const [credentials, setCredentials] = useState<Record<string, Record<string, string>>>({})
    const [expandedSource, setExpandedSource] = useState<string | null>(null)
    const [saving, setSaving] = useState<string | null>(null)
    const [sourceStatus, setSourceStatus] = useState<Record<string, SaveStatus>>({})

    useEffect(() => {
        void organizerRepo.getConfig()
            .then((cfg) => {
                setConfig(cfg)
                setLanguage(cfg.language)
                setChineseScript(cfg.chinese_script ?? "simplified")
                setLyricsSource(cfg.lyrics_source ?? "lrclib")
                setTemplates(cfg.templates)
                setDefaultScrapers(cfg.default_scrapers ?? { movies: "tmdb", tv: "tmdb", music: "musicbrainz" })
            })
            .catch(() => undefined)
    }, [])

    const sources = useMemo(() => config?.sources ?? [], [config])

    const saveDefaultsPatch = async (patch: Record<string, unknown>) => {
        setSaving("defaults")
        try {
            const next = await organizerRepo.updateConfig(patch)
            setConfig(next)
            setLanguage(next.language)
            setChineseScript(next.chinese_script ?? "simplified")
            setLyricsSource(next.lyrics_source ?? "lrclib")
            setTemplates(next.templates)
            setDefaultScrapers(next.default_scrapers)
        } catch {
            // The next explicit template update or selector change can retry.
        } finally {
            setSaving(null)
        }
    }

    const saveTemplates = async () => {
        if (Object.values(templates).some((value) => !value.trim())) {
            return
        }
        await saveDefaultsPatch({ templates })
    }

    const saveSource = async (source: string, enabled: boolean) => {
        setSaving(source)
        setSourceStatus((prev) => ({ ...prev, [source]: { state: "saving" } }))
        const enteredCredentials = credentials[source] ?? {}
        const credentialPatch = Object.fromEntries(
            Object.entries(enteredCredentials).filter(([, value]) => value.trim().length > 0),
        )
        try {
            const next = await organizerRepo.updateConfig({
                source,
                enabled,
                credentials: Object.keys(credentialPatch).length > 0 ? credentialPatch : undefined,
            })
            setConfig(next)
            setCredentials((prev) => ({ ...prev, [source]: {} }))
            setSourceStatus((prev) => ({ ...prev, [source]: { state: "saved" } }))
        } catch (err) {
            setSourceStatus((prev) => ({
                ...prev,
                [source]: { state: "error", message: err instanceof Error ? err.message : "Save failed" },
            }))
        } finally {
            setSaving(null)
        }
    }

    return (
        <div className="space-y-5">
            <Card>
                <CardContent className="space-y-5 pt-5">
                    <SectionIntro
                        icon={WandSparkles}
                        title="Organizer defaults"
                        description="Configure metadata language and output templates for movies, TV, and music."
                    />

                    <div className="space-y-1.5">
                        <label className="px-1 text-[13px] font-medium uppercase tracking-wider text-muted-foreground/90">
                            Metadata language
                        </label>
                        <Select
                            value={language}
                            onChange={(e) => {
                                setLanguage(e.target.value)
                                void saveDefaultsPatch({ language: e.target.value })
                            }}
                            className="h-11 rounded-xl border-0 bg-secondary/60"
                        >
                            {languageOptions.map((option) => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </Select>
                    </div>

                    <div className="space-y-1.5">
                        <label className="px-1 text-[13px] font-medium uppercase tracking-wider text-muted-foreground/90">
                            Chinese text normalization
                        </label>
                        <Select
                            value={chineseScript}
                            onChange={(e) => {
                                setChineseScript(e.target.value)
                                void saveDefaultsPatch({ chinese_script: e.target.value })
                            }}
                            className="h-11 rounded-xl border-0 bg-secondary/60"
                        >
                            <option value="simplified">简体中文</option>
                            <option value="traditional">繁體中文</option>
                        </Select>
                    </div>

                    <div className="space-y-1.5">
                        <label className="px-1 text-[13px] font-medium uppercase tracking-wider text-muted-foreground/90">
                            Lyrics source
                        </label>
                        <Select
                            value={lyricsSource}
                            onChange={(e) => {
                                setLyricsSource(e.target.value)
                                void saveDefaultsPatch({ lyrics_source: e.target.value })
                            }}
                            className="h-11 rounded-xl border-0 bg-secondary/60"
                        >
                            {lyricsSourceOptions.map((option) => (
                                <option key={option.value} value={option.value}>{option.label}</option>
                            ))}
                        </Select>
                    </div>

                    <div className="grid gap-3 md:grid-cols-3">
                        {(["movies", "tv", "music"] as const).map((kind) => (
                            <label key={kind} className="space-y-1.5">
                                <span className="px-1 text-[13px] font-medium uppercase tracking-wider text-muted-foreground/90">
                                    {kind === "tv" ? "Shows scraper" : `${kind} scraper`}
                                </span>
                                <Select
                                    value={defaultScrapers[kind] ?? defaultScraperFallback(kind)}
                                    onChange={(event) => {
                                        const next = { ...defaultScrapers, [kind]: event.target.value }
                                        setDefaultScrapers(next)
                                        void saveDefaultsPatch({ default_scrapers: next })
                                    }}
                                    className="h-11 rounded-xl border-0 bg-secondary/60"
                                >
                                    {scraperOptionsForKind(sources, kind).map((source) => (
                                        <option key={source.name} value={source.name}>
                                            {formatSourceName(source.name)}
                                        </option>
                                    ))}
                                </Select>
                            </label>
                        ))}
                    </div>

                    <div className="grid gap-3">
                        {["movie", "tv", "track"].map((key) => (
                            <Input
                                key={key}
                                label={`${key} template`}
                                value={templates[key] ?? ""}
                                onChange={(e) => setTemplates((prev) => ({ ...prev, [key]: e.target.value }))}
                                className="font-mono text-[12px]"
                            />
                        ))}
                    </div>

                    <div className="flex justify-end">
                        <Button size="sm" variant="tinted" loading={saving === "defaults"} onClick={() => void saveTemplates()}>
                            <Save className="h-4 w-4" />
                            Validate & update templates
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardContent className="space-y-4 pt-5">
                    <SectionIntro
                        icon={KeyRound}
                        title="Scraper sources"
                        description="Enable metadata providers and store credentials in the global config."
                    />

                    <div className="-mx-5 divide-y divide-border/55">
                        {sources.map((source, index) => (
                            <div key={source.name} className={index === 0 ? "border-t border-border/55" : undefined}>
                                <ScraperSourceRow
                                    source={source}
                                    credentials={credentials[source.name] ?? {}}
                                    saving={saving === source.name}
                                    status={sourceStatus[source.name] ?? { state: "idle" }}
                                    expanded={expandedSource === source.name}
                                    onToggleExpanded={() =>
                                        setExpandedSource((current) => current === source.name ? null : source.name)
                                    }
                                    onCredentialsChange={(field, value) => {
                                        setCredentials((prev) => ({
                                            ...prev,
                                            [source.name]: {
                                                ...(prev[source.name] ?? {}),
                                                [field]: value,
                                            },
                                        }))
                                    }}
                                    onSave={(enabled) => void saveSource(source.name, enabled)}
                                />
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}

type SaveStatus =
    | { state: "idle" | "saving" | "saved" }
    | { state: "error"; message: string }

function SectionIntro({
    icon: Icon,
    title,
    description,
    status,
}: {
    icon: typeof WandSparkles
    title: string
    description: string
    status?: SaveStatus
}) {
    return (
        <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-primary/15 text-primary">
                <Icon className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
                <h3 className="text-[15px] font-semibold">{title}</h3>
                <p className="mt-0.5 text-[13px] text-muted-foreground">{description}</p>
            </div>
            {status && <StatusSlot status={status} />}
        </div>
    )
}

function ScraperSourceRow({
    source,
    credentials,
    saving,
    status,
    expanded,
    onToggleExpanded,
    onCredentialsChange,
    onSave,
}: {
    source: OrganizerSourceStatus
    credentials: Record<string, string>
    saving: boolean
    status: SaveStatus
    expanded: boolean
    onToggleExpanded: () => void
    onCredentialsChange: (field: string, value: string) => void
    onSave: (enabled: boolean) => void
}) {
    const fields = credentialFields[source.name] ?? []
    return (
        <div>
            <div className="flex items-center gap-3 px-5 py-3.5">
                <button
                    type="button"
                    onClick={onToggleExpanded}
                    className="flex min-w-0 flex-1 items-center gap-3 text-left"
                >
                    <SourceIndicator
                        enabled={source.enabled}
                        configured={source.has_credentials}
                        pending={!source.implemented}
                    />
                    <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                            <h4 className="truncate text-[15px] font-semibold">{formatSourceName(source.name)}</h4>
                            {!source.implemented && <StatusPill active={false} label="Pending" />}
                            {source.has_credentials && <StatusPill active label="Configured" />}
                            <StatusSlot status={status} compact />
                        </div>
                        <p className="mt-0.5 truncate text-[12px] text-muted-foreground">{source.base_url}</p>
                    </div>
                    {fields.length > 0 && (
                        <ChevronDown
                            className={cn(
                                "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
                                expanded && "rotate-180",
                            )}
                        />
                    )}
                </button>
                <Switch
                    checked={source.enabled}
                    onChange={(enabled) => onSave(enabled)}
                    disabled={saving}
                />
            </div>

            {fields.length > 0 && expanded && (
                <div className="border-t border-border/55 bg-secondary/20 px-5 py-3.5">
                    <div className="grid gap-2 md:grid-cols-2">
                        {fields.map((field) => (
                            <Input
                                key={field}
                                leftIcon={<KeyRound className="h-4 w-4" />}
                                placeholder={`${field}${source.has_credentials ? " (leave blank to keep)" : ""}`}
                                value={credentials[field] ?? ""}
                                onChange={(e) => onCredentialsChange(field, e.target.value)}
                                className="bg-background/70"
                            />
                        ))}
                    </div>
                    <div className="mt-3 flex justify-end">
                        <Button
                            size="sm"
                            variant="plain"
                            loading={saving}
                            onClick={() => onSave(source.enabled)}
                        >
                            Save credentials
                        </Button>
                    </div>
                </div>
            )}
        </div>
    )
}

function SourceIndicator({
    enabled,
    configured,
    pending,
}: {
    enabled: boolean
    configured: boolean
    pending: boolean
}) {
    return (
        <div className="flex h-6 w-6 shrink-0 items-center justify-center">
            {configured ? (
                <CheckCircle2 className="h-4 w-4" strokeWidth={2.2} />
            ) : (
                <span
                    className={cn(
                        "h-2.5 w-2.5 rounded-full",
                        pending ? "bg-muted-foreground/45" : enabled ? "bg-primary" : "bg-muted-foreground/35",
                    )}
                />
            )}
        </div>
    )
}

function StatusPill({ active, label }: { active: boolean; label: string }) {
    return (
        <span
            className={cn(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                active ? "bg-primary/12 text-primary" : "bg-background/70 text-muted-foreground",
            )}
        >
            {active && <CheckCircle2 className="h-3 w-3" />}
            {label}
        </span>
    )
}

function StatusSlot({ status, compact }: { status: SaveStatus; compact?: boolean }) {
    if (status.state === "idle") return null
    const label = status.state === "saving"
        ? "Saving"
        : status.state === "saved"
            ? "Saved"
            : "Failed"
    const className = status.state === "error"
        ? "bg-destructive/10 text-destructive"
        : status.state === "saved"
            ? "bg-primary/10 text-primary"
            : "bg-secondary text-muted-foreground"
    return (
        <span
            title={status.state === "error" ? status.message : undefined}
            className={cn(
                "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                className,
                !compact && "mt-0.5",
            )}
        >
            {label}
        </span>
    )
}

function Switch({
    checked,
    disabled,
    onChange,
}: {
    checked: boolean
    disabled?: boolean
    onChange: (checked: boolean) => void
}) {
    return (
        <button
            type="button"
            disabled={disabled}
            onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                onChange(!checked)
            }}
            className={cn(
                "inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full px-3 text-[12px] font-semibold transition-colors disabled:opacity-50",
                checked
                    ? "bg-primary/12 text-primary hover:bg-primary/18"
                    : "bg-background/70 text-muted-foreground hover:bg-background",
            )}
            aria-pressed={checked}
        >
            <span
                className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    checked ? "bg-primary" : "bg-muted-foreground/45",
                )}
            />
            {checked ? "On" : "Off"}
        </button>
    )
}
