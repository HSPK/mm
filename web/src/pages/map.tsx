import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet"
import L, { type LatLngExpression } from "leaflet"
import { MapPin } from "lucide-react"
import "leaflet/dist/leaflet.css"
import { statsRepo } from "@/api/stats"
import { mediaUrl } from "@/lib/media-url"
import type { GeoPoint, Media } from "@/api/types"
import { EmptyState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { Spinner } from "@/components/ui/spinner"
import { MediaDetailPanel } from "@/components/media-detail"

export default function MapPage() {
    const [points, setPoints] = useState<GeoPoint[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [openId, setOpenId] = useState<number | null>(null)
    const loadedRef = useRef(false)

    const load = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            // Single fast JOIN query — no client-side pagination
            setPoints(await statsRepo.geo(2000))
            loadedRef.current = true
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load")
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        if (loadedRef.current) return
        void load()
    }, [load])

    // Synthesise minimal Media[] for the viewer. MediaDetailPanel performs
    // its own detail fetch via `mediaRepo.get(id)`, so we only need id /
    // filename / media_type / gps for the lightbox to navigate siblings.
    const items: Media[] = useMemo(
        () => points.map((p) => ({
            id: p.id,
            filename: p.filename,
            extension: "",
            media_type: p.media_type,
            file_size: 0,
            rating: 0,
            width: null,
            height: null,
            date_taken: p.date ?? null,
            camera_model: null,
            duration: null,
            gps_lat: p.lat,
            gps_lon: p.lon,
            location_label: p.city ?? null,
            location_city: p.city ?? null,
            location_country: null,
            deleted_at: null,
        })),
        [points],
    )

    return (
        <div className="flex flex-col h-screen">
            <PageHeader title="Map" back />
            <div className="relative flex-1">
                {points.length === 0 && loading && (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <Spinner />
                    </div>
                )}
                {points.length === 0 && !loading && error && (
                    <EmptyState
                        icon={MapPin}
                        title="Couldn’t load map"
                        description={error}
                        action={{ label: "Retry", onClick: () => void load(), variant: "primary" }}
                    />
                )}
                {points.length === 0 && !loading && !error && (
                    <EmptyState
                        icon={MapPin}
                        title="No location data"
                        description="Items with GPS coordinates show up here."
                    />
                )}
                {points.length > 0 && <MapBody points={points} onOpen={setOpenId} />}
            </div>
            {openId != null && (() => {
                const idx = items.findIndex((m) => m.id === openId)
                if (idx < 0) return null
                return (
                    <MediaDetailPanel
                        items={items}
                        startIndex={idx}
                        onClose={() => setOpenId(null)}
                        onDelete={(id) => {
                            setPoints((prev) => prev.filter((p) => p.id !== id))
                            setOpenId(null)
                        }}
                    />
                )
            })()}
        </div>
    )
}

type Bounds = [[number, number], [number, number]]

function MapBody({ points, onOpen }: { points: GeoPoint[]; onOpen: (id: number) => void }) {
    const bounds = useMemo(() => computeBounds(points), [points])
    const center: LatLngExpression = useMemo(() => {
        if (!bounds) return [0, 0]
        const [[s, w], [n, e]] = bounds
        return [(s + n) / 2, (w + e) / 2]
    }, [bounds])

    return (
        <MapContainer
            center={center}
            zoom={3}
            scrollWheelZoom
            className="h-full w-full"
            style={{ background: "#0b0d10" }}
        >
            <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FitBounds bounds={bounds} />
            {points.map((p) => (
                <Marker
                    key={p.id}
                    position={[p.lat, p.lon]}
                    icon={thumbIcon(p)}
                    eventHandlers={{ click: () => onOpen(p.id) }}
                >
                    <Popup>
                        <div className="text-xs">
                            <p className="font-medium mb-1 truncate max-w-[200px]">{p.filename}</p>
                            {p.city && (
                                <p className="text-muted-foreground">{p.city}</p>
                            )}
                        </div>
                    </Popup>
                </Marker>
            ))}
        </MapContainer>
    )
}

function FitBounds({ bounds }: { bounds: Bounds | null }) {
    const map = useMap()
    useEffect(() => {
        if (bounds) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
    }, [bounds, map])
    return null
}

function computeBounds(points: GeoPoint[]): Bounds | null {
    if (points.length === 0) return null
    let s = 90, n = -90, w = 180, e = -180
    for (const p of points) {
        if (p.lat < s) s = p.lat
        if (p.lat > n) n = p.lat
        if (p.lon < w) w = p.lon
        if (p.lon > e) e = p.lon
    }
    return [[s, w], [n, e]]
}

/** Cached map of media id → marker icon to avoid recreating divIcons on every render. */
const iconCache = new Map<number, L.DivIcon>()

function thumbIcon(p: GeoPoint): L.DivIcon {
    const cached = iconCache.get(p.id)
    if (cached) return cached
    const html = `
        <div class="mm-pin">
            <img src="${mediaUrl.thumbnail(p.id, "sm")}" alt="" />
        </div>
    `
    const icon = L.divIcon({
        html,
        className: "mm-pin-wrap",
        iconSize: [44, 44],
        iconAnchor: [22, 44],
        popupAnchor: [0, -42],
    })
    iconCache.set(p.id, icon)
    return icon
}
