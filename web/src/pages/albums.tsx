import { FolderHeart } from "lucide-react"

export default function AlbumsPage() {
    return (
        <div className="flex flex-col items-center justify-center h-full text-muted-foreground/50 gap-3 pb-24">
            <FolderHeart className="h-12 w-12" />
            <p className="text-sm font-medium">Albums coming soon</p>
        </div>
    )
}
