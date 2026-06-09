import { useState } from "react"
import { Check, Database, FolderOpen, Save } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { LibraryInfo } from "@/api/library"
import { useCurrentLibrary } from "@/hooks/use-current-library"
import { previewImportTemplate, useImportTemplate } from "@/hooks/use-import-template"

export function LibraryCard() {
    const lib = useCurrentLibrary()
    const tmpl = useImportTemplate(lib.current)

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">Library</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
                {lib.current && <CurrentLibraryBanner library={lib.current} />}

                {lib.recent.length > 1 && (
                    <RecentLibraries
                        libraries={lib.recent.filter((l) => l.db_path !== lib.current?.db_path)}
                        disabled={lib.switching}
                        onSelect={lib.switchTo}
                    />
                )}

                <OpenLibraryInput
                    switching={lib.switching}
                    error={lib.error}
                    onSwitch={lib.switchTo}
                />

                <div className="border-t border-border" />

                <ImportTemplateSection tmpl={tmpl} />

                <div className="flex justify-end pt-1">
                    <Button onClick={tmpl.save} loading={tmpl.saving} size="sm">
                        {tmpl.saved ? (
                            <><Check className="mr-2 h-4 w-4" /> Saved</>
                        ) : tmpl.saving ? (
                            <>Saving…</>
                        ) : (
                            <><Save className="mr-2 h-4 w-4" /> Save</>
                        )}
                    </Button>
                </div>
            </CardContent>
        </Card>
    )
}

function CurrentLibraryBanner({ library }: { library: LibraryInfo }) {
    return (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-primary/5 border border-primary/20">
            <Database className="h-5 w-5 text-primary shrink-0" />
            <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold truncate">{library.name}</p>
                <p className="text-xs text-muted-foreground truncate">{library.db_path}</p>
            </div>
            <span className="text-[10px] font-medium text-primary bg-primary/10 px-2 py-0.5 rounded-full">Active</span>
        </div>
    )
}

function RecentLibraries({
    libraries,
    disabled,
    onSelect,
}: {
    libraries: LibraryInfo[]
    disabled: boolean
    onSelect: (path: string) => void
}) {
    return (
        <div className="space-y-2">
            <label className="text-sm font-medium">Recent Libraries</label>
            <div className="space-y-1.5">
                {libraries.map((lib) => (
                    <button
                        key={lib.db_path}
                        onClick={() => onSelect(lib.db_path)}
                        disabled={disabled}
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
        <div className="space-y-2">
            <label className="text-sm font-medium">Open Library</label>
            <p className="text-xs text-muted-foreground">
                Enter a server-side path to a library directory (containing mm.db) or a .db file.
            </p>
            <div className="flex gap-2">
                <Input
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    placeholder="/path/to/library or /path/to/mm.db"
                    onKeyDown={(e) => e.key === "Enter" && submit()}
                />
                <Button
                    onClick={submit}
                    disabled={!value.trim()}
                    loading={switching}
                    size="sm"
                    className="shrink-0"
                >
                    {switching ? "Switching" : "Switch"}
                </Button>
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
    )
}

function ImportTemplateSection({ tmpl }: { tmpl: ReturnType<typeof useImportTemplate> }) {
    return (
        <div className="space-y-2">
            <label className="text-sm font-medium">Import Directory Structure</label>
            <p className="text-xs text-muted-foreground">
                Template for organizing imported media into folders.
                Variables: <code className="text-[11px]">{"{year}"}</code>, <code className="text-[11px]">{"{month}"}</code>, <code className="text-[11px]">{"{day}"}</code>, <code className="text-[11px]">{"{camera}"}</code>, <code className="text-[11px]">{"{type}"}</code>, <code className="text-[11px]">{"{ext}"}</code>, <code className="text-[11px]">{"{original_name}"}</code>
            </p>
            <Input
                value={tmpl.template}
                onChange={(e) => tmpl.setTemplate(e.target.value)}
                placeholder="{year}/{year}-{month:02d}-{day:02d}/{original_name}{ext}"
                className="font-mono text-sm"
            />
            <p className="text-[11px] text-muted-foreground">
                Preview: <span className="font-mono text-foreground/70">{previewImportTemplate(tmpl.template)}</span>
            </p>
        </div>
    )
}
