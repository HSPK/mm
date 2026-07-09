import { useCallback, useState } from "react"
import { DownloadCloud, FolderInput } from "lucide-react"
import { importRepo, type ImportPlanResponse } from "@/api/import"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { PageHeader } from "@/components/ui/page-header"
import { ServerFilePicker } from "@/components/server-file-picker"
import { toast } from "@/stores/toast"
import { cn } from "@/lib/utils"

export default function ImportPage() {
    const [source, setSource] = useState("")
    const [move, setMove] = useState(false)
    const [metadataMode, setMetadataMode] = useState("exiftool")
    const [plan, setPlan] = useState<ImportPlanResponse | null>(null)
    const [loading, setLoading] = useState<string | null>(null)
    const [operationStatus, setOperationStatus] = useState<{ state: "idle" | "error"; text?: string }>({ state: "idle" })
    const [pickerOpen, setPickerOpen] = useState(false)

    const run = useCallback(async <T,>(label: string, fn: () => Promise<T>) => {
        setLoading(label)
        setOperationStatus({ state: "idle" })
        try {
            return await fn()
        } catch (err) {
            setOperationStatus({
                state: "error",
                text: err instanceof Error ? err.message : "Import failed",
            })
            return null
        } finally {
            setLoading(null)
        }
    }, [])

    const planImport = useCallback(async () => {
        const result = await run("plan", () => importRepo.plan(source, move, metadataMode))
        if (result) setPlan(result)
    }, [metadataMode, move, run, source])

    const applyImport = useCallback(async () => {
        const result = await run("apply", () => importRepo.apply(source, move, metadataMode))
        if (result) {
            toast.success(result.message)
            setPlan(null)
        }
    }, [metadataMode, move, run, source])

    return (
        <div className="min-h-screen pb-24">
            <PageHeader title="Import" back />
            <div className="mx-auto grid max-w-7xl gap-5 p-4 sm:p-6 lg:grid-cols-[22rem_1fr]">
                <Card>
                    <CardContent className="space-y-5 pt-5">
                        <div>
                            <h2 className="text-[17px] font-semibold">Import media</h2>
                            <p className="mt-1 text-[13px] text-muted-foreground">
                                Copy or move new media into the active library using the configured import template.
                            </p>
                        </div>
                        <div className="space-y-1.5">
                            <label className="px-1 text-[13px] font-medium uppercase tracking-wider text-muted-foreground/90">
                                Source folder
                            </label>
                            <div className="flex gap-2">
                                <Input
                                    value={source}
                                    readOnly
                                    placeholder="/path/to/import"
                                    wrapperClassName="flex-1"
                                />
                                <Button variant="tinted" onClick={() => setPickerOpen(true)}>
                                    Browse
                                </Button>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="px-1 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
                                Metadata mode
                            </label>
                            <select
                                value={metadataMode}
                                onChange={(e) => setMetadataMode(e.target.value)}
                                className="h-10 w-full rounded-2xl bg-secondary/60 px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
                            >
                                <option value="exiftool">exiftool</option>
                                <option value="pillow">pillow</option>
                            </select>
                        </div>
                        <label className="flex cursor-pointer items-center gap-2 rounded-2xl bg-secondary/50 px-3 py-2 text-sm">
                            <input
                                type="checkbox"
                                checked={move}
                                onChange={(e) => setMove(e.target.checked)}
                                className="accent-primary"
                            />
                            Move files instead of copying
                        </label>
                        <div className="flex flex-wrap gap-2">
                            <Button
                                onClick={() => void planImport()}
                                disabled={!source.trim()}
                                loading={loading === "plan"}
                            >
                                <FolderInput className="h-4 w-4" />
                                Plan
                            </Button>
                            <Button
                                variant="tinted"
                                onClick={() => void applyImport()}
                                disabled={!plan || plan.importable === 0}
                                loading={loading === "apply"}
                            >
                                <DownloadCloud className="h-4 w-4" />
                                {move ? "Move" : "Copy"}
                            </Button>
                            {operationStatus.state === "error" && (
                                <span
                                    title={operationStatus.text}
                                    className="self-center rounded-full bg-destructive/10 px-2.5 py-1 text-[11px] font-semibold text-destructive"
                                >
                                    Failed
                                </span>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {plan ? (
                    <ImportPlanView plan={plan} move={move} />
                ) : (
                    <EmptyState
                        icon={FolderInput}
                        title="No import plan yet"
                        description="Enter a server-side source folder and create a plan before copying files."
                    />
                )}
            </div>
            <ServerFilePicker
                open={pickerOpen}
                title="Choose import folder"
                select="directory"
                initialPath={source}
                onClose={() => setPickerOpen(false)}
                onSelect={(path) => {
                    setSource(path)
                    setPlan(null)
                    setPickerOpen(false)
                }}
            />
        </div>
    )
}

function ImportPlanView({ plan, move }: { plan: ImportPlanResponse; move: boolean }) {
    return (
        <div className="space-y-5">
            <Card>
                <CardContent className="grid gap-3 pt-5 sm:grid-cols-5">
                    <Stat label="Discovered" value={plan.discovered} />
                    <Stat label="New" value={plan.new_files} />
                    <Stat label="Importable" value={plan.importable} />
                    <Stat label="Duplicates" value={plan.library_duplicates + plan.intra_duplicates} />
                    <Stat label="Errors" value={plan.errors} danger={plan.errors > 0} />
                </CardContent>
            </Card>
            <Card>
                <CardContent className="pt-5">
                    <div className="mb-4">
                        <h2 className="text-[17px] font-semibold">{move ? "Move" : "Copy"} plan</h2>
                        <p className="mt-1 text-[13px] text-muted-foreground">
                            Template: <span className="font-mono text-foreground/80">{plan.template}</span>
                        </p>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[760px] text-left text-sm">
                            <thead className="text-[11px] uppercase tracking-wider text-muted-foreground">
                                <tr className="border-b border-border">
                                    <th className="py-2 pr-3">Status</th>
                                    <th className="px-3 py-2">Type</th>
                                    <th className="px-3 py-2">Source</th>
                                    <th className="px-3 py-2">Destination</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border/50">
                                {plan.operations.map((op) => (
                                    <tr key={`${op.source}->${op.destination}`}>
                                        <td className="py-3 pr-3">
                                            <span className={cn(
                                                "rounded-full px-2 py-1 text-[11px] font-semibold uppercase tracking-wider",
                                                op.status === "ready"
                                                    ? "bg-primary/12 text-primary"
                                                    : "bg-secondary text-muted-foreground",
                                            )}>
                                                {op.status}
                                            </span>
                                        </td>
                                        <td className="px-3 py-3">{op.media_type}</td>
                                        <td className="max-w-[18rem] truncate px-3 py-3">{op.source}</td>
                                        <td className="max-w-[24rem] truncate px-3 py-3">{op.destination}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}

function Stat({ label, value, danger }: { label: string; value: number; danger?: boolean }) {
    return (
        <div className="rounded-2xl bg-secondary/45 p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
            <p className={cn("mt-1 text-2xl font-bold tabular-nums", danger && "text-destructive")}>
                {value.toLocaleString()}
            </p>
        </div>
    )
}
