import { useEffect, useState } from "react"
import { FolderOpen } from "lucide-react"
import { organizerRepo } from "@/api/organizer"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ServerFilePicker } from "@/components/server-file-picker"
import { cn } from "@/lib/utils"

type MediaSourceKind = "movies" | "tv" | "music"

const labels: Record<MediaSourceKind, string> = {
    movies: "Movies",
    tv: "TV Series",
    music: "Music",
}

export function MediaSourcesCard() {
    const [sources, setSources] = useState<Record<MediaSourceKind, string[]>>({
        movies: [],
        tv: [],
        music: [],
    })
    const [pickerKind, setPickerKind] = useState<MediaSourceKind | null>(null)
    const [saving, setSaving] = useState(false)
    const [status, setStatus] = useState<"idle" | "saved" | "error">("idle")

    useEffect(() => {
        void organizerRepo.getConfig()
            .then((cfg) => {
                setSources({
                    movies: cfg.media_sources.movies ?? [],
                    tv: cfg.media_sources.tv ?? [],
                    music: cfg.media_sources.music ?? [],
                })
            })
            .catch(() => setStatus("error"))
    }, [])

    const save = async (nextSources: Record<MediaSourceKind, string[]>) => {
        setSaving(true)
        setStatus("idle")
        try {
            const next = await organizerRepo.updateConfig({ media_sources: nextSources })
            setSources({
                movies: next.media_sources.movies ?? [],
                tv: next.media_sources.tv ?? [],
                music: next.media_sources.music ?? [],
            })
            setStatus("saved")
        } catch {
            setStatus("error")
        } finally {
            setSaving(false)
        }
    }

    return (
        <Card>
            <CardContent className="space-y-5 pt-5">
                <div className="flex items-start gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-primary/15 text-primary">
                        <FolderOpen className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                        <h3 className="text-[15px] font-semibold">Media source folders</h3>
                        <p className="mt-0.5 text-[13px] text-muted-foreground">
                            Add server folders for Movies, TV Series, and Music without importing or copying files.
                        </p>
                    </div>
                    {(saving || status !== "idle") && (
                        <span
                            className={cn(
                                "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                                status === "error"
                                    ? "bg-destructive/10 text-destructive"
                                    : "bg-primary/10 text-primary",
                            )}
                        >
                            {saving ? "Saving" : status === "saved" ? "Saved" : "Failed"}
                        </span>
                    )}
                </div>

                <div className="grid gap-3">
                    {(["movies", "tv", "music"] as const).map((kind) => (
                        <MediaSourceList
                            key={kind}
                            kind={kind}
                            paths={sources[kind] ?? []}
                            onAdd={() => setPickerKind(kind)}
                            onRemove={(path) => {
                                const next = {
                                    ...sources,
                                    [kind]: (sources[kind] ?? []).filter((item) => item !== path),
                                }
                                setSources(next)
                                void save(next)
                            }}
                        />
                    ))}
                </div>

                <ServerFilePicker
                    open={pickerKind != null}
                    title={`Add ${pickerKind ? labels[pickerKind] : "Media"} source`}
                    select="directory"
                    onClose={() => setPickerKind(null)}
                    onSelect={(path) => {
                        if (!pickerKind) return
                        const next = {
                            ...sources,
                            [pickerKind]: Array.from(new Set([...(sources[pickerKind] ?? []), path])),
                        }
                        setSources(next)
                        setPickerKind(null)
                        void save(next)
                    }}
                />
            </CardContent>
        </Card>
    )
}

function MediaSourceList({
    kind,
    paths,
    onAdd,
    onRemove,
}: {
    kind: MediaSourceKind
    paths: string[]
    onAdd: () => void
    onRemove: (path: string) => void
}) {
    return (
        <div className="rounded-2xl bg-secondary/35 p-3">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <p className="text-sm font-semibold">{labels[kind]}</p>
                    <p className="text-[12px] text-muted-foreground">
                        {paths.length} server folder(s)
                    </p>
                </div>
                <Button size="sm" variant="plain" onClick={onAdd}>
                    Add
                </Button>
            </div>
            {paths.length > 0 && (
                <div className="mt-2 space-y-1">
                    {paths.map((path) => (
                        <div key={path} className="flex items-center gap-2 rounded-xl bg-background/70 px-2.5 py-2">
                            <span className="min-w-0 flex-1 truncate font-mono text-[12px] text-muted-foreground">
                                {path}
                            </span>
                            <button
                                type="button"
                                onClick={() => onRemove(path)}
                                className="rounded-full px-2 py-0.5 text-[11px] text-destructive hover:bg-destructive/10"
                            >
                                Remove
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
