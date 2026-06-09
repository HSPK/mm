import {
    ChevronLeft,
    Download,
    ExternalLink,
    Info,
    Pencil,
    Share2,
    Trash2,
} from "lucide-react"
import { Spinner } from "@/components/ui/spinner"

interface MediaViewerChromeProps {
    showInfo: boolean
    isEditing: boolean
    controlsVisible: boolean
    downloading: boolean
    deleting: boolean
    inTrash: boolean
    onClose: () => void
    onOpenInfo: () => void
    onOpenEdit: () => void
    onDownload: () => void
    onShare: () => void
    onOpenOriginal: () => void
    onDelete: () => void
}

const actionBtnClass = (active = false) =>
    `flex items-center justify-center w-11 h-11 rounded-full transition-all duration-100 active:scale-90 ${active
        ? "text-white bg-white/20"
        : "text-white/70 hover:text-white hover:bg-white/10"
    }`

/**
 * Top action bar above the media viewer. Renders close (left), and
 * info / edit / share / open-original / download / delete (right).
 */
export function MediaViewerChrome({
    showInfo,
    isEditing,
    controlsVisible,
    downloading,
    deleting,
    inTrash,
    onClose,
    onOpenInfo,
    onOpenEdit,
    onDownload,
    onShare,
    onOpenOriginal,
    onDelete,
}: MediaViewerChromeProps) {
    const visibilityClass = controlsVisible ? "opacity-100" : "pointer-events-none opacity-0"

    return (
        <div
            className={`absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-3 pb-3 transition-opacity duration-200 ${visibilityClass}`}
            aria-hidden={!controlsVisible}
            inert={controlsVisible ? undefined : true}
            style={{
                paddingTop: "max(env(safe-area-inset-top, 0px), 12px)",
                background: "linear-gradient(to bottom, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.25) 60%, transparent 100%)",
            }}
        >
            <button
                type="button"
                onClick={onClose}
                className="flex items-center justify-center w-11 h-11 rounded-full text-white/80 hover:text-white hover:bg-white/10 active:scale-90 transition-all duration-100"
                aria-label="Back"
            >
                <ChevronLeft className="h-6 w-6" />
            </button>

            <div className="flex items-center gap-1">
                <ChromeButton onClick={onOpenInfo} active={showInfo && !isEditing} label="Info">
                    <Info className="h-[1.2rem] w-[1.2rem]" strokeWidth={showInfo && !isEditing ? 2.2 : 1.8} />
                </ChromeButton>
                <ChromeButton onClick={onOpenEdit} active={showInfo && isEditing} label="Edit">
                    <Pencil className="h-[1.2rem] w-[1.2rem]" strokeWidth={showInfo && isEditing ? 2.2 : 1.8} />
                </ChromeButton>
                <ChromeButton onClick={onShare} label="Share">
                    <Share2 className="h-[1.2rem] w-[1.2rem]" strokeWidth={1.8} />
                </ChromeButton>
                <ChromeButton onClick={onOpenOriginal} label="Open original in new tab">
                    <ExternalLink className="h-[1.2rem] w-[1.2rem]" strokeWidth={1.8} />
                </ChromeButton>
                <ChromeButton onClick={onDownload} label="Download" disabled={downloading}>
                    {downloading
                        ? <Spinner size="sm" />
                        : <Download className="h-[1.2rem] w-[1.2rem]" strokeWidth={1.8} />}
                </ChromeButton>
                <ChromeButton
                    onClick={onDelete}
                    label={inTrash ? "Delete permanently" : "Move to trash"}
                    disabled={deleting}
                >
                    {deleting
                        ? <Spinner size="sm" />
                        : <Trash2 className="h-[1.2rem] w-[1.2rem]" strokeWidth={1.8} />}
                </ChromeButton>
            </div>
        </div>
    )
}

interface ChromeButtonProps {
    onClick: () => void
    label: string
    active?: boolean
    disabled?: boolean
    children: React.ReactNode
}

function ChromeButton({ onClick, label, active, disabled, children }: ChromeButtonProps) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={actionBtnClass(active)}
            aria-label={label}
            disabled={disabled}
        >
            {children}
        </button>
    )
}
