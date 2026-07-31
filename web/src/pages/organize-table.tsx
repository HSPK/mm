import { useCallback, useEffect, useMemo, useRef, type MouseEvent, type MutableRefObject } from "react"
import { Captions, ChevronDown, ChevronRight, FileText, Image, Star } from "lucide-react"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { MediaRow, OrganizerKind } from "./organize-model"
import { IconHeader, IconStatus, NewBadge, RatingIndicator } from "./organize-badges"

export function MediaTable({
    rows,
    kind,
    selectedKey,
    selectedKeys,
    onOpenDetail,
    onSelect,
    onToggleExpand,
}: {
    rows: MediaRow[]
    kind: OrganizerKind
    selectedKey: string | null
    selectedKeys: string[]
    onOpenDetail: (key: string) => void
    onSelect: (key: string, shiftKey: boolean, visibleRows: MediaRow[]) => void
    onToggleExpand: (key: string) => void
}) {
    const selectedSet = useMemo(() => new Set(selectedKeys), [selectedKeys])
    const rowRefs = useRef(new Map<string, HTMLTableRowElement>())
    const handleRowClick = useCallback((event: MouseEvent<HTMLTableRowElement>, key: string) => {
        if (event.shiftKey) event.preventDefault()
        onSelect(key, event.shiftKey, rows)
    }, [onSelect, rows])

    useEffect(() => {
        if (!selectedKey) return
        if (kind === "music") return
        rowRefs.current.get(selectedKey)?.scrollIntoView({ block: "center", behavior: "smooth" })
    }, [kind, selectedKey])

    return (
        <Card className="flex h-full min-h-0 flex-col overflow-hidden rounded-[1.25rem]">
            <div className={cn(
                "min-h-0 flex-1 overflow-y-auto",
                kind === "music" ? "overflow-x-hidden" : "overflow-x-auto",
            )}>
                <table className={cn("w-full text-left text-sm", kind === "music" ? "table-fixed" : "min-w-[720px]")}>
                    <thead className="sticky top-0 z-10 border-b border-border/55 bg-card text-[11px] uppercase tracking-wider text-muted-foreground">
                        <tr>
                            <th className="min-w-0 px-5 py-2.5 font-semibold">Title</th>
                            <th className="w-16 px-2 py-2.5 font-semibold">Year</th>
                            {kind !== "music" && (
                                <th className="w-12 px-2 py-2.5 text-center font-semibold"><IconHeader icon={Star} label="Rating" /></th>
                            )}
                            <th className="w-10 px-2 py-2.5 text-center font-semibold"><IconHeader icon={FileText} label="Metadata" /></th>
                            <th className="w-10 px-2 py-2.5 text-center font-semibold"><IconHeader icon={Image} label="Images" /></th>
                            <th className="w-10 px-2 py-2.5 text-center font-semibold">
                                <IconHeader icon={Captions} label={kind === "music" ? "Lyrics" : "Subtitles"} />
                            </th>
                            {kind !== "music" && (
                                <th className="w-10 px-2 py-2.5 text-center font-semibold">
                                    <span className="sr-only">Details</span>
                                </th>
                            )}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border/55">
                        {rows.map((row) => (
                            <MediaTableRow
                                key={row.key}
                                row={row}
                                kind={kind}
                                active={row.key === selectedKey}
                                selected={selectedSet.has(row.key)}
                                onOpenDetail={onOpenDetail}
                                onSelect={handleRowClick}
                                onToggleExpand={onToggleExpand}
                                rowRefs={rowRefs}
                            />
                        ))}
                    </tbody>
                </table>
            </div>
        </Card>
    )
}

function MediaTableRow({
    row,
    kind,
    active,
    selected,
    onOpenDetail,
    onSelect,
    onToggleExpand,
    rowRefs,
}: {
    row: MediaRow
    kind: OrganizerKind
    active: boolean
    selected: boolean
    onOpenDetail: (key: string) => void
    onSelect: (event: MouseEvent<HTMLTableRowElement>, key: string) => void
    onToggleExpand: (key: string) => void
    rowRefs: MutableRefObject<Map<string, HTMLTableRowElement>>
}) {
    return (
        <tr
            ref={(node) => {
                if (node) rowRefs.current.set(row.key, node)
                else rowRefs.current.delete(row.key)
            }}
            onMouseDown={(event) => {
                if (event.shiftKey) event.preventDefault()
            }}
            onClick={(event) => onSelect(event, row.key)}
            className={cn(
                "cursor-pointer select-none transition-colors",
                selected
                    ? "bg-primary/10 hover:bg-primary/10"
                    : active
                        ? "bg-secondary/25 hover:bg-secondary/25"
                        : "hover:bg-secondary/35",
            )}
        >
            <td className="px-5 py-2.5">
                <div
                    className="flex min-w-0 items-center gap-2"
                    style={{ paddingLeft: `${row.depth * 1.25}rem` }}
                >
                    <ExpandCell row={row} onToggleExpand={onToggleExpand} />
                    <div className="min-w-0">
                        <div className="flex min-w-0 items-center gap-2">
                            <span className="truncate font-semibold">{row.title}</span>
                            {row.isNew && <NewBadge />}
                        </div>
                        {row.subtitle && (
                            <div className="mt-0.5 truncate text-xs text-muted-foreground">{row.subtitle}</div>
                        )}
                    </div>
                </div>
            </td>
            <td className="px-2 py-2.5 tabular-nums text-muted-foreground">{row.year ?? "-"}</td>
            {kind !== "music" && <td className="px-2 py-2.5 text-center"><RatingIndicator rating={row.rating} /></td>}
            <td className="px-2 py-2.5 text-center"><IconStatus icon={FileText} value={row.metadata} label="Metadata" /></td>
            <td className="px-2 py-2.5 text-center"><IconStatus icon={Image} value={row.images} label="Images" /></td>
            <td className="px-2 py-2.5 text-center">
                <IconStatus
                    icon={Captions}
                    value={kind === "music" ? row.lyrics : row.subtitles}
                    label={kind === "music" ? "Lyrics" : "Subtitles"}
                />
            </td>
            {kind !== "music" && (
                <td className="px-2 py-2.5 text-center" onClick={(event) => event.stopPropagation()}>
                    <button
                        type="button"
                        onClick={() => onOpenDetail(row.key)}
                        aria-label={`Show ${row.title} details`}
                        className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-secondary/60 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                    >
                        <ChevronRight className="h-3.5 w-3.5" />
                    </button>
                </td>
            )}
        </tr>
    )
}

function ExpandCell({ row, onToggleExpand }: { row: MediaRow, onToggleExpand: (key: string) => void }) {
    if (row.expandable) {
        return (
            <button
                type="button"
                onClick={(event) => {
                    event.stopPropagation()
                    onToggleExpand(row.key)
                }}
                aria-label={row.expanded ? `Collapse ${row.title}` : `Expand ${row.title}`}
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            >
                {row.expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
        )
    }
    return row.depth > 0 ? <span className="h-6 w-6 shrink-0" /> : null
}
