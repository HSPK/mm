import { CheckCheck, FolderPlus, RotateCcw, Trash2, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface SelectionActionBarProps {
    selectedCount: number
    inTrash: boolean
    albumPickerOpen: boolean
    onCancel: () => void
    onSelectAll: () => void
    onToggleAlbumPicker: () => void
    onDelete: () => void
    onRestore: () => void
}

export function SelectionActionBar({
    selectedCount,
    inTrash,
    albumPickerOpen,
    onCancel,
    onSelectAll,
    onToggleAlbumPicker,
    onDelete,
    onRestore,
}: SelectionActionBarProps) {
    return (
        <div className="relative flex items-center gap-1 px-2 py-1.5 material-thick elevation-3 border border-border/50 rounded-full">
            <BarButton onClick={onCancel} icon={X} label="Cancel" inline />
            <span className="text-[10px] font-semibold text-foreground/80 px-2 tabular-nums">
                {selectedCount}
            </span>
            <BarButton onClick={onSelectAll} icon={CheckCheck} label="All" title="Select all" />

            {inTrash ? (
                <>
                    <BarButton onClick={onRestore} icon={RotateCcw} label="Restore" title="Restore" />
                    <BarButton onClick={onDelete} icon={Trash2} label="Delete" title="Delete permanently" destructive />
                </>
            ) : (
                <>
                    <BarButton
                        onClick={onToggleAlbumPicker}
                        icon={FolderPlus}
                        label="Album"
                        title="Add to album"
                        active={albumPickerOpen}
                    />
                    <BarButton onClick={onDelete} icon={Trash2} label="Delete" title="Delete" destructive />
                </>
            )}
        </div>
    )
}

interface BarButtonProps {
    onClick: () => void
    icon: typeof X
    label: string
    title?: string
    destructive?: boolean
    active?: boolean
    inline?: boolean
}

function BarButton({ onClick, icon: Icon, label, title, destructive, active, inline }: BarButtonProps) {
    return (
        <button
            type="button"
            onClick={onClick}
            title={title}
            className={cn(
                "relative z-10 flex px-3 py-1.5 rounded-full text-[10px] font-medium transition-colors",
                inline ? "items-center gap-1" : "flex-col items-center gap-0.5",
                destructive
                    ? "text-destructive/70 hover:text-destructive"
                    : active
                        ? "text-primary"
                        : "text-muted-foreground/70 hover:text-foreground",
            )}
        >
            <Icon className="h-[1.15rem] w-[1.15rem]" />
            <span>{label}</span>
        </button>
    )
}
