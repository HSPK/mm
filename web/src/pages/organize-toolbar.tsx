import { ArrowDownUp, ChevronDown, ChevronRight, FileSearch, RefreshCw, Search } from "lucide-react"
import type { OrganizerRenameLogEntry } from "@/api/organizer"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { OrganizerKind, OrganizerSortMode } from "./organize-model"
import { organizerKindOptions } from "./organize-options"


export function OrganizerToolbar({
    activeKind,
    sourceCount,
    loading,
    hasRows,
    hasSelected,
    canScrape,
    canRename,
    renameLogs,
    renameMenuOpen,
    onKindChange,
    search,
    onSearchChange,
    sortMode,
    onSortChange,
    onUpdateSources,
    onScrape,
    onRename,
    onToggleRenameMenu,
    onUndoRename,
    onSettings,
}: {
    activeKind: OrganizerKind
    sourceCount: number
    loading: string | null
    hasRows: boolean
    hasSelected: boolean
    canScrape: boolean
    canRename: boolean
    renameLogs: OrganizerRenameLogEntry[]
    renameMenuOpen: boolean
    onKindChange: (kind: OrganizerKind) => void
    search: string
    onSearchChange: (value: string) => void
    sortMode: OrganizerSortMode
    onSortChange: (mode: OrganizerSortMode) => void
    onUpdateSources: () => void
    onScrape: () => void
    onRename: () => void
    onToggleRenameMenu: () => void
    onUndoRename: (batchId: string) => void
    onSettings: () => void
}) {
    return (
        <div className="sticky top-0 z-20 shrink-0 border-b border-border/70 bg-background">
            <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6">
                <div className="flex rounded-2xl bg-secondary/55 p-1">
                    {organizerKindOptions.map(({ kind, label, icon: Icon }) => {
                        const active = activeKind === kind
                        return (
                            <button
                                key={kind}
                                type="button"
                                onClick={() => onKindChange(kind)}
                                className={cn(
                                    "flex h-9 items-center gap-2 rounded-xl px-3 text-sm font-semibold transition-colors",
                                    active ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
                                )}
                                aria-pressed={active}
                            >
                                <Icon className="h-4 w-4" />
                                <span>{label}</span>
                            </button>
                        )
                    })}
                </div>
                <div className="flex min-w-0 flex-1 items-center gap-2">
                    <label className="relative min-w-0 max-w-md flex-1">
                        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <input
                            type="search"
                            value={search}
                            onChange={(event) => onSearchChange(event.target.value)}
                            placeholder="Search title, artist, album"
                            className="h-9 w-full rounded-full border border-border/70 bg-secondary/40 pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-muted-foreground/50 focus:border-ring/45 focus:ring-2 focus:ring-ring/15"
                        />
                    </label>
                    <div className="relative inline-flex items-center">
                        <ArrowDownUp className="pointer-events-none absolute left-2.5 h-3.5 w-3.5 text-muted-foreground" />
                        <select
                            value={sortMode}
                            onChange={(event) => onSortChange(event.target.value as OrganizerSortMode)}
                            aria-label="Sort"
                            className="h-9 appearance-none rounded-full border border-border/70 bg-secondary/40 pl-8 pr-7 text-sm font-medium outline-none focus:border-ring/45"
                        >
                            <option value="name">Name</option>
                            <option value="year">Year</option>
                            <option value="incomplete">Incomplete first</option>
                        </select>
                        <ChevronDown className="pointer-events-none absolute right-2.5 h-3.5 w-3.5 text-muted-foreground" />
                    </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <Button
                        size="sm"
                        variant="tinted"
                        onClick={onUpdateSources}
                        disabled={sourceCount === 0 || loading === "update-sources"}
                        aria-busy={loading === "update-sources" || undefined}
                    >
                        <RefreshCw className={cn("h-4 w-4", loading === "update-sources" && "animate-spin")} />
                        Sync
                    </Button>
                    <Button
                        size="sm"
                        variant="tinted"
                        onClick={onScrape}
                        disabled={!hasRows || !canScrape || loading === "scrape"}
                        aria-busy={loading === "scrape" || undefined}
                    >
                        <FileSearch className="h-4 w-4" />
                        Scrape
                    </Button>
                    <RenameActions
                        hasSelected={hasSelected}
                        canRename={canRename}
                        loading={loading}
                        renameLogs={renameLogs}
                        renameMenuOpen={renameMenuOpen}
                        onRename={onRename}
                        onToggleRenameMenu={onToggleRenameMenu}
                        onUndoRename={onUndoRename}
                    />
                    {sourceCount === 0 && (
                        <Button size="sm" variant="plain" onClick={onSettings}>
                            Settings
                        </Button>
                    )}
                </div>
            </div>
        </div>
    )
}

function RenameActions({
    hasSelected,
    canRename,
    loading,
    renameLogs,
    renameMenuOpen,
    onRename,
    onToggleRenameMenu,
    onUndoRename,
}: {
    hasSelected: boolean
    canRename: boolean
    loading: string | null
    renameLogs: OrganizerRenameLogEntry[]
    renameMenuOpen: boolean
    onRename: () => void
    onToggleRenameMenu: () => void
    onUndoRename: (batchId: string) => void
}) {
    return (
        <div className="relative inline-flex">
            <button
                type="button"
                onClick={onToggleRenameMenu}
                className="inline-flex h-8 w-8 items-center justify-center rounded-l-full bg-primary text-primary-foreground transition-opacity hover:opacity-90"
                aria-label="Rename history"
                aria-expanded={renameMenuOpen}
            >
                <ChevronDown className={cn("h-4 w-4 transition-transform", renameMenuOpen && "rotate-180")} />
            </button>
            <button
                type="button"
                onClick={onRename}
                disabled={!hasSelected || !canRename || loading === "rename" || loading === "rename-apply"}
                aria-disabled={!hasSelected || !canRename}
                className={cn(
                    "inline-flex h-8 items-center justify-center rounded-r-full border-l border-primary-foreground/20 bg-primary pl-3 pr-4 text-[13px] font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:pointer-events-none disabled:opacity-80",
                    (!hasSelected || !canRename) && "cursor-default hover:opacity-100",
                )}
            >
                Rename
            </button>
            {renameMenuOpen && <RenameHistory renameLogs={renameLogs} onUndoRename={onUndoRename} />}
        </div>
    )
}

function RenameHistory({
    renameLogs,
    onUndoRename,
}: {
    renameLogs: OrganizerRenameLogEntry[]
    onUndoRename: (batchId: string) => void
}) {
    const applied = renameLogs.filter((log) => log.status === "applied")
    return (
        <div className="absolute right-0 top-10 z-30 w-72 overflow-hidden rounded-2xl border border-border bg-popover shadow-xl">
            <div className="border-b border-border px-3 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Rename history
            </div>
            {applied.length === 0 ? (
                <div className="px-3 py-3 text-sm text-muted-foreground">Empty</div>
            ) : applied.map((log) => (
                <button
                    key={log.batch_id}
                    type="button"
                    onClick={() => onUndoRename(log.batch_id)}
                    className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-secondary/45"
                >
                    <span className="min-w-0">
                        <span className="block truncate font-medium">Undo rename</span>
                        <span className="block truncate text-xs text-muted-foreground">
                            {log.count} file(s) · {formatDateTime(log.created_at)}
                        </span>
                    </span>
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                </button>
            ))}
        </div>
    )
}

function formatDateTime(value: string) {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString()
}
