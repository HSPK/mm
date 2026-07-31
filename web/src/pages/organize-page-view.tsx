import { Settings2 } from "lucide-react"
import type { Dispatch, SetStateAction } from "react"
import { type OrganizerCandidate, type OrganizerConfig } from "@/api/organizer"
import { EmptyState } from "@/components/ui/empty-state"
import { Spinner } from "@/components/ui/spinner"
import {
    type MediaRow,
    type MetadataEditValues,
    type OrganizerKind,
    type OrganizerKindSession,
    type ScrapeApplyOptions,
    actionKey,
    toggleKey,
} from "./organize-model"
import { MediaDetailModal } from "./organize-detail-modal"
import { MatchDialog as ScrapeMatchDialog } from "./organize-match-dialog"
import { MusicDetailsSidebar } from "./organize-music-details"
import { MediaTable } from "./organize-table"
import { OrganizerToolbar } from "./organize-toolbar"
import { folderOpenIcon } from "./organize-options"

export function OrganizePageView({
    activeKind,
    activeSession,
    activeOption,
    config,
    noSources,
    sourcePaths,
    rows,
    selectedRow,
    selectedRows,
    actionRows,
    loadedKinds,
    expandedKeys,
    loading,
    loadError,
    canScrape,
    canRename,
    searchQuery,
    sortMode,
    renameLogs,
    renameMenuOpen,
    detailsOpen,
    editingKey,
    matchDialogOpen,
    visibleScrapeDialogRows,
    scrapeDialogIndex,
    scrapeSource,
    scraperOptions,
    setDetailsOpen,
    setEditingKey,
    setSelectionAnchorKey,
    setSessionState,
    setExpandedKeys,
    setMatchDialogOpen,
    setScrapeDialogKeys,
    setScrapeDialogIndex,
    setScrapeSequential,
    setOperationStatus,
    updateActiveSession,
    updateSources,
    refreshItems,
    retrySetup,
    scrape,
    rename,
    toggleRenameMenu,
    undoRename,
    openMediaSettings,
    selectTableRow,
    saveEdit,
    selectCandidateForRow,
    applyScrape,
}: {
    activeKind: OrganizerKind
    activeSession: OrganizerKindSession
    activeOption: { label: string; icon: typeof Settings2 }
    config: OrganizerConfig | null
    noSources: boolean
    sourcePaths: string[]
    rows: MediaRow[]
    selectedRow: MediaRow | null
    selectedRows: MediaRow[]
    actionRows: MediaRow[]
    loadedKinds: string[]
    expandedKeys: string[]
    loading: string | null
    loadError: string | null
    canScrape: boolean
    canRename: boolean
    searchQuery: string
    sortMode: "name" | "year" | "incomplete"
    renameLogs: Array<{ batch_id: string; count: number; status: string; created_at: string }>
    renameMenuOpen: boolean
    detailsOpen: boolean
    editingKey: string | null
    matchDialogOpen: boolean
    visibleScrapeDialogRows: MediaRow[]
    scrapeDialogIndex: number
    scrapeSource: string
    scraperOptions: string[]
    setDetailsOpen: Dispatch<SetStateAction<boolean>>
    setEditingKey: Dispatch<SetStateAction<string | null>>
    setSelectionAnchorKey: Dispatch<SetStateAction<string | null>>
    setSessionState: Dispatch<SetStateAction<{ activeKind: OrganizerKind; sessions: Record<OrganizerKind, OrganizerKindSession> }>>
    setExpandedKeys: Dispatch<SetStateAction<string[]>>
    setMatchDialogOpen: Dispatch<SetStateAction<boolean>>
    setScrapeDialogKeys: Dispatch<SetStateAction<string[]>>
    setScrapeDialogIndex: Dispatch<SetStateAction<number>>
    setScrapeSequential: Dispatch<SetStateAction<boolean>>
    setOperationStatus: Dispatch<SetStateAction<{ state: "idle" | "error"; text?: string }>>
    updateActiveSession: (updater: (session: OrganizerKindSession) => OrganizerKindSession) => void
    updateSources: () => Promise<void>
    refreshItems: () => Promise<void>
    retrySetup: () => Promise<void>
    scrape: (target?: "missing" | "current" | "missing-metadata" | "missing-lyrics") => Promise<void>
    rename: () => Promise<void>
    toggleRenameMenu: () => void
    undoRename: (batchId: string) => Promise<void>
    openMediaSettings: () => void
    selectTableRow: (key: string, shiftKey: boolean, visibleRows: MediaRow[]) => void
    saveEdit: (row: MediaRow, values: MetadataEditValues) => Promise<void>
    selectCandidateForRow: (row: MediaRow, candidate: OrganizerCandidate) => void
    applyScrape: (rows: MediaRow[], options: ScrapeApplyOptions) => Promise<void>
}) {
    const toggleExpand = (key: string) => {
        if (expandedKeys.includes(key)) {
            setSelectionAnchorKey(null)
            updateActiveSession((session) => ({
                ...session,
                selectedKeys: session.selectedKeys.filter((item) => !item.startsWith(`${key}:season:`)),
            }))
        }
        setExpandedKeys((prev) => toggleKey(prev, key))
    }

    return (
        <div className="flex h-full min-h-0 flex-col overflow-hidden">
            <OrganizerToolbar
                activeKind={activeKind}
                sourceCount={sourcePaths.length}
                loading={loading}
                hasRows={rows.length > 0}
                hasSelected={selectedRows.length > 0}
                canScrape={canScrape}
                canRename={canRename}
                renameLogs={renameLogs}
                renameMenuOpen={renameMenuOpen}
                onKindChange={(kind) => {
                    setDetailsOpen(false)
                    setEditingKey(null)
                    setSelectionAnchorKey(null)
                    setOperationStatus({ state: "idle" })
                    setSessionState((prev) => ({ ...prev, activeKind: kind }))
                }}
                search={searchQuery}
                onSearchChange={(query) => updateActiveSession((session) => ({ ...session, query }))}
                sortMode={sortMode}
                onSortChange={(order) => updateActiveSession((session) => ({ ...session, order }))}
                onUpdateSources={() => void updateSources()}
                onScrape={() => void scrape(actionRows.length > 0 ? "current" : "missing")}
                onRename={() => void rename()}
                onToggleRenameMenu={toggleRenameMenu}
                onUndoRename={(batchId) => void undoRename(batchId)}
                onSettings={openMediaSettings}
            />
            <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 flex-col px-5 py-4 sm:px-7 sm:py-5">
                <OrganizerBody
                    activeKind={activeKind}
                    activeSession={activeSession}
                    activeOption={activeOption}
                    config={config}
                    noSources={noSources}
                    loadedKinds={loadedKinds}
                    rows={rows}
                    selectedRow={selectedRow}
                    sourcePaths={sourcePaths}
                    expandedKeys={expandedKeys}
                    onOpenMediaSettings={openMediaSettings}
                    onSelectTableRow={selectTableRow}
                    onToggleExpand={toggleExpand}
                    onOpenDetail={(key) => {
                        setEditingKey(null)
                        setDetailsOpen(true)
                        updateActiveSession((session) => ({ ...session, selectedKey: key }))
                    }}
                    onLyricsApplied={async () => {
                        await refreshItems()
                    }}
                    loadError={loadError}
                    refreshItems={refreshItems}
                    retrySetup={retrySetup}
                />
            </div>
            <MediaDetailModal
                open={activeKind !== "music" && detailsOpen && !!selectedRow}
                row={selectedRow}
                editing={!!selectedRow && editingKey === selectedRow.key}
                onEdit={() => {
                    if (selectedRow) setEditingKey((key) => key === selectedRow.key ? null : selectedRow.key)
                }}
                onClose={() => {
                    setDetailsOpen(false)
                    setEditingKey(null)
                }}
                onSaveEdit={saveEdit}
                onCancelEdit={() => setEditingKey(null)}
            />
            <ScrapeMatchDialog
                key={matchDialogOpen ? `${actionKey(visibleScrapeDialogRows)}:${scrapeDialogIndex}` : "closed"}
                open={matchDialogOpen}
                rows={visibleScrapeDialogRows}
                scraperSource={scrapeSource}
                scraperOptions={scraperOptions}
                scraperStatuses={config?.sources ?? []}
                scraperLanguage={config?.language ?? "zh-CN"}
                initialLoading={loading === "scrape"}
                applying={loading === "scrape-apply"}
                onClose={() => {
                    setMatchDialogOpen(false)
                    setScrapeDialogKeys([])
                    setScrapeDialogIndex(0)
                    setScrapeSequential(false)
                }}
                onSelectCandidate={selectCandidateForRow}
                onApply={applyScrape}
            />
        </div>
    )
}

function OrganizerBody({
    activeKind,
    activeSession,
    activeOption,
    config,
    noSources,
    loadedKinds,
    rows,
    selectedRow,
    sourcePaths,
    onOpenMediaSettings,
    onSelectTableRow,
    onToggleExpand,
    onOpenDetail,
    onLyricsApplied,
    loadError,
    refreshItems,
    retrySetup,
}: {
    activeKind: OrganizerKind
    activeSession: OrganizerKindSession
    activeOption: { label: string; icon: typeof Settings2 }
    config: OrganizerConfig | null
    noSources: boolean
    loadedKinds: string[]
    rows: MediaRow[]
    selectedRow: MediaRow | null
    sourcePaths: string[]
    expandedKeys: string[]
    onOpenMediaSettings: () => void
    onSelectTableRow: (key: string, shiftKey: boolean, visibleRows: MediaRow[]) => void
    onToggleExpand: (key: string) => void
    onOpenDetail: (key: string) => void
    onLyricsApplied: () => Promise<void>
    loadError: string | null
    refreshItems: () => Promise<void>
    retrySetup: () => Promise<void>
}) {
    if (config == null) {
        if (loadError) return <RetryState message={loadError} onRetry={retrySetup} />
        return <EmptyState icon={Settings2} title="Loading organizer settings" description="Media paths are inherited from Settings > Media." className="flex-1" />
    }
    if (!loadedKinds.includes(activeKind)) {
        if (loadError) return <RetryState message={loadError} onRetry={refreshItems} />
        return <div className="flex flex-1 items-center justify-center py-20"><Spinner /></div>
    }
    if (noSources && activeSession.items.length === 0) {
        return (
            <EmptyState
                icon={folderOpenIcon(activeKind)}
                title={`No ${activeOption.label.toLowerCase()} source folders`}
                description="Add source folders in Settings > Media before syncing."
                action={{ label: "Open Media settings", onClick: onOpenMediaSettings, variant: "primary" }}
                className="flex-1"
            />
        )
    }
    if (rows.length === 0) {
        const hasStoredItems = activeSession.items.length > 0
        return (
            <EmptyState
                icon={activeOption.icon}
                title={hasStoredItems ? `No matching ${activeOption.label.toLowerCase()}` : activeSession.scanned ? `No ${activeOption.label.toLowerCase()} found` : `Sync ${activeOption.label.toLowerCase()}`}
                description={hasStoredItems ? "Try a different search." : activeSession.scanned ? "No identifiable media was found in the configured source folders." : "Use Sync to parse media from configured folders."}
                className="flex-1"
            />
        )
    }
    if (activeKind === "music") {
        return (
            <div className="grid h-full min-h-0 gap-4 overflow-y-auto xl:grid-cols-[minmax(0,1fr)_34rem] xl:overflow-visible">
                <div className="min-h-[28rem] xl:min-h-0">
                    <MediaTable
                        rows={rows}
                        kind={activeKind}
                        selectedKey={selectedRow?.key ?? null}
                        selectedKeys={activeSession.selectedKeys}
                        onOpenDetail={() => undefined}
                        onSelect={onSelectTableRow}
                        onToggleExpand={() => undefined}
                    />
                </div>
                <MusicDetailsSidebar
                    row={selectedRow}
                    sourcePaths={sourcePaths}
                    defaultLyricsSource={config?.lyrics_source ?? "lrclib"}
                    onLyricsApplied={onLyricsApplied}
                />
            </div>
        )
    }
    return (
        <div className="h-full min-h-0">
            <MediaTable
                rows={rows}
                kind={activeKind}
                selectedKey={selectedRow?.key ?? null}
                selectedKeys={activeSession.selectedKeys}
                onOpenDetail={onOpenDetail}
                onSelect={onSelectTableRow}
                onToggleExpand={onToggleExpand}
            />
        </div>
    )
}

function RetryState({ message, onRetry }: { message: string, onRetry: () => Promise<void> }) {
    return <EmptyState icon={Settings2} title="Could not load organizer" description={message} action={{ label: "Retry", onClick: () => void onRetry(), variant: "primary" }} className="flex-1" />
}
