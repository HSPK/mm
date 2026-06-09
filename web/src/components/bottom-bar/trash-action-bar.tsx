import { CheckCheck, RotateCcw, Trash2, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface TrashActionBarProps {
    total: number
    onBack: () => void
    onSelectAll: () => void
    onRestoreAll: () => void
    onEmpty: () => void
}

export function TrashActionBar({
    total,
    onBack,
    onSelectAll,
    onRestoreAll,
    onEmpty,
}: TrashActionBarProps) {
    return (
        <div className="relative flex items-center gap-1 px-2 py-1.5 material-thick elevation-3 border border-border/50 rounded-full">
            <BarButton onClick={onBack} icon={X} label="Back" inline />
            <span className="text-[10px] font-semibold text-foreground/80 px-2 tabular-nums">
                {total}
            </span>
            <BarButton onClick={onSelectAll} icon={CheckCheck} label="All" title="Select all" />
            <BarButton onClick={onRestoreAll} icon={RotateCcw} label="Restore" title="Restore all" />
            <BarButton onClick={onEmpty} icon={Trash2} label="Empty" title="Empty trash" destructive />
        </div>
    )
}

interface BarButtonProps {
    onClick: () => void
    icon: typeof X
    label: string
    title?: string
    destructive?: boolean
    inline?: boolean
}

function BarButton({ onClick, icon: Icon, label, title, destructive, inline }: BarButtonProps) {
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
                    : "text-muted-foreground/70 hover:text-foreground",
            )}
        >
            <Icon className="h-[1.15rem] w-[1.15rem]" />
            <span>{label}</span>
        </button>
    )
}
