import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react"
import { CircleMarker, MapContainer, TileLayer, useMap } from "react-leaflet"
import L, { type LatLngExpression } from "leaflet"
import { MapPin } from "lucide-react"
import "leaflet/dist/leaflet.css"
import { statsRepo } from "@/api/stats"
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

const MapBody = memo(function MapBody({ points, onOpen }: { points: GeoPoint[]; onOpen: (id: number) => void }) {
    const bounds = useMemo(() => computeBounds(points), [points])
    const renderer = useMemo(() => L.canvas({ padding: 0.5 }), [])
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
            preferCanvas
            className="h-full w-full"
            style={{ background: "#0b0d10" }}
        >
            <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FitBounds bounds={bounds} />
            {points.map((p) => (
                <CircleMarker
                    key={p.id}
                    center={[p.lat, p.lon]}
                    renderer={renderer}
                    radius={markerRadius(p)}
                    pathOptions={markerStyle(p)}
                    eventHandlers={{ click: () => onOpen(p.id) }}
                />
            ))}
        </MapContainer>
    )
})

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

const PHOTO_MARKER_STYLE: L.PathOptions = {
    color: "#38bdf8",
    fillColor: "#38bdf8",
    fillOpacity: 0.72,
    opacity: 0.9,
    weight: 1,
}

const VIDEO_MARKER_STYLE: L.PathOptions = {
    color: "#fb923c",
    fillColor: "#fb923c",
    fillOpacity: 0.78,
    opacity: 0.95,
    weight: 1,
}

function markerRadius(point: GeoPoint): number {
    return point.media_type === "video" ? 5 : 4
}

function markerStyle(point: GeoPoint): L.PathOptions {
    return point.media_type === "video" ? VIDEO_MARKER_STYLE : PHOTO_MARKER_STYLE
}
