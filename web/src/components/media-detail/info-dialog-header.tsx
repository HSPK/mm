import { Check, Loader2, Pencil, X } from "lucide-react"

interface InfoDialogHeaderProps {
    isEditing: boolean
    saving: boolean
    canEdit: boolean
    onEnterEdit: () => void
    onCancelEdit: () => void
    onSave: () => void
    onClose: () => void
}

export function InfoDialogHeader({
    isEditing,
    saving,
    canEdit,
    onEnterEdit,
    onCancelEdit,
    onSave,
    onClose,
}: InfoDialogHeaderProps) {
    return (
        <div className="flex shrink-0 items-center justify-between px-5 pb-2 pt-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                {isEditing ? "Edit Metadata" : "Details"}
            </span>
            <div className="flex items-center gap-1">
                {isEditing ? (
                    <>
                        <button
                            onClick={onCancelEdit}
                            disabled={saving}
                            className="rounded-full p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                            title="Cancel"
                        >
                            <X className="h-4 w-4" />
                        </button>
                        <button
                            onClick={onSave}
                            disabled={saving}
                            className="rounded-full p-1.5 text-emerald-500 transition-colors hover:bg-emerald-500/10"
                            title="Save"
                        >
                            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                        </button>
                    </>
                ) : (
                    <>
                        <button
                            onClick={onEnterEdit}
                            disabled={!canEdit}
                            className="rounded-full p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
                            title="Edit"
                        >
                            <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                            onClick={onClose}
                            className="rounded-full p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                            title="Close"
                        >
                            <X className="h-4 w-4" />
                        </button>
                    </>
                )}
            </div>
        </div>
    )
}
