import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
    organizerRepo,
    type OrganizerCandidate,
    type OrganizerConfig,
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
    itemBelongsToKind,
    loadSession,
    mergeMatches,
    persistedViewState,
    pollOrganizerJob,
    renameItemsForRows,
    scrapeEmptyMessage,
    scrapeItemsForRows,
    scrapeResultMessage,
    scrapeTargetRows,
    scraperForKind,
    scraperOptionsForKind,
    selectedCandidateMap,
    splitList,
    visibleRangeKeys,
} from "./organize-model"
import { OrganizePageView } from "./organize-page-view"
import { optionForKind } from "./organize-toolbar"
export default function OrganizePage() {
    const navigate = useNavigate()
    const [config, setConfig] = useState<OrganizerConfig | null>(null)
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
    const [renameLogs, setRenameLogs] = useState<OrganizerRenameLogEntry[]>([])
    const [renameMenuOpen, setRenameMenuOpen] = useState(false)
    const activeKind = sessionState.activeKind
    const activeSession = sessionState.sessions[activeKind]
    const activeOption = optionForKind(activeKind)
    const sourcePaths = useMemo(
        () => config?.media_sources?.[activeKind] ?? [],
        [activeKind, config],
    )
    const scraperOptions = useMemo(
        () => scraperOptionsForKind(config, activeKind),
        [activeKind, config],
    )
    const scrapeSource = scraperForKind(
        activeKind,
        activeSession.source || config?.default_scrapers?.[activeKind] || "",
        scraperOptions,
    )
    const rows = useMemo(
        () => buildRows(activeSession.items, activeSession.matches, activeSession.selectedCandidates, activeKind, expandedKeys),
        [activeKind, activeSession.items, activeSession.matches, activeSession.selectedCandidates, expandedKeys],
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
    useEffect(() => {
        void organizerRepo.getConfig().then(setConfig).catch((err) => {
            setOperationStatus({
                state: "error",
                text: err instanceof Error ? err.message : "Could not load organizer config",
            })
        })
    }, [])
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
    useEffect(() => {
        if (loadedKinds.includes(activeKind)) return
        let cancelled = false
        void organizerRepo.items(activeKind)
            .then((items) => {
                if (cancelled) return
                updateKindSession(activeKind, (session) => ({
                    ...session,
                    items,
                    scanned: items.length > 0,
                    selectedKey: null,
                    selectedKeys: [],
                }))
                setLoadedKinds((prev) => Array.from(new Set([...prev, activeKind])))
            })
            .catch(() => {
                if (!cancelled) setLoadedKinds((prev) => Array.from(new Set([...prev, activeKind])))
            })
        return () => {
            cancelled = true
        }
    }, [activeKind, loadedKinds, updateKindSession])
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
        const notificationId = notify.task("Sync queued", `${paths.length} source folder(s)`)
        const job = await run("update-sources", () => jobsRepo.createSyncJob(paths, recursive))
        if (!job) return
        await pollOrganizerJob(job.id, notificationId)
        const result = await run("load-items", () => organizerRepo.items(kind))
        if (!result) return
        setLoadedKinds((prev) => Array.from(new Set([...prev, kind])))
        setSelectionAnchorKey(null)
        updateKindSession(kind, (session) => ({
            ...session,
            scanned: true,
            items: result,
            selectedKey: null,
            selectedKeys: [],
            renamePlan: null,
            renamePlanKey: null,
        }))
    }, [activeKind, activeSession.recursive, run, sourcePaths, updateKindSession])
    const runScrapeJob = useCallback(async (targetRows: MediaRow[], options: ScrapeApplyOptions) => {
        const kind = activeKind
        const source = scrapeSource
        const taskId = notify.task("Scrape queued", `${targetRows.length} album(s) queued`)
        const batches = options.sequentialRows ? targetRows.map((row) => [row]) : [targetRows]
        let done = 0
        let failed = 0
        try {
            for (const batch of batches) {
                const items = batch.flatMap((row) => row.files)
                notify.update(taskId, {
                    kind: "task",
                    status: "active",
                    title: "Scrape running",
                    message: `${done + failed + 1}/${batches.length}: ${batch[0]?.title ?? "Album"}`,
                    detail: "",
                    progress: Math.round((done + failed) / batches.length * 100),
                })
                const job = await jobsRepo.createScrapeJob(items, {
                    source,
                    overwrite: !options.missingOnly,
                    selectedCandidates: selectedCandidateMap(batch),
                })
                notify.update(taskId, { jobId: job.id })
                const finished = await pollOrganizerJob(job.id, taskId)
                if (finished.status === "error" || finished.status === "canceled") failed += 1
                else done += 1
                const refreshed = await organizerRepo.items(kind)
                updateKindSession(kind, (session) => ({
                    ...session,
                    items: refreshed,
                    selectedKey: session.selectedKey,
                    selectedKeys: [],
                    renamePlan: null,
                    renamePlanKey: null,
                }))
            }
            notify.update(taskId, {
                kind: failed > 0 ? "error" : "success",
                status: failed > 0 ? "error" : "done",
                title: failed > 0 ? "Scrape completed with failures" : "Scrape complete",
                message: `${done} album(s) done${failed ? `, ${failed} failed` : ""}`,
                detail: "",
                progress: 100,
            })
        } catch (error) {
            notify.update(taskId, {
                kind: "error",
                status: "error",
                title: "Scrape failed",
                message: errorMessage(error),
                progress: 100,
            })
        }
    }, [activeKind, scrapeSource, updateKindSession])
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
        const notificationId = notify.task("Rename queued", `${actionItems.length} file(s)`)
        const job = await run("rename", () => jobsRepo.createRenameJob(actionItems))
        if (!job) return
        const finished = await pollOrganizerJob(job.id, notificationId)
        if (finished.status === "error") return
        await refreshRenameLogs()
        const refreshed = await run("load-items", () => organizerRepo.items(kind))
        if (!refreshed) return
        updateKindSession(kind, (session) => ({
            ...session,
            items: refreshed,
            selectedKey: null,
            selectedKeys: [],
            renamePlan: null,
            renamePlanKey: null,
        }))
    }, [actionItems, actionPlanKey, activeKind, refreshRenameLogs, run, updateKindSession])
    const undoRename = useCallback(async (batchId: string) => {
        const result = await run("rename-undo", () => organizerRepo.renameUndo(batchId))
        if (!result) return
        notify.success("Undo complete", result.message)
        setRenameMenuOpen(false)
        await refreshRenameLogs()
        const refreshed = await run("update-sources", () => organizerRepo.scan(sourcePaths, activeSession.recursive))
        if (!refreshed) return
        const kind = activeKind
        updateKindSession(kind, (session) => ({
            ...session,
            items: refreshed.filter((item) => itemBelongsToKind(item, kind)),
            selectedKey: null,
            selectedKeys: [],
            renamePlan: null,
            renamePlanKey: null,
        }))
    }, [activeKind, activeSession.recursive, refreshRenameLogs, run, sourcePaths, updateKindSession])
    const toggleRenameMenu = useCallback(() => {
        setRenameMenuOpen((open) => {
            if (!open) void refreshRenameLogs()
            return !open
        })
    }, [refreshRenameLogs])
    const selectTableRow = useCallback((key: string, shiftKey: boolean) => {
        const nextKeys = shiftKey
            ? visibleRangeKeys(rows, selectionAnchorKey, key)
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
    }, [activeSession.selectedKeys, rows, selectionAnchorKey, updateActiveSession])
    const saveEdit = useCallback((row: MediaRow, values: MetadataEditValues) => {
        updateActiveSession((session) => ({
            ...session,
            items: session.items.map((item) => {
                if (!row.files.some((file) => file.path === item.path)) return item
                return {
                    ...item,
                    title: row.kind === "music" ? item.title : values.title,
                    album: row.kind === "music" ? values.title : item.album,
                    year: values.year,
                    metadata: true,
                    metadata_title: row.kind === "tv" ? item.metadata_title : values.title,
                    metadata_show_title: row.kind === "tv" ? values.title : item.metadata_show_title,
                    metadata_original_title: values.originalTitle || null,
                    metadata_year: values.year,
                    metadata_rating: values.rating,
                    metadata_rating_source: values.rating == null ? null : "User",
                    metadata_premiered: values.premiered || null,
                    metadata_certification: values.certification || null,
                    metadata_runtime: values.runtime,
                    metadata_genres: splitList(values.genres),
                    metadata_status: values.status || null,
                    metadata_studios: splitList(values.studios),
                    metadata_countries: splitList(values.countries),
                    metadata_tagline: values.tagline || null,
                    metadata_plot: values.plot || null,
                    metadata_tags: splitList(values.tags),
                    metadata_cast: splitList(values.cast),
                }
            }),
            renamePlan: null,
            renamePlanKey: null,
        }))
        setEditingKey(null)
    }, [updateActiveSession])
    const openMediaSettings = useCallback(() => {
        navigate("/settings?section=media")
    }, [navigate])
    const selectCandidateForRow = useCallback((row: MediaRow, candidate: OrganizerCandidate) => {
        updateActiveSession((session) => {
            const selectedCandidates = { ...session.selectedCandidates }
            for (const file of row.files) selectedCandidates[file.path] = candidate
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
        const taskId = notify.task("Scrape queued", `${items.length} file(s) queued`)
        try {
            const job = await jobsRepo.createScrapeJob(items, {
                source,
                overwrite: !options.missingOnly,
                selectedCandidates,
            })
            notify.update(taskId, { jobId: job.id })
            const finished = await pollOrganizerJob(job.id, taskId)
            notify.update(taskId, { message: scrapeResultMessage(finished), detail: "" })
            if (finished.status === "error" || finished.status === "canceled") return
            const refreshed = await organizerRepo.items(kind)
            updateKindSession(kind, (session) => ({
                ...session,
                items: refreshed,
                selectedKey: null,
                selectedKeys: [],
                renamePlan: null,
                renamePlanKey: null,
            }))
            if (scrapeSequential && scrapeDialogIndex < scrapeDialogKeys.length - 1) {
                setScrapeDialogIndex((index) => index + 1)
                setMatchDialogOpen(true)
            } else {
                setScrapeDialogKeys([])
                setScrapeDialogIndex(0)
                setScrapeSequential(false)
            }
        } catch (error) {
            notify.update(taskId, {
                kind: "error",
                status: "error",
                title: "Scrape failed",
                message: errorMessage(error),
                progress: 100,
            })
        }
    }, [
        activeKind,
        scrapeDialogIndex,
        scrapeDialogKeys.length,
        scrapeSource,
        scrapeSequential,
        updateKindSession,
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
            loading={loading}
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
            updateKindSession={updateKindSession}
            updateSources={updateSources}
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
