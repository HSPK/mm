import { useState, memo } from "react"
import { cn } from "@/lib/utils"

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api"
// Check if API is cross-origin (needs credentials attribute)
const IS_CROSS_ORIGIN = API_BASE.startsWith("http")

interface AuthImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
    /** API path, e.g. "/media/123/thumbnail" — uses cookie auth */
    apiSrc: string | null
}

/**
 * An <img> that loads via native browser image loading with cookie authentication.
 * More efficient than fetching blobs - browser handles request queuing.
 */
export const AuthImage = memo(function AuthImage({ apiSrc, className, alt, loading = "lazy", ...rest }: AuthImageProps) {
    const [loaded, setLoaded] = useState(false)
    const [error, setError] = useState(false)

    if (!apiSrc || error) {
        return <div className={cn("bg-muted", className)} />
    }

    const src = apiSrc.startsWith("/") ? `${API_BASE}${apiSrc}` : apiSrc

    return (
        <>
            {!loaded && <div className={cn("bg-muted absolute inset-0", className)} />}
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
