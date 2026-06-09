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
                <Tag className="h-[13px] w-[13px] text-white/20 shrink-0 mr-0.5" />
                {detail.tags.map((t) => (
                    <span
                        key={t.name}
                        className="inline-flex items-center gap-1 pl-2.5 pr-1.5 py-[5px] bg-white/[0.07] text-white/65 rounded-full text-xs font-medium group"
                    >
                        <button
                            onClick={() => onClickTag(t.name)}
                            className="hover:text-white transition-colors cursor-pointer"
                            title={`Filter by tag: ${t.name}`}
                        >
                            {t.name}
                        </button>
                        <button
                            onClick={() => onRemoveTag(t.name)}
                            disabled={removingTag != null}
                            className="p-0.5 rounded-full hover:bg-white/15 text-white/25 hover:text-white/60 transition-colors disabled:pointer-events-none disabled:opacity-40"
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
                    <div className="flex items-center border border-dashed border-white/[0.08] rounded-full overflow-hidden hover:border-white/20 focus-within:border-white/25 transition-colors">
                        {submitting
                            ? <Loader2 className="h-3 w-3 text-white/25 ml-2 shrink-0 animate-spin" />
                            : <Plus className="h-3 w-3 text-white/15 ml-2 shrink-0" />}
                        <input
                            type="text"
                            value={addInput}
                            onChange={(e) => onAddInputChange(e.target.value)}
                            disabled={submitting}
                            placeholder={detail.tags.length === 0 ? "Add tag…" : "Add…"}
                            className="bg-transparent text-white text-xs pl-1 pr-2.5 py-[5px] w-16 focus:w-24 focus:outline-none transition-all placeholder:text-white/15 disabled:opacity-50"
                        />
                    </div>
                </form>
            </div>
        </div>
    )
}
