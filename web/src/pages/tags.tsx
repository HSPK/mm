import { useCallback, useEffect, useMemo, useState } from "react"
import { Check, Pencil, RefreshCw, Search, Tag as TagIcon, Trash2, X } from "lucide-react"
import { tagsRepo } from "@/api/tags"
import type { Tag } from "@/api/types"
import { Card, CardContent } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { PageHeader } from "@/components/ui/page-header"
import { Spinner } from "@/components/ui/spinner"
import { toast } from "@/stores/toast"
import { cn } from "@/lib/utils"

export default function TagsPage() {
    const [tags, setTags] = useState<Tag[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [query, setQuery] = useState("")

    const load = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            setTags(await tagsRepo.list())
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load tags")
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { void load() }, [load])

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase()
        if (!q) return tags
        return tags.filter((t) => t.name.toLowerCase().includes(q))
    }, [tags, query])

    const handleRename = useCallback(async (tag: Tag, newName: string) => {
        const trimmed = newName.trim()
        if (!trimmed || trimmed === tag.name) return
        try {
            await tagsRepo.rename(tag.id, trimmed)
            setTags((prev) => prev.map((t) => (t.id === tag.id ? { ...t, name: trimmed } : t)))
            toast.success(`Renamed "${tag.name}" → "${trimmed}"`)
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "Rename failed")
        }
    }, [])

    const handleDelete = useCallback(async (tag: Tag) => {
        if (!confirm(`Delete tag "${tag.name}"? This removes it from ${tag.count} item(s).`)) return
        try {
            await tagsRepo.remove(tag.id)
            setTags((prev) => prev.filter((t) => t.id !== tag.id))
            toast.success(`Deleted "${tag.name}"`)
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "Delete failed")
        }
    }, [])

    return (
        <div>
            <PageHeader
                title="Tags"
                back
                actions={
                    <button
                        type="button"
                        onClick={() => void load()}
                        aria-label="Refresh"
                        disabled={loading}
                        className="flex items-center justify-center h-9 w-9 rounded-full hover:bg-secondary transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                    </button>
                }
            />
            <div className="p-6 max-w-3xl mx-auto space-y-4">
                <Input
                    type="search"
                    placeholder="Search tags"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    leftIcon={<Search className="h-4 w-4" />}
                />

                {loading && tags.length === 0 && (
                    <div className="py-12 flex justify-center"><Spinner /></div>
                )}

                {!loading && error && tags.length === 0 && (
                    <EmptyState
                        icon={TagIcon}
                        title="Couldn’t load tags"
                        description={error}
                        action={{ label: "Retry", onClick: () => void load(), variant: "primary" }}
                    />
                )}

                {!loading && tags.length === 0 && !error && (
                    <EmptyState
                        icon={TagIcon}
                        title="No tags yet"
                        description="Tags appear here once you add them to media."
                    />
                )}

                {filtered.length > 0 && (
                    <Card>
                        <CardContent className="p-2">
                            <ul className="divide-y divide-border/40">
                                {filtered.map((tag) => (
                                    <TagRow
                                        key={tag.id}
                                        tag={tag}
                                        onRename={(newName) => handleRename(tag, newName)}
                                        onDelete={() => void handleDelete(tag)}
                                    />
                                ))}
                            </ul>
                        </CardContent>
                    </Card>
                )}

                {filtered.length === 0 && tags.length > 0 && (
                    <p className="text-center text-sm text-muted-foreground/60 py-8">
                        No tags match “{query}”.
                    </p>
                )}
            </div>
        </div>
    )
}

function TagRow({ tag, onRename, onDelete }: {
    tag: Tag
    onRename: (name: string) => void
    onDelete: () => void
}) {
    const [editing, setEditing] = useState(false)
    const [draft, setDraft] = useState(tag.name)

    const commit = () => {
        const trimmed = draft.trim()
        if (trimmed && trimmed !== tag.name) onRename(trimmed)
        setEditing(false)
    }

    return (
        <li className="flex items-center gap-2 py-2 px-3 hover:bg-secondary/30 transition-colors rounded-lg">
            {editing ? (
                <>
                    <input
                        autoFocus
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter") commit()
                            else if (e.key === "Escape") { setDraft(tag.name); setEditing(false) }
                        }}
                        className="flex-1 h-8 px-2 rounded-md bg-background border border-border text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                    <button onClick={commit} className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-secondary text-emerald-500" aria-label="Save">
                        <Check className="h-4 w-4" />
                    </button>
                    <button onClick={() => { setDraft(tag.name); setEditing(false) }} className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-secondary text-muted-foreground" aria-label="Cancel">
                        <X className="h-4 w-4" />
                    </button>
                </>
            ) : (
                <>
                    <span className="flex-1 text-sm">{tag.name}</span>
                    <span className="text-xs text-muted-foreground/70 tabular-nums px-2">{tag.count.toLocaleString()}</span>
                    <button onClick={() => { setDraft(tag.name); setEditing(true) }} className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-secondary text-muted-foreground" aria-label="Rename">
                        <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button onClick={onDelete} className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-destructive/15 text-destructive" aria-label="Delete">
                        <Trash2 className="h-3.5 w-3.5" />
                    </button>
                </>
            )}
        </li>
    )
}
