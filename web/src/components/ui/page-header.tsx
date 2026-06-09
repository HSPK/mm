import { ChevronLeft } from "lucide-react"
import type { ReactNode } from "react"
import { useNavigate } from "react-router-dom"
import { cn } from "@/lib/utils"

interface PageHeaderProps {
    title: string
    back?: boolean | (() => void)
    backLabel?: string
    actions?: ReactNode
    /** Render the title twice — once large under the bar (iOS large title)
     *  and again in the compact bar above. Defaults to false. */
    largeTitle?: boolean
}

/**
 * Apple-style navigation bar. Translucent vibrancy material with a hairline
 * separator. `largeTitle` adds an iOS-style oversized heading below the bar.
 */
export function PageHeader({ title, back, backLabel, actions, largeTitle }: PageHeaderProps) {
    const navigate = useNavigate()
    const handleBack = typeof back === "function" ? back : () => navigate(-1)

    return (
        <>
            <div className="sticky top-0 z-20 material-bar hairline-b">
                <div className="flex items-center gap-1 px-2 h-11 sm:h-12">
                    {back ? (
                        <button
                            type="button"
                            onClick={handleBack}
                            aria-label={backLabel ?? "Back"}
                            className="flex items-center gap-0.5 -ml-1 pl-1 pr-2 h-8 rounded-full text-[15px] font-normal text-primary hover:bg-secondary/40 active:bg-secondary/60 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                            <ChevronLeft className="h-[18px] w-[18px] stroke-[2.3]" />
                            {backLabel && <span>{backLabel}</span>}
                        </button>
                    ) : (
                        <div className="w-2" aria-hidden />
                    )}
                    <h1 className={cn(
                        "text-[17px] font-semibold flex-1 text-center truncate",
                        largeTitle && "opacity-0", // hidden until scroll on large-title pages
                    )}>
                        {title}
                    </h1>
                    <div className="flex items-center gap-1 min-w-[2rem] justify-end">{actions}</div>
                </div>
            </div>
            {largeTitle && (
                <div className="px-5 pt-3 pb-4">
                    <h1 className="text-[34px] font-bold tracking-tight leading-[1.1]">{title}</h1>
                </div>
            )}
        </>
    )
}
