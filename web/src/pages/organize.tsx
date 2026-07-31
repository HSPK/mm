import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
    organizerRepo,
    type OrganizerCandidate,
    type OrganizerConfig,
    type OrganizerCapabilities,
    type OrganizerRenameLogEntry,
} from "@/api/organizer"
import { jobsRepo } from "@/api/jobs"
import { notify } from "@/stores/notifications"
import {
    type MediaRow,
    type MetadataEditValues,
    type OrganizerKind,
    type OrganizerKindSession,
    type OrganizerSessionState,
    type ScrapeApplyOptions,
    type ScrapeTarget,
    ORGANIZER_SESSION_KEY,
    actionKey,
    buildRows,
    errorMessage,
    filterAndSortRows,
    loadSession,
    mergeMatches,
    metadataPatchRequests,
    persistedViewState,
    renameItemsForRows,
    scrapeEmptyMessage,
    scrapeItemsForRows,
    scrapeResultMessage,
    scrapeTargetRows,
    scraperForKind,
    scraperOptionsForKind,
    selectedCandidateMap,
    visibleRangeKeys,
} from "./organize-model"
import { OrganizePageView } from "./organize-page-view"
import { optionForKind } from "./organize-options"
import { useOrganizerJob } from "./use-organizer-job"
export default function OrganizePage() {
    const navigate = useNavigate()
    const [config, setConfig] = useState<OrganizerConfig | null>(null)
    const [capabilities, setCapabilities] = useState<OrganizerCapabilities | null>(null)
    const [sessionState, setSessionState] = useState<OrganizerSessionState>(() => loadSession())
    const [loading, setLoading] = useState<string | null>(null)
    const [, setOperationStatus] = useState<{ state: "idle" | "error"; text?: string }>({ state: "idle" })
    const [editingKey, setEditingKey] = useState<string | null>(null)
    const [detailsOpen, setDetailsOpen] = useState(false)
    const [matchDialogOpen, setMatchDialogOpen] = useState(false)
    const [scrapeDialogKeys, setScrapeDialogKeys] = useState<string[]>([])
    const [scrapeDialogIndex, setScrapeDialogIndex] = useState(0)
    const [scrapeSequential, setScrapeSequential] = useState(false)
    const [expandedKeys, setExpandedKeys] = useState<string[]>([])
    const [selectionAnchorKey, setSelectionAnchorKey] = useState<string | null>(null)
    const [loadedKinds, setLoadedKinds] = useState<string[]>([])
    const [loadError, setLoadError] = useState<string | null>(null)
    const [renameLogs, setRenameLogs] = useState<OrganizerRenameLogEntry[]>([])
    const [renameMenuOpen, setRenameMenuOpen] = useState(false)
    const itemRequests = useRef<Record<OrganizerKind, { generation: number, controller?: AbortController }>>({
        movies: { generation: 0 }, tv: { generation: 0 }, music: { generation: 0 },
    })
    const { isCommandActive, runJob } = useOrganizerJob()
    const activeKind = sessionState.activeKind
    const activeSession = sessionState.sessions[activeKind]
    const activeOption = optionForKind(activeKind)
    const sourcePaths = useMemo(
        () => config?.media_sources?.[activeKind] ?? [],
        [activeKind, config],
    )
    const scraperOptions = useMemo(
        () => scraperOptionsForKind(config, capabilities, activeKind),
        [activeKind, capabilities, config],
    )
    const scrapeSource = scraperForKind(
        activeKind,
        activeSession.source || config?.default_scrapers?.[activeKind] || "",
        scraperOptions,
    )
    const catalogRows = useMemo(
        () => buildRows(activeSession.items, activeSession.matches, activeSession.selectedCandidates, activeKind, expandedKeys),
        [activeKind, activeSession.items, activeSession.matches, activeSession.selectedCandidates, expandedKeys],
    )
    const rows = useMemo(
        () => filterAndSortRows(catalogRows, activeSession.query ?? "", activeSession.order ?? "name"),
        [activeSession.order, activeSession.query, catalogRows],
    )
    const scrapeDialogRows = useMemo(
        () => scrapeDialogKeys
            .map((key) => rows.find((row) => row.key === key))
            .filter((row): row is MediaRow => Boolean(row)),
        [rows, scrapeDialogKeys],
    )
    const visibleScrapeDialogRows = scrapeSequential
        ? scrapeDialogRows.slice(scrapeDialogIndex, scrapeDialogIndex + 1)
        : scrapeDialogRows
    const selectedRow = rows.find((row) => row.key === activeSession.selectedKey) ?? null
    const selectedRows = useMemo(() => {
        const keys = new Set(activeSession.selectedKeys)
        return rows.filter((row) => keys.has(row.key))
    }, [activeSession.selectedKeys, rows])
    const actionRows = useMemo(
        () => selectedRows,
        [selectedRows],
    )
    const actionItems = useMemo(() => renameItemsForRows(activeKind, actionRows), [activeKind, actionRows])
    const actionPlanKey = useMemo(
        () => actionRows.length > 0 ? actionKey(actionRows) : null,
        [actionRows],
    )
    const noSources = config != null && sourcePaths.length === 0
    const activeCapabilities = useMemo(() => {
        const mediaTypes = activeKind === "movies" ? ["movie"] : activeKind === "tv" ? ["tv"] : ["track", "album"]
        return capabilities?.media_types.filter((capability) => mediaTypes.includes(capability.media_type)) ?? []
    }, [activeKind, capabilities])
    const canScrape = activeCapabilities.some((capability) => capability.scrapers.length > 0)
    const canRename = activeCapabilities.some((capability) => capability.rename)
    const loadOrganizerSetup = useCallback(async () => {
        setLoadError(null)
        try {
            const [nextConfig, nextCapabilities] = await Promise.all([organizerRepo.getConfig(), organizerRepo.capabilities()])
            setConfig(nextConfig)
            setCapabilities(nextCapabilities)
        } catch (err) {
            setOperationStatus({
                state: "error",
                text: err instanceof Error ? err.message : "Could not load organizer config",
            })
            setLoadError(err instanceof Error ? err.message : "Could not load organizer config")
        }
    }, [])
    useEffect(() => {
        const id = window.setTimeout(() => {
            void loadOrganizerSetup()
        }, 0)
        return () => window.clearTimeout(id)
    }, [loadOrganizerSetup])
    const refreshRenameLogs = useCallback(async () => {
        try {
            setRenameLogs(await organizerRepo.renameLogs(8))
        } catch {
            setRenameLogs([])
        }
    }, [])
    useEffect(() => {
        try {
            localStorage.setItem(ORGANIZER_SESSION_KEY, JSON.stringify(persistedViewState(sessionState)))
        } catch {
            localStorage.removeItem(ORGANIZER_SESSION_KEY)
        }
    }, [sessionState])
    const updateKindSession = useCallback((
        kind: OrganizerKind,
        updater: (session: OrganizerKindSession) => OrganizerKindSession,
    ) => {
        setSessionState((prev) => ({
            ...prev,
            sessions: {
                ...prev.sessions,
                [kind]: updater(prev.sessions[kind]),
            },
        }))
    }, [])
    const updateActiveSession = useCallback(
        (updater: (session: OrganizerKindSession) => OrganizerKindSession) => {
            updateKindSession(activeKind, updater)
        },
        [activeKind, updateKindSession],
    )
    const loadItems = useCallback(async (kind: OrganizerKind) => {
        const request = itemRequests.current[kind]
        request.controller?.abort()
        request.generation += 1
        const generation = request.generation
        const controller = new AbortController()
        request.controller = controller
        setLoadError(null)
        try {
            const response = await organizerRepo.items({ kind }, { signal: controller.signal })
            if (itemRequests.current[kind].generation !== generation) return
            updateKindSession(kind, (current) => ({
                ...current,
                items: response.items,
                scanned: current.scanned || response.items.length > 0,
            }))
            setLoadedKinds((prev) => Array.from(new Set([...prev, kind])))
        } catch (error) {
            if (controller.signal.aborted || itemRequests.current[kind].generation !== generation) return
            setLoadError(errorMessage(error))
        }
    }, [updateKindSession])
    useEffect(() => {
        const request = itemRequests.current[activeKind]
        const timer = window.setTimeout(() => void loadItems(activeKind), 0)
        return () => {
            window.clearTimeout(timer)
            request.controller?.abort()
        }
    }, [activeKind, loadItems])
    const run = useCallback(async <T,>(label: string, fn: () => Promise<T>) => {
        setLoading(label)
        setOperationStatus({ state: "idle" })
        try {
            return await fn()
        } catch (err) {
            const message = err instanceof Error ? err.message : "Organizer operation failed"
            setOperationStatus({ state: "error", text: message })
            notify.error("Operation failed", message)
            return null
        } finally {
            setLoading(null)
        }
    }, [])
    const updateSources = useCallback(async () => {
        const kind = activeKind
        const paths = sourcePaths
        const recursive = activeSession.recursive
        const job = await runJob("sync", "Sync queued", `${paths.length} source folder(s)`, (key) =>
            jobsRepo.createSyncJob(paths, recursive, key))
        if (!job) return
        await loadItems(kind)
        const completed = job.status === "done" || job.status === "completed_with_errors"
        if (!completed) return
        updateKindSession(kind, (session) => ({
            ...session,
            scanned: true,
            renamePlan: null,
            renamePlanKey: null,
        }))
    }, [activeKind, activeSession.recursive, loadItems, runJob, sourcePaths, updateKindSession])
    const runScrapeJob = useCallback(async (targetRows: MediaRow[], options: ScrapeApplyOptions) => {
        const kind = activeKind
        const source = scrapeSource
        const batches = options.sequentialRows ? targetRows.map((row) => [row]) : [targetRows]
        let done = 0
        let failed = 0
        try {
            for (const batch of batches) {
                const items = batch.flatMap((row) => row.files)
                const finished = await runJob("scrape", "Scrape queued", `${done + failed + 1}/${batches.length}: ${batch[0]?.title ?? "Album"}`, (key) => jobsRepo.createScrapeJob(items, {
                    source,
                    language: options.language ?? config?.language,
                    overwrite: !options.missingOnly,
                    selectedCandidates: selectedCandidateMap(batch),
                }, key))
                if (!finished || finished.status === "error" || finished.status === "canceled" || finished.status === "completed_with_errors") failed += 1
                else done += 1
                await loadItems(kind)
            }
            if (failed > 0) notify.info("Scrape completed with errors", `${done} album(s) completed, ${failed} skipped or failed`)
        } catch (error) {
            notify.error("Scrape failed", errorMessage(error))
        }
    }, [activeKind, config?.language, loadItems, runJob, scrapeSource])
    const scrape = useCallback(async (target: ScrapeTarget = "missing") => {
        const kind = activeKind
        const baseRows = actionRows.length > 0 ? actionRows : rows
        const targetRows = scrapeTargetRows(kind, baseRows, target)
        if (targetRows.length === 0) {
            notify.info("Nothing to scrape", scrapeEmptyMessage(target, kind))
            return
        }
        const sequential = actionRows.length > 0
        if (!sequential && target === "missing") {
            await runScrapeJob(targetRows, { missingOnly: true, sequentialRows: true })
            return
        }
        setScrapeDialogKeys(targetRows.map((row) => row.key))
        setScrapeDialogIndex(0)
        setScrapeSequential(sequential)
        const targetItems = scrapeItemsForRows(kind, targetRows, actionItems, activeSession.items)
        setMatchDialogOpen(true)
        const result = await run("scrape", () => organizerRepo.match(targetItems, scrapeSource, 5))
        if (!result) return
        updateKindSession(kind, (session) => mergeMatches(session, result))
    }, [
        actionItems,
        actionRows,
        activeKind,
        activeSession.items,
        rows,
        run,
        runScrapeJob,
        scrapeSource,
        updateKindSession,
    ])
    const rename = useCallback(async () => {
        if (actionItems.length === 0 || !actionPlanKey) return
        const kind = activeKind
        const finished = await runJob("rename", "Rename queued", `${actionItems.length} file(s)`, (key) =>
            jobsRepo.createRenameJob(actionItems, {}, key))
        if (!finished) return
        await refreshRenameLogs()
        await loadItems(kind)
        const counts = renameResultMessage(finished)
        if (counts) notify.info(finished.status === "completed_with_errors" ? "Rename partially completed" : "Rename result", counts)
        updateKindSession(kind, (session) => ({
            ...session,
            selectedKey: null,
            selectedKeys: [],
            renamePlan: null,
            renamePlanKey: null,
        }))
    }, [actionItems, actionPlanKey, activeKind, loadItems, refreshRenameLogs, runJob, updateKindSession])
    const undoRename = useCallback(async (batchId: string) => {
        const result = await run("rename-undo", () => organizerRepo.renameUndo(batchId))
        if (!result) return
        notify.success("Undo complete", result.message)
        setRenameMenuOpen(false)
        await refreshRenameLogs()
        const kind = activeKind
        await loadItems(kind)
        updateKindSession(kind, (session) => ({
            ...session,
            selectedKey: null,
            selectedKeys: [],
            renamePlan: null,
            renamePlanKey: null,
        }))
    }, [activeKind, loadItems, refreshRenameLogs, run, updateKindSession])
    const toggleRenameMenu = useCallback(() => {
        setRenameMenuOpen((open) => {
            if (!open) void refreshRenameLogs()
            return !open
        })
    }, [refreshRenameLogs])
    const selectTableRow = useCallback((key: string, shiftKey: boolean, visibleRows: MediaRow[]) => {
        const nextKeys = shiftKey
            ? visibleRangeKeys(visibleRows, selectionAnchorKey, key)
            : activeSession.selectedKeys.includes(key)
                ? activeSession.selectedKeys.filter((item) => item !== key)
                : [key]
        if (!shiftKey) setSelectionAnchorKey(nextKeys.length > 0 ? key : null)
        else if (!selectionAnchorKey) setSelectionAnchorKey(key)
        updateActiveSession((session) => ({
            ...session,
            selectedKey: nextKeys.includes(key) ? key : nextKeys[0] ?? null,
            selectedKeys: nextKeys,
            renamePlan: null,
            renamePlanKey: null,
        }))
    }, [activeSession.selectedKeys, selectionAnchorKey, updateActiveSession])
    const saveEdit = useCallback(async (row: MediaRow, values: MetadataEditValues) => {
        if (row.files.some((item) => !item.item_uid || item.revision == null)) {
            notify.error("Cannot save legacy item", "This projection has no persistent item identity. Sync it again before saving.")
            return
        }
        try {
            const patchedItems = await organizerRepo.patchItems(
                metadataPatchRequests(row, values),
            )
            const patchedByUid = new Map(
                patchedItems.map((item) => [item.item_uid, item]),
            )
            updateActiveSession((session) => ({
                ...session,
                items: session.items.map((current) => (
                    patchedByUid.get(current.item_uid) ?? current
                )),
                renamePlan: null,
                renamePlanKey: null,
            }))
            setEditingKey(null)
            notify.success("Projection saved", values.writeNfo ? "Saved and wrote NFO." : "Saved to the organizer projection only.")
        } catch (error) {
            const status = (error as { response?: { status?: number } }).response?.status
            if (status === 409) {
                await loadItems(activeKind)
                notify.error("Revision conflict", "The item changed elsewhere. The latest projection was reloaded.")
                return
            }
            await loadItems(activeKind)
            notify.error("Could not save projection", errorMessage(error))
        }
    }, [activeKind, loadItems, updateActiveSession])
    const openMediaSettings = useCallback(() => {
        navigate("/settings?section=media")
    }, [navigate])
    const selectCandidateForRow = useCallback((row: MediaRow, candidate: OrganizerCandidate) => {
        updateActiveSession((session) => {
            const selectedCandidates = { ...session.selectedCandidates }
            for (const file of row.files) selectedCandidates[file.item_uid ?? file.path] = candidate
            return {
                ...session,
                selectedCandidates,
                renamePlan: null,
                renamePlanKey: null,
            }
        })
    }, [updateActiveSession])
    const applyScrape = useCallback(async (targetRows: MediaRow[], options: ScrapeApplyOptions) => {
        const kind = activeKind
        const source = scrapeSource
        setMatchDialogOpen(false)
        const items = targetRows.flatMap((row) => row.files)
        const selectedCandidates = selectedCandidateMap(targetRows)
        const finished = await runJob("scrape", "Scrape queued", `${items.length} file(s) queued`, (key) =>
            jobsRepo.createScrapeJob(items, {
                source,
                language: options.language ?? config?.language,
                overwrite: !options.missingOnly,
                selectedCandidates,
            }, key))
        if (!finished) return
        await loadItems(kind)
        if (finished.status === "completed_with_errors") notify.info("Scrape partially completed", scrapeResultMessage(finished))
        if (scrapeSequential && scrapeDialogIndex < scrapeDialogKeys.length - 1) {
            setScrapeDialogIndex((index) => index + 1)
            setMatchDialogOpen(true)
        } else {
            setScrapeDialogKeys([])
            setScrapeDialogIndex(0)
            setScrapeSequential(false)
        }
    }, [
        activeKind,
        config?.language,
        scrapeDialogIndex,
        scrapeDialogKeys.length,
        scrapeSource,
        scrapeSequential,
        loadItems,
        runJob,
    ])
        return (
        <OrganizePageView
            activeKind={activeKind}
            activeSession={activeSession}
            activeOption={activeOption}
            config={config}
            noSources={noSources}
            sourcePaths={sourcePaths}
            rows={rows}
            selectedRow={selectedRow}
            selectedRows={selectedRows}
            actionRows={actionRows}
            loadedKinds={loadedKinds}
            expandedKeys={expandedKeys}
            loading={loading ?? (isCommandActive("sync") ? "update-sources" : isCommandActive("scrape") ? "scrape" : isCommandActive("rename") ? "rename" : null)}
            loadError={loadError}
            canScrape={canScrape}
            canRename={canRename}
            searchQuery={activeSession.query ?? ""}
            sortMode={activeSession.order ?? "name"}
            renameLogs={renameLogs}
            renameMenuOpen={renameMenuOpen}
            detailsOpen={detailsOpen}
            editingKey={editingKey}
            matchDialogOpen={matchDialogOpen}
            visibleScrapeDialogRows={visibleScrapeDialogRows}
            scrapeDialogIndex={scrapeDialogIndex}
            scrapeSource={scrapeSource}
            scraperOptions={scraperOptions}
            setDetailsOpen={setDetailsOpen}
            setEditingKey={setEditingKey}
            setSelectionAnchorKey={setSelectionAnchorKey}
            setSessionState={setSessionState}
            setExpandedKeys={setExpandedKeys}
            setMatchDialogOpen={setMatchDialogOpen}
            setScrapeDialogKeys={setScrapeDialogKeys}
            setScrapeDialogIndex={setScrapeDialogIndex}
            setScrapeSequential={setScrapeSequential}
            setOperationStatus={setOperationStatus}
            updateActiveSession={updateActiveSession}
            updateSources={updateSources}
            refreshItems={() => loadItems(activeKind)}
            retrySetup={loadOrganizerSetup}
            scrape={scrape}
            rename={rename}
            toggleRenameMenu={toggleRenameMenu}
            undoRename={undoRename}
            openMediaSettings={openMediaSettings}
            selectTableRow={selectTableRow}
            saveEdit={saveEdit}
            selectCandidateForRow={selectCandidateForRow}
            applyScrape={applyScrape}
        />
    )
}

function renameResultMessage(job: import("@/api/jobs").Job) {
    const result = job.result ?? {}
    const completed = result.completed ?? result.renamed ?? 0
    const skipped = result.skipped ?? 0
    const conflicts = result.conflicts ?? 0
    const failed = result.failed ?? 0
    return `Completed ${completed}, skipped ${skipped}, conflicts ${conflicts}, failed ${failed}`
}
