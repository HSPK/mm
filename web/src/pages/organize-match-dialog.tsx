import { useEffect, useState } from "react"
import { createPortal } from "react-dom"
import { FileSearch, Image, X } from "lucide-react"
import {
    organizerRepo,
    type OrganizerCandidate,
    type OrganizerConfig,
} from "@/api/organizer"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { cn } from "@/lib/utils"
import { LabeledScrapeInput, LabeledSelect } from "./organize-form-controls"
import {
    type MediaRow,
    type ScrapeApplyOptions,
    activeRowInfoLine,
    candidateInfoLine,
    candidateKey,
    firstMusicArtist,
    hasScraperCredentialStatus,
    languageDisplayName,
    parseYear,
    ratingText,
    scrapeFieldChips,
    scraperDisplayName,
    searchItemsForRow,
    uniqueCandidates,
} from "./organize-model"

export function MatchDialog({
    open,
    rows,
    scraperSource,
    scraperOptions,
    scraperStatuses,
    scraperLanguage,
    initialLoading,
    applying,
    onClose,
    onSelectCandidate,
    onApply,
}: {
    open: boolean
    rows: MediaRow[]
    scraperSource: string
    scraperOptions: string[]
    scraperStatuses: OrganizerConfig["sources"]
    scraperLanguage: string
    initialLoading: boolean
    applying: boolean
    onClose: () => void
    onSelectCandidate: (row: MediaRow, candidate: OrganizerCandidate) => void
    onApply: (rows: MediaRow[], options: ScrapeApplyOptions) => Promise<void>
}) {
    const [activeRowKey, setActiveRowKey] = useState<string>("")
    const [activeCandidateKey, setActiveCandidateKey] = useState<string>("")
    const [query, setQuery] = useState<string | null>(null)
    const [queryYear, setQueryYear] = useState<string | null>(null)
    const [queryArtist, setQueryArtist] = useState<string | null>(null)
    const [selectedScraper, setSelectedScraper] = useState(scraperSource)
    const [selectedLanguage, setSelectedLanguage] = useState(scraperLanguage)
    const [searching, setSearching] = useState(false)
    const [searchError, setSearchError] = useState("")
    const [missingOnly, setMissingOnly] = useState(true)
    const [dialogCandidates, setDialogCandidates] = useState<Record<string, OrganizerCandidate[]>>({})

    useEffect(() => {
        if (!open) return undefined
        const previous = document.body.style.overflow
        const handler = (event: KeyboardEvent) => {
            if (event.key === "Escape") onClose()
        }
        document.body.style.overflow = "hidden"
        window.addEventListener("keydown", handler)
        return () => {
            document.body.style.overflow = previous
            window.removeEventListener("keydown", handler)
        }
    }, [onClose, open])

    const activeRow = rows.find((row) => row.key === activeRowKey) ?? rows[0] ?? null
    const rowCandidates = activeRow ? (dialogCandidates[activeRow.key] ?? activeRow.candidates) : []
    const busy = initialLoading || searching
    const activeCandidate = activeRow
        ? rowCandidates.find((candidate) => candidateKey(candidate) === activeCandidateKey)
            ?? activeRow.candidate
            ?? rowCandidates[0]
        : null
    const searchTitle = query ?? activeRow?.title ?? ""
    const searchYear = queryYear ?? (activeRow?.year ? String(activeRow.year) : "")
    const searchArtist = queryArtist ?? firstMusicArtist(activeRow) ?? ""

    if (!open) return null

    const selectCandidate = (row: MediaRow, candidate: OrganizerCandidate) => {
        if (row.key !== activeRow?.key) {
            setQuery(null)
            setQueryYear(null)
            setQueryArtist(null)
            setSearchError("")
        }
        setActiveRowKey(row.key)
        setActiveCandidateKey(candidateKey(candidate))
        onSelectCandidate(row, candidate)
    }
    const runSearch = async () => {
        const searchText = searchTitle.trim()
        if (!activeRow || !searchText) return
        if (!hasScraperCredentialStatus(scraperStatuses, selectedScraper)) {
            setSearchError(`${scraperDisplayName(selectedScraper)} credentials are missing.`)
            return
        }
        setSearching(true)
        setSearchError("")
        try {
            const year = parseYear(searchYear)
            const items = searchItemsForRow(activeRow, searchText, year, searchArtist)
            const results = await organizerRepo.match(items, selectedScraper, 5, selectedLanguage)
            const candidates = uniqueCandidates(results.flatMap((result) => result.candidates))
            setDialogCandidates((prev) => ({ ...prev, [activeRow.key]: candidates }))
            if (candidates[0]) selectCandidate(activeRow, candidates[0])
            else setActiveCandidateKey("")
        } catch {
            setSearchError(`Search failed with ${scraperDisplayName(selectedScraper)}. Check credentials and network access.`)
        } finally {
            setSearching(false)
        }
    }

    return createPortal(
        <div
            className="fixed inset-0 z-[10020] flex items-center justify-center bg-black/40 p-4"
            onClick={onClose}
            onWheel={(event) => event.stopPropagation()}
            onTouchMove={(event) => event.stopPropagation()}
        >
            <section
                role="dialog"
                aria-modal="true"
                aria-label="Scrape matches"
                onClick={(event) => event.stopPropagation()}
                className="flex h-[82vh] w-full max-w-6xl flex-col overflow-hidden rounded-[1.25rem] bg-background shadow-2xl"
            >
                <MatchDialogHeader activeRow={activeRow} onClose={onClose} />
                <MatchSearchControls
                    activeRow={activeRow}
                    busy={busy}
                    scraperSource={scraperSource}
                    scraperOptions={scraperOptions}
                    selectedScraper={selectedScraper}
                    selectedLanguage={selectedLanguage}
                    searchTitle={searchTitle}
                    searchYear={searchYear}
                    searchArtist={searchArtist}
                    searchError={searchError}
                    scraperStatuses={scraperStatuses}
                    onScraperChange={setSelectedScraper}
                    onLanguageChange={setSelectedLanguage}
                    onTitleChange={setQuery}
                    onYearChange={setQueryYear}
                    onArtistChange={setQueryArtist}
                    onSearch={runSearch}
                />
                <MatchContent
                    activeRow={activeRow}
                    activeCandidate={activeCandidate}
                    candidates={rowCandidates}
                    initialLoading={initialLoading}
                    onSelectCandidate={selectCandidate}
                />
                <MatchFooter
                    activeRow={activeRow}
                    rows={rows}
                    language={selectedLanguage}
                    missingOnly={missingOnly}
                    applying={applying}
                    onMissingOnlyChange={setMissingOnly}
                    onClose={onClose}
                    onApply={onApply}
                />
            </section>
        </div>,
        document.body,
    )
}

function MatchDialogHeader({ activeRow, onClose }: { activeRow: MediaRow | null, onClose: () => void }) {
    return (
        <div className="flex items-center justify-between border-b border-border/70 px-5 py-3">
            <div className="min-w-0">
                <p className="truncate font-mono text-xs text-muted-foreground">
                    {activeRow?.files[0]?.path ?? "No media selected"}
                </p>
            </div>
            <button
                type="button"
                onClick={onClose}
                aria-label="Close matches"
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            >
                <X className="h-5 w-5" />
            </button>
        </div>
    )
}

function MatchSearchControls({
    activeRow,
    busy,
    scraperSource,
    scraperOptions,
    selectedScraper,
    selectedLanguage,
    searchTitle,
    searchYear,
    searchArtist,
    searchError,
    scraperStatuses,
    onScraperChange,
    onLanguageChange,
    onTitleChange,
    onYearChange,
    onArtistChange,
    onSearch,
}: {
    activeRow: MediaRow | null
    busy: boolean
    scraperSource: string
    scraperOptions: string[]
    selectedScraper: string
    selectedLanguage: string
    searchTitle: string
    searchYear: string
    searchArtist: string
    searchError: string
    scraperStatuses: OrganizerConfig["sources"]
    onScraperChange: (value: string) => void
    onLanguageChange: (value: string) => void
    onTitleChange: (value: string) => void
    onYearChange: (value: string) => void
    onArtistChange: (value: string) => void
    onSearch: () => Promise<void>
}) {
    return (
        <div className="border-b border-border/70 px-5 py-3">
            <div className={cn(
                "grid gap-2",
                activeRow?.kind === "music"
                    ? "md:grid-cols-[9rem_minmax(0,14rem)_minmax(0,1fr)_auto]"
                    : "md:grid-cols-[9rem_12rem_minmax(0,1fr)_7rem_auto]",
            )}>
                <LabeledSelect label="Scraper" value={selectedScraper} onChange={onScraperChange}>
                    {Array.from(new Set([scraperSource, ...scraperOptions])).map((source) => (
                        <option key={source} value={source}>{scraperDisplayName(source)}</option>
                    ))}
                </LabeledSelect>
                {activeRow?.kind !== "music" ? (
                    <LabeledSelect label="Language" value={selectedLanguage} onChange={onLanguageChange}>
                        {["zh-CN", "zh-TW", "en-US", "ja-JP", "ko-KR"].map((language) => (
                            <option key={language} value={language}>{languageDisplayName(language)}</option>
                        ))}
                    </LabeledSelect>
                ) : (
                    <LabeledScrapeInput label="Artist" value={searchArtist} onChange={onArtistChange} onEnter={onSearch} />
                )}
                <LabeledScrapeInput label={activeRow?.kind === "music" ? "Album" : "Title"} value={searchTitle} onChange={onTitleChange} onEnter={onSearch} />
                {activeRow?.kind !== "music" && (
                    <LabeledScrapeInput label="Year" value={searchYear} onChange={onYearChange} onEnter={onSearch} inputMode="numeric" />
                )}
                <Button size="sm" variant="tinted" disabled={busy} aria-busy={busy || undefined} onClick={() => void onSearch()} className="w-24 self-end">
                    <FileSearch className="h-4 w-4" />
                    Search
                </Button>
            </div>
            {busy && <div className="mt-2 h-0.5 overflow-hidden rounded-full bg-secondary"><div className="h-full w-1/3 animate-[shimmer_1s_infinite] bg-primary" /></div>}
            <div className="mt-2 flex items-center gap-2 text-xs">
                {!hasScraperCredentialStatus(scraperStatuses, selectedScraper) && (
                    <span className="rounded-full bg-destructive/10 px-2 py-0.5 font-semibold text-destructive">
                        Configure {scraperDisplayName(selectedScraper)} credentials in Settings
                    </span>
                )}
                {searchError && <span className="text-destructive">{searchError}</span>}
            </div>
        </div>
    )
}

function MatchContent({
    activeRow,
    activeCandidate,
    candidates,
    initialLoading,
    onSelectCandidate,
}: {
    activeRow: MediaRow | null
    activeCandidate: OrganizerCandidate | null
    candidates: OrganizerCandidate[]
    initialLoading: boolean
    onSelectCandidate: (row: MediaRow, candidate: OrganizerCandidate) => void
}) {
    return (
        <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_22rem]">
            {activeRow ? (
                <>
                    <CandidateTable
                        activeRow={activeRow}
                        activeCandidate={activeCandidate}
                        candidates={candidates}
                        initialLoading={initialLoading}
                        onSelectCandidate={onSelectCandidate}
                    />
                    <CandidatePreview activeRow={activeRow} candidate={activeCandidate} />
                </>
            ) : (
                <EmptyState icon={FileSearch} title="No media selected" description="Select media before scraping." className="col-span-full" />
            )}
        </div>
    )
}

function CandidateTable({
    activeRow,
    activeCandidate,
    candidates,
    initialLoading,
    onSelectCandidate,
}: {
    activeRow: MediaRow
    activeCandidate: OrganizerCandidate | null
    candidates: OrganizerCandidate[]
    initialLoading: boolean
    onSelectCandidate: (row: MediaRow, candidate: OrganizerCandidate) => void
}) {
    return (
        <div className="min-h-0 overflow-y-auto border-r border-border/70 p-4">
            {candidates.length === 0 ? (
                <EmptyState
                    icon={FileSearch}
                    title={initialLoading ? "Searching matches" : "No matches found"}
                    description={initialLoading ? "Fetching candidates from the selected scraper." : "Try another title, or check scraper credentials in Settings."}
                    className="min-h-[22rem]"
                />
            ) : (
                <table className="w-full text-left text-sm">
                    <thead className="border-b border-border text-xs text-muted-foreground">
                        <tr>
                            <th className="py-2 pr-3 font-semibold">Search result</th>
                            <th className="px-3 py-2 font-semibold">Year</th>
                            <th className="px-3 py-2 font-semibold">ID</th>
                            <th className="px-3 py-2 text-right font-semibold">Score</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                        {candidates.map((candidate) => {
                            const active = activeCandidate
                                && candidateKey(activeCandidate) === candidateKey(candidate)
                            return (
                                <tr
                                    key={`${activeRow.key}:${candidateKey(candidate)}`}
                                    onClick={() => onSelectCandidate(activeRow, candidate)}
                                    className={cn("cursor-pointer transition-colors", active ? "bg-primary/10 hover:bg-primary/10" : "hover:bg-secondary/35")}
                                >
                                    <td className="max-w-[24rem] py-2 pr-3">
                                        <div className="truncate font-semibold">{candidate.title}</div>
                                        <div className="truncate text-xs text-muted-foreground">
                                            {candidateInfoLine(candidate) || activeRow.title}
                                        </div>
                                    </td>
                                    <td className="whitespace-nowrap px-3 py-2">{candidate.year ?? "-"}</td>
                                    <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">{candidate.source_id}</td>
                                    <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{candidate.confidence.toFixed(2)}</td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            )}
        </div>
    )
}

function CandidatePreview({ activeRow, candidate }: { activeRow: MediaRow | null, candidate: OrganizerCandidate | null }) {
    return (
        <aside className="min-h-0 overflow-y-auto p-5">
            {candidate && (
                <div className="space-y-4">
                    <div className="mx-auto flex aspect-[2/3] w-36 items-center justify-center overflow-hidden bg-secondary/60">
                        {candidate.poster_url ? (
                            <img src={candidate.poster_url} alt="" className="h-full w-full object-cover" />
                        ) : (
                            <Image className="h-10 w-10 text-muted-foreground/50" />
                        )}
                    </div>
                    <div>
                        <h3 className="text-lg font-bold">{candidate.title}</h3>
                        <p className="mt-1 text-sm text-muted-foreground">
                            {[candidate.year, candidate.source, ratingText(candidate.rating)].filter((item) => item && item !== "-").join(" · ")}
                        </p>
                    </div>
                    <div className="grid gap-2 text-sm">
                        <CompactDetailField label="Current" value={activeRowInfoLine(activeRow)} />
                        <CompactDetailField label="Artist" value={candidate.artist} />
                        <CompactDetailField label="Album" value={candidate.album} />
                        <CompactDetailField label="Type" value={candidate.media_type} />
                        <CompactDetailField label="Runtime" value={candidate.runtime ? `${candidate.runtime} min` : ""} />
                        <CompactDetailField label="Release" value={candidate.release_date} />
                        <CompactDetailField label="Genres" value={candidate.genres.join(", ")} />
                        <CompactDetailField label="IDs" value={Object.entries(candidate.external_ids).map(([key, value]) => `${key}:${value}`).join(", ")} />
                    </div>
                    {candidate.overview && <p className="text-sm leading-6 text-muted-foreground">{candidate.overview}</p>}
                </div>
            )}
        </aside>
    )
}

function MatchFooter({
    activeRow,
    rows,
    language,
    missingOnly,
    applying,
    onMissingOnlyChange,
    onClose,
    onApply,
}: {
    activeRow: MediaRow | null
    rows: MediaRow[]
    language: string
    missingOnly: boolean
    applying: boolean
    onMissingOnlyChange: (missingOnly: boolean) => void
    onClose: () => void
    onApply: (rows: MediaRow[], options: ScrapeApplyOptions) => Promise<void>
}) {
    return (
        <div className="border-t border-border/70 px-5 py-3">
            <div className="mb-3">
                <p className="mb-2 text-xs font-semibold text-muted-foreground">Scrape following items</p>
                <div className="flex flex-wrap gap-1.5">
                    {scrapeFieldChips(activeRow?.kind ?? "movies").map((item) => (
                        <span key={item} className="rounded-md bg-secondary/60 px-2 py-1 text-xs text-muted-foreground">{item}</span>
                    ))}
                </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3">
                <label className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <input
                        type="checkbox"
                        checked={missingOnly}
                        onChange={(event) => onMissingOnlyChange(event.target.checked)}
                        className="h-4 w-4 accent-primary"
                    />
                    Only update missing data
                </label>
                <div className="flex justify-end gap-2">
                    <Button size="sm" variant="plain" onClick={onClose}>Cancel</Button>
                    <Button
                        size="sm"
                        loading={applying}
                        onClick={() => void onApply(rows, { missingOnly, language })}
                    >
                        OK
                    </Button>
                </div>
            </div>
        </div>
    )
}

function CompactDetailField({
    label,
    value,
}: {
    label: string
    value?: string | number | null
}) {
    if (!value) return null
    return (
        <div className="grid grid-cols-[4.25rem_minmax(0,1fr)] gap-2">
            <dt className="font-bold text-muted-foreground">{label}</dt>
            <dd className="min-w-0 break-words text-foreground/80">{value}</dd>
        </div>
    )
}
