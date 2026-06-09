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
        <div className="flex items-center justify-between px-5 pt-4 pb-2 shrink-0">
            <span className="text-white/35 text-[11px] uppercase tracking-wider font-semibold">
                {isEditing ? "Edit Metadata" : "Details"}
            </span>
            <div className="flex items-center gap-1">
                {isEditing ? (
                    <>
                        <button
                            onClick={onCancelEdit}
                            disabled={saving}
                            className="p-1.5 rounded-full text-white/30 hover:text-white/70 hover:bg-white/10 transition-colors"
                            title="Cancel"
                        >
                            <X className="h-4 w-4" />
                        </button>
                        <button
                            onClick={onSave}
                            disabled={saving}
                            className="p-1.5 rounded-full text-green-400/70 hover:text-green-400 hover:bg-white/10 transition-colors"
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
                            className="p-1.5 rounded-full text-white/30 hover:text-white/70 hover:bg-white/10 transition-colors disabled:pointer-events-none disabled:opacity-30"
                            title="Edit"
                        >
                            <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                            onClick={onClose}
                            className="p-1.5 rounded-full text-white/30 hover:text-white/70 hover:bg-white/10 transition-colors"
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
