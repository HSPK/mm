import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react"
import { MapContainer, Marker, TileLayer, ZoomControl, useMap, useMapEvents } from "react-leaflet"
import L, { type LatLngExpression } from "leaflet"
import { MapPin } from "lucide-react"
import "leaflet/dist/leaflet.css"
import { statsRepo } from "@/api/stats"
import type { GeoPoint, Media } from "@/api/types"
import { EmptyState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { Spinner } from "@/components/ui/spinner"
import { MediaDetailPanel } from "@/components/media-detail"
import { displayLatLng } from "@/lib/geo-coordinate"
import { mediaUrl } from "@/lib/media-url"
import { themes, useThemeStore } from "@/stores/theme"

export default function MapPage() {
    const [points, setPoints] = useState<GeoPoint[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [openPreview, setOpenPreview] = useState<{ id: number; points: GeoPoint[] } | null>(null)
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

    const openItems: Media[] = useMemo(
        () => (openPreview?.points ?? []).map(geoPointToMedia),
        [openPreview],
    )

    const handleOpenPreview = useCallback(
        (id: number, groupPoints: GeoPoint[]) => {
            setOpenPreview({ id, points: groupPoints })
        },
        [],
    )

    return (
        <div className="flex h-full flex-col">
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
                {points.length > 0 && <MapBody points={points} onOpen={handleOpenPreview} />}
            </div>
            {openPreview != null && (() => {
                const idx = openItems.findIndex((m) => m.id === openPreview.id)
                if (idx < 0) return null
                return (
                    <MediaDetailPanel
                        items={openItems}
                        startIndex={idx}
                        onClose={() => setOpenPreview(null)}
                        onActiveChange={(id) => {
                            setOpenPreview((prev) => (prev ? { ...prev, id } : prev))
                        }}
                        onDelete={(id) => {
                            setPoints((prev) => prev.filter((p) => p.id !== id))
                            setOpenPreview((prev) => {
                                if (!prev) return prev
                                const nextPoints = prev.points.filter((p) => p.id !== id)
                                return nextPoints.length > 0
                                    ? { id: nextPoints[0].id, points: nextPoints }
                                    : null
                            })
                        }}
                    />
                )
            })()}
        </div>
    )
}

function geoPointToMedia(p: GeoPoint): Media {
    return {
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
    }
}

type Bounds = [[number, number], [number, number]]
const EMPTY_TILE_URL = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='256' height='256'%3E%3C/svg%3E"
type OpenMapPreview = (id: number, groupPoints: GeoPoint[]) => void

const MapBody = memo(function MapBody({ points, onOpen }: { points: GeoPoint[]; onOpen: OpenMapPreview }) {
    const themeId = useThemeStore((s) => s.themeId)
    const themeMode = themes.find((theme) => theme.id === themeId)?.mode ?? "dark"
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
            zoomSnap={0.25}
            zoomDelta={0.5}
            wheelDebounceTime={12}
            wheelPxPerZoomLevel={120}
            zoomControl={false}
            scrollWheelZoom
            fadeAnimation={false}
            markerZoomAnimation={false}
            className="h-full w-full"
            style={{ background: themeMode === "dark" ? "#0b0f14" : "#eef1f4" }}
        >
            <TileLayer
                key={themeMode}
                attribution='&copy; 高德地图'
                url="https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
                subdomains={["1", "2", "3", "4"]}
                errorTileUrl={EMPTY_TILE_URL}
                updateWhenIdle={false}
                updateWhenZooming={false}
                updateInterval={160}
                keepBuffer={3}
            />
            <ZoomControl position="bottomright" />
            <FitBounds bounds={bounds} />
            <MapThemeClass mode={themeMode} />
            <PlaceMarkers points={points} onOpen={onOpen} />
        </MapContainer>
    )
})

const MAX_VISIBLE_MARKERS = 140

function FitBounds({ bounds }: { bounds: Bounds | null }) {
    const map = useMap()
    useEffect(() => {
        if (bounds) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
    }, [bounds, map])
    return null
}

function MapThemeClass({ mode }: { mode: "light" | "dark" }) {
    const map = useMap()
    useEffect(() => {
        const container = map.getContainer()
        container.classList.toggle("mm-map-dark", mode === "dark")
        container.classList.toggle("mm-map-light", mode === "light")
        return () => {
            container.classList.remove("mm-map-dark", "mm-map-light")
        }
    }, [map, mode])
    return null
}

interface PlaceCluster {
    key: string
    label: string | null
    count: number
    center: LatLngExpression
    bounds: Bounds
    points: GeoPoint[]
    cover: GeoPoint
    hasVideo: boolean
}

function PlaceMarkers({ points, onOpen }: { points: GeoPoint[]; onOpen: OpenMapPreview }) {
    const map = useMap()
    const [zoom, setZoom] = useState(() => map.getZoom())

    useMapEvents({
        zoomend: () => setZoom(map.getZoom()),
    })

    const clusters = useMemo(
        () => clusterGeoPoints(points, zoom, map),
        [map, points, zoom],
    )

    const openCluster = useCallback((cluster: PlaceCluster) => {
        const targetZoom = targetZoomForCluster(cluster, zoom)
        if (
            cluster.count === 1 ||
            zoom >= 14 ||
            targetZoom <= zoom + 0.75 ||
            clusterSpan(cluster) < 0.0015
        ) {
            onOpen(cluster.cover.id, sortClusterPoints(cluster.points))
            return
        }

        map.flyTo(cluster.center, targetZoom, {
            animate: true,
            duration: 0.55,
            easeLinearity: 0.35,
        })
    }, [map, onOpen, zoom])

    return (
        <>
            {clusters.map((cluster) => (
                <Marker
                    key={`${cluster.key}:${cluster.cover.id}:${cluster.count}`}
                    position={cluster.center}
                    icon={createPlaceIcon(cluster, zoom)}
                    eventHandlers={{ click: () => openCluster(cluster) }}
                    zIndexOffset={cluster.count}
                />
            ))}
        </>
    )
}

function computeBounds(points: GeoPoint[]): Bounds | null {
    if (points.length === 0) return null
    let s = 90, n = -90, w = 180, e = -180
    for (const p of points) {
        const [lat, lon] = displayLatLng(p)
        if (lat < s) s = lat
        if (lat > n) n = lat
        if (lon < w) w = lon
        if (lon > e) e = lon
    }
    return [[s, w], [n, e]]
}

function clusterGeoPoints(
    points: GeoPoint[],
    zoom: number,
    map: L.Map,
): PlaceCluster[] {
    let cell = cellPxForZoom(zoom)
    let clusters: PlaceCluster[] = []

    for (let attempt = 0; attempt < 5; attempt += 1) {
        clusters = buildClusters(points, zoom, map, cell)
        if (clusters.length <= MAX_VISIBLE_MARKERS) break
        cell *= 1.35
    }

    return clusters
}

function buildClusters(points: GeoPoint[], zoom: number, map: L.Map, cell: number): PlaceCluster[] {
    const buckets = new Map<string, GeoPoint[]>()

    for (const point of points) {
        const projected = map.project(displayLatLng(point), zoom)
        const key = `px:${Math.floor(projected.x / cell)}:${Math.floor(projected.y / cell)}`
        const bucket = buckets.get(key)
        if (bucket) bucket.push(point)
        else buckets.set(key, [point])
    }

    return Array.from(buckets.entries())
        .map(([key, bucket]) => makeCluster(key, bucket))
        .sort((a, b) => b.count - a.count)
}

function cellPxForZoom(zoom: number): number {
    if (zoom < 5) return 96
    if (zoom < 8) return 88
    if (zoom < 11) return 80
    if (zoom < 14) return 72
    return 64
}

function targetZoomForCluster(cluster: PlaceCluster, currentZoom: number): number {
    const span = clusterSpan(cluster)
    if (span < 0.0005) return 16
    if (span < 0.002) return Math.max(currentZoom + 3, 16)
    if (span < 0.008) return Math.max(currentZoom + 3, 15.5)
    if (span < 0.03) return Math.max(currentZoom + 2.5, 14.5)
    if (cluster.count >= 80) return Math.max(currentZoom + 3, 13.5)
    if (cluster.count >= 20) return Math.max(currentZoom + 2.5, 12.5)
    return Math.max(currentZoom + 2, 11)
}

function clusterSpan(cluster: PlaceCluster): number {
    const [[s, w], [n, e]] = cluster.bounds
    return Math.max(Math.abs(n - s), Math.abs(e - w))
}

function sortClusterPoints(points: GeoPoint[]): GeoPoint[] {
    return [...points].sort((a, b) => {
        const aTime = a.date ? Date.parse(a.date) : 0
        const bTime = b.date ? Date.parse(b.date) : 0
        return bTime - aTime
    })
}

function makeCluster(key: string, points: GeoPoint[]): PlaceCluster {
    let lat = 0
    let lon = 0
    let s = 90, n = -90, w = 180, e = -180
    for (const point of points) {
        const [displayLat, displayLon] = displayLatLng(point)
        lat += displayLat
        lon += displayLon
        if (displayLat < s) s = displayLat
        if (displayLat > n) n = displayLat
        if (displayLon < w) w = displayLon
        if (displayLon > e) e = displayLon
    }

    const cover = points.find((point) => point.media_type !== "video") ?? points[0]
    const label = mostCommonCity(points) ?? cover.city ?? null

    return {
        key,
        label,
        count: points.length,
        center: [lat / points.length, lon / points.length],
        bounds: [[s, w], [n, e]],
        points,
        cover,
        hasVideo: points.some((point) => point.media_type === "video"),
    }
}

function mostCommonCity(points: GeoPoint[]): string | null {
    const counts = new Map<string, number>()
    for (const point of points) {
        const city = point.city?.trim()
        if (!city) continue
        counts.set(city, (counts.get(city) ?? 0) + 1)
    }
    let best: string | null = null
    let bestCount = 0
    for (const [city, count] of counts) {
        if (count > bestCount) {
            best = city
            bestCount = count
        }
    }
    return best
}

function createPlaceIcon(cluster: PlaceCluster, zoom: number): L.DivIcon {
    const size = markerSize(cluster.count, zoom)
    const showLabel = zoom >= 13.5 && cluster.count >= 4 && size >= 42 && cluster.label
    const showMeta = zoom >= 15 && cluster.count >= 8 && size >= 44
    const image = cluster.cover.media_type === "video"
        ? videoFallbackHtml(size)
        : photoMarkerHtml(cluster.cover)

    const labelHtml = showLabel
        ? `<div style="margin-top:5px;max-width:116px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border-radius:999px;background:color-mix(in srgb, var(--color-popover) 94%, transparent);padding:3px 8px;color:var(--color-foreground);font-size:10px;font-weight:650;box-shadow:0 6px 18px rgba(0,0,0,.13);">${escapeHtml(cluster.label ?? "")}${showMeta ? ` <span style="color:var(--color-muted-foreground);font-weight:600;">${cluster.count}</span>` : ""}</div>`
        : ""

    const countHtml = cluster.count > 1
        ? `<div style="position:absolute;right:-6px;top:-6px;min-width:20px;height:20px;border-radius:999px;background:var(--color-primary);color:var(--color-primary-foreground);display:flex;align-items:center;justify-content:center;padding:0 5px;font-size:10px;font-weight:800;box-shadow:0 4px 12px rgba(0,0,0,.22);">${cluster.count > 99 ? "99+" : cluster.count}</div>`
        : ""

    const stackHtml = cluster.count > 1
        ? `<div style="position:absolute;inset:0;transform:rotate(-6deg) translate(-3px,3px);border-radius:20%;background:var(--color-card);box-shadow:0 6px 16px rgba(0,0,0,.14);"></div><div style="position:absolute;inset:0;transform:rotate(5deg) translate(3px,2px);border-radius:20%;background:var(--color-card);box-shadow:0 6px 16px rgba(0,0,0,.12);"></div>`
        : ""

    const labelHeight = showLabel ? 30 : 0
    const iconWidth = Math.max(size + 32, showLabel ? 148 : size + 32)
    const iconHeight = size + labelHeight + 20
    const html = `
        <div style="width:${iconWidth}px;height:${iconHeight}px;display:flex;flex-direction:column;align-items:center;">
            <div style="position:relative;width:${size}px;height:${size}px;">
                ${stackHtml}
                <div style="position:relative;height:100%;width:100%;overflow:hidden;border-radius:22%;background:var(--color-muted);box-shadow:0 9px 22px rgba(0,0,0,.22), 0 0 0 2px var(--color-background), 0 0 0 3px color-mix(in srgb, var(--color-border) 80%, transparent);">
                    ${image}
                </div>
                ${countHtml}
            </div>
            ${labelHtml}
        </div>`

    return L.divIcon({
        className: "mm-map-place-marker",
        html,
        iconSize: [iconWidth, iconHeight],
        iconAnchor: [iconWidth / 2, size / 2],
    })
}

function photoMarkerHtml(point: GeoPoint): string {
    const thumb = escapeHtml(mediaUrl.thumbnail(point.id, "sm"))
    const preview = escapeHtml(mediaUrl.preview(point.id))
    return `
        ${photoFallbackHtml()}
        <img
            src="${thumb}"
            alt=""
            loading="lazy"
            decoding="async"
            onerror="if(!this.dataset.preview){this.dataset.preview='1';this.src='${preview}';}else{this.remove();}"
            style="position:absolute;inset:0;height:100%;width:100%;object-fit:cover;display:block;"
        />`
}

function photoFallbackHtml(): string {
    return `
        <div style="position:absolute;inset:0;height:100%;width:100%;background:linear-gradient(135deg, var(--color-muted), var(--color-secondary));"></div>`
}

function markerSize(count: number, zoom: number): number {
    const base = zoom < 5 ? 30 : zoom < 8 ? 34 : zoom < 12 ? 38 : zoom < 14 ? 42 : 46
    return Math.round(base + Math.min(12, Math.log2(Math.max(1, count)) * 3))
}

function videoFallbackHtml(size: number): string {
    const iconSize = Math.max(14, Math.round(size * 0.36))
    return `
        <div style="height:100%;width:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg, var(--color-muted), var(--color-secondary));color:var(--color-muted-foreground);">
            <svg xmlns="http://www.w3.org/2000/svg" width="${iconSize}" height="${iconSize}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.934a.5.5 0 0 0-.777-.416L16 11"/><rect x="2" y="6" width="14" height="12" rx="2"/></svg>
        </div>`
}

function escapeHtml(value: string): string {
    return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;")
}
