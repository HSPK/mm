import { memo, useState } from "react"
import { cn } from "@/lib/utils"
import { config } from "@/lib/config"

const IS_CROSS_ORIGIN = config.apiBaseUrl.startsWith("http")

interface AuthImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
    apiSrc: string | null
    /**
     * Optional fallback element shown when the source fails to load. Defaults
     * to a neutral muted block — pass `null` to render nothing.
     */
    fallback?: React.ReactNode
}

/**
 * Cookie-authenticated <img>. Shows an animated shimmer placeholder while
 * loading and a customizable fallback on error.
 */
export const AuthImage = memo(function AuthImage({
    apiSrc,
    className,
    alt,
    loading = "lazy",
    fallback,
    ...rest
}: AuthImageProps) {
    const [loaded, setLoaded] = useState(false)
    const [error, setError] = useState(false)

    if (!apiSrc || error) {
        if (fallback !== undefined) {
            return <>{fallback}</>
        }
        return <div className={cn("bg-muted", className)} aria-hidden />
    }

    const src = apiSrc.startsWith("/") ? `${config.apiBaseUrl}${apiSrc}` : apiSrc

    return (
        <>
            {!loaded && (
                <div
                    aria-hidden
                    className={cn(
                        "absolute inset-0 bg-muted/60 overflow-hidden",
                        "before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_1.5s_infinite]",
                        "before:bg-gradient-to-r before:from-transparent before:via-white/[0.06] before:to-transparent",
                        "motion-reduce:before:animate-none",
                        className,
                    )}
                />
            )}
            <img
                src={src}
                alt={alt ?? ""}
                loading={loading}
                decoding="async"
                crossOrigin={IS_CROSS_ORIGIN ? "use-credentials" : undefined}
                className={cn(className, !loaded && "opacity-0")}
                onLoad={() => setLoaded(true)}
                onError={() => setError(true)}
                {...rest}
            />
        </>
    )
})
