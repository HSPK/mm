import { Loader2, Plus, Tag, X } from "lucide-react"
import type { MediaDetail } from "@/api/types"

interface TagsSectionProps {
    detail: MediaDetail
    addInput: string
    onAddInputChange: (value: string) => void
    submitting: boolean
    removingTag: string | null
    onAddTag: () => void
    onRemoveTag: (name: string) => void
    onClickTag: (name: string) => void
}

export function TagsSection({
    detail,
    addInput,
    onAddInputChange,
    submitting,
    removingTag,
    onAddTag,
    onRemoveTag,
    onClickTag,
}: TagsSectionProps) {
    return (
        <div className="pb-4">
            <div className="flex flex-wrap items-center gap-1.5">
                <Tag className="h-[13px] w-[13px] text-muted-foreground shrink-0 mr-0.5" />
                {detail.tags.map((t) => (
                    <span
                        key={t.name}
                        className="group inline-flex items-center gap-1 rounded-full bg-secondary/55 py-[5px] pl-2.5 pr-1.5 text-xs font-medium text-foreground/75"
                    >
                        <button
                            onClick={() => onClickTag(t.name)}
                            className="cursor-pointer transition-colors hover:text-primary"
                            title={`Filter by tag: ${t.name}`}
                        >
                            {t.name}
                        </button>
                        <button
                            onClick={() => onRemoveTag(t.name)}
                            disabled={removingTag != null}
                            className="rounded-full p-0.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
                            title={`Remove tag: ${t.name}`}
                        >
                            {removingTag === t.name
                                ? <Loader2 className="h-2.5 w-2.5 animate-spin" />
                                : <X className="h-2.5 w-2.5" />}
                        </button>
                    </span>
                ))}
                <form
                    onSubmit={(e) => {
                        e.preventDefault()
                        onAddTag()
                    }}
                    className="inline-flex"
                >
                    <div className="flex items-center overflow-hidden rounded-full border border-dashed border-border transition-colors hover:border-border/80 focus-within:border-ring/40">
                        {submitting
                            ? <Loader2 className="h-3 w-3 text-muted-foreground ml-2 shrink-0 animate-spin" />
                            : <Plus className="h-3 w-3 text-muted-foreground/60 ml-2 shrink-0" />}
                        <input
                            type="text"
                            value={addInput}
                            onChange={(e) => onAddInputChange(e.target.value)}
                            disabled={submitting}
                            placeholder={detail.tags.length === 0 ? "Add tag…" : "Add…"}
                            className="w-16 bg-transparent py-[5px] pl-1 pr-2.5 text-xs text-foreground transition-all placeholder:text-muted-foreground/45 focus:w-24 focus:outline-none disabled:opacity-50"
                        />
                    </div>
                </form>
            </div>
        </div>
    )
}
