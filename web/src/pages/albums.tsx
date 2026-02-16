import { useEffect, useState, useMemo, useCallback, memo } from "react"
import { api } from "@/api/client"
import type { PaginatedMedia } from "@/api/types"
import { useMediaStore, type Filters } from "@/stores/media"
import { useNavigate } from "react-router-dom"
import { AuthImage } from "@/components/auth-image"
import {
    Images,
    Camera,
    MapPin,
    Calendar,
    HelpCircle,
    Trash2,
    Star,
    Film,
    Image,
    Loader2,
} from "lucide-react"
import { cn } from "@/lib/utils"

// ─── Types ────────────────────────────────────────────────

interface CameraAlbum {
    make: string
    model: string
    count: number
}

interface TimelineEntry {
    date: string
    count: number
}

interface GeoItem {
    id: number
    lat: number
    lon: number
    city: string | null
}

interface Stats {
    total_files: number
    total_size: number
    type_distribution: Record<string, number>
    cameras: CameraAlbum[]
    tags: { name: string; count: number }[]
}

// ─── Smart album card ─────────────────────────────────────

interface AlbumCardProps {
    icon: React.ElementType
    title: string
    subtitle?: string
    count?: number
    coverId?: number | null
    onClick: () => void
    color?: string
}

const AlbumCard = memo(function AlbumCard({
    icon: Icon,
    title,
    subtitle,
    count,
    coverId,
    onClick,
    color,
}: AlbumCardProps) {
    return (
        <button
            onClick={onClick}
            className="group relative overflow-hidden rounded-2xl bg-secondary/30 border border-border/60 hover:border-border transition-all duration-200 text-left w-full"
        >
            <div className="aspect-[4/3] relative overflow-hidden bg-muted">
                {coverId ? (
                    <AuthImage
                        apiSrc={`/media/${coverId}/thumbnail?size=lg`}
                        alt=""
                        loading="lazy"
                        className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                ) : (
                    <div
                        className={cn(
                            "h-full w-full flex items-center justify-center",
                            color || "bg-secondary/50",
                        )}
                    >
                        <Icon className="h-10 w-10 text-muted-foreground/20" />
                    </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
                {count != null && (
                    <span className="absolute top-2 right-2 inline-flex items-center rounded-full bg-black/50 backdrop-blur-sm px-2 py-0.5 text-[10px] text-white/80 font-medium border border-white/10">
                        {count.toLocaleString()}
                    </span>
                )}
                <div className="absolute bottom-0 left-0 right-0 p-3">
                    <h3 className="text-sm font-semibold text-white truncate">
                        {title}
                    </h3>
                    {subtitle && (
                        <p className="text-[10px] text-white/50 mt-0.5 truncate">
                            {subtitle}
                        </p>
                    )}
                </div>
            </div>
        </button>
    )
})

// ─── Section header ───────────────────────────────────────

function SectionHeader({
    icon: Icon,
    title,
    count,
}: {
    icon: React.ElementType
    title: string
    count?: number
}) {
    return (
        <div className="flex items-center gap-2.5 mb-3 px-1">
            <Icon className="h-4 w-4 text-muted-foreground/50" />
            <h2 className="text-sm font-semibold text-foreground/80 tracking-wide">
                {title}
            </h2>
            {count != null && (
                <span className="text-[10px] text-muted-foreground/40 font-medium">
                    {count}
                </span>
            )}
        </div>
    )
}

// ─── Year extraction from timeline ────────────────────────

function extractYears(
    timeline: TimelineEntry[],
): { year: string; count: number }[] {
    const yearMap = new Map<string, number>()
    for (const entry of timeline) {
        const year = entry.date.substring(0, 4)
        yearMap.set(year, (yearMap.get(year) ?? 0) + entry.count)
    }
    return Array.from(yearMap.entries())
        .map(([year, count]) => ({ year, count }))
        .sort((a, b) => b.year.localeCompare(a.year))
}

// ─── Location clustering (grid-based ~50 km) ─────────────

interface LocationCluster {
    name: string
    lat: number
    lon: number
    count: number
    sampleId: number
}

// Grid size in degrees (~55 km); the backend bounding-box radius must cover
// half this distance so that every item in the cell is included.
// 0.25° × 111.32 km/° ≈ 27.8 km → use 30 km for a safe margin.
const LOCATION_GRID = 0.5
const LOCATION_RADIUS_KM = 30

function clusterLocations(items: GeoItem[]): LocationCluster[] {
    const GRID = LOCATION_GRID
    const clusters = new Map<
        string,
        { centerLat: number; centerLon: number; count: number; sampleId: number; city: string | null }
    >()

    for (const entry of items) {
        const centerLat = Math.round(entry.lat / GRID) * GRID
        const centerLon = Math.round(entry.lon / GRID) * GRID
        const key = `${centerLat},${centerLon}`
        const c = clusters.get(key)
        if (c) {
            c.count++
            if (!c.city && entry.city) c.city = entry.city
        } else {
            clusters.set(key, {
                centerLat,
                centerLon,
                count: 1,
                sampleId: entry.id,
                city: entry.city,
            })
        }
    }

    return Array.from(clusters.values())
        .filter((c) => c.count >= 2)
        .sort((a, b) => b.count - a.count)
        .slice(0, 20)
        .map((c) => ({
            name: c.city || `${c.centerLat.toFixed(1)}°, ${c.centerLon.toFixed(1)}°`,
            lat: c.centerLat,
            lon: c.centerLon,
            count: c.count,
            sampleId: c.sampleId,
        }))
}

// ─── Fetch a representative cover for a filter ────────────

async function fetchCoverId(
    params: Record<string, unknown>,
): Promise<number | null> {
    try {
        const res = await api.get("/media", {
            params: { ...params, page: 1, per_page: 1 },
        })
        const items = res.data?.items
        return items?.length ? items[0].id : null
    } catch {
        return null
    }
}

// ─── Main Albums Page ─────────────────────────────────────

export default function AlbumsPage() {
    const navigate = useNavigate()
    const { setFilter, setFilters, total, setActiveLabel } = useMediaStore()

    const [loading, setLoading] = useState(true)
    const [stats, setStats] = useState<Stats | null>(null)
    const [timeline, setTimeline] = useState<TimelineEntry[]>([])
    const [geoData, setGeoData] = useState<GeoItem[]>([])
    // Cover IDs keyed by album identifier
    const [covers, setCovers] = useState<Record<string, number | null>>({})
    const [trashCount, setTrashCount] = useState(0)
    const [trashCoverId, setTrashCoverId] = useState<number | null>(null)

    useEffect(() => {
        let mounted = true

        Promise.all([
            api.get<Stats>("/stats"),
            api.get<TimelineEntry[]>("/timeline"),
            api.get<PaginatedMedia>("/media", { params: { has_location: true, per_page: 5000, sort: "date_taken", order: "desc" } }),
        ])
            .then(async ([statsRes, timelineRes, geoRes]) => {
                if (!mounted) return
                const s = statsRes.data
                const tl = timelineRes.data
                const geoItems: GeoItem[] = (geoRes.data.items || [])
                    .filter((m) => m.gps_lat != null && m.gps_lon != null)
                    .map((m) => ({
                        id: m.id,
                        lat: m.gps_lat!,
                        lon: m.gps_lon!,
                        city: m.location_city || null,
                    }))
                setStats(s)
                setTimeline(tl)
                setGeoData(geoItems)

                // Fetch representative covers in parallel
                const coverTasks: [string, Record<string, unknown>][] = [
                    ["all", { sort: "date_taken", order: "desc" }],
                    ["photo", { type: "photo", sort: "date_taken", order: "desc" }],
                    ["video", { type: "video", sort: "date_taken", order: "desc" }],
                    ["fav", { min_rating: 4, sort: "rating", order: "desc" }],
                ]
                // Camera covers
                for (const cam of (s.cameras ?? []).slice(0, 9)) {
                    const label = cam.model || cam.make
                    coverTasks.push([
                        `cam-${label}`,
                        { camera: label, sort: "date_taken", order: "desc" },
                    ])
                }
                // Year covers
                const years = extractYears(tl)
                for (const yr of years.slice(0, 12)) {
                    coverTasks.push([
                        `yr-${yr.year}`,
                        {
                            date_from: `${yr.year}-01-01`,
                            date_to: `${yr.year}-12-31`,
                            sort: "date_taken",
                            order: "desc",
                        },
                    ])
                }

                const results = await Promise.all(
                    coverTasks.map(([key, params]) =>
                        fetchCoverId(params).then((id) => [key, id] as const),
                    ),
                )
                if (!mounted) return
                const coverMap: Record<string, number | null> = {}
                for (const [key, id] of results) coverMap[key] = id
                setCovers(coverMap)
                setLoading(false)

                // Fetch trash count and cover
                api.get<PaginatedMedia>("/media", { params: { deleted: true, per_page: 1, sort: "date_taken", order: "desc" } })
                    .then(res => {
                        if (!mounted) return
                        setTrashCount(res.data.total)
                        if (res.data.items.length > 0) setTrashCoverId(res.data.items[0].id)
                    })
                    .catch(() => { })
            })
            .catch(() => {
                if (mounted) setLoading(false)
            })

        return () => {
            mounted = false
        }
    }, [])

    const years = useMemo(() => extractYears(timeline), [timeline])
    const locations = useMemo(() => clusterLocations(geoData), [geoData])

    const cameras = stats?.cameras ?? []
    const typeDist = stats?.type_distribution ?? {}

    const knownDateCount = timeline.reduce((sum, t) => sum + t.count, 0)
    const unknownDateCount = Math.max(0, (stats?.total_files ?? 0) - knownDateCount)

    const goLibraryWith = useCallback(
        (updates: Partial<Record<string, unknown>>, label?: string) => {
            // Apply updates on top of defaults to clear any previous filters
            setFilters({
                type: null,
                tag: null,
                camera: null,
                date_from: null,
                date_to: null,
                sort: "date_taken",
                order: "desc",
                search: null,
                min_rating: null,
                favorites_only: false,
                lat: null,
                lon: null,
                radius: null,
                no_date: false,
                deleted: false,
                ...updates,
            } as Partial<Filters>)
            // Determine which filter keys are album-locked (non-null values from updates)
            const lockedKeys = Object.entries(updates)
                .filter(([, v]) => v != null && v !== false && v !== "")
                .map(([k]) => k)
            setActiveLabel(label ?? null, lockedKeys)
            navigate("/")
        },
        [navigate, setFilters, setActiveLabel],
    )

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full pb-24">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground/40" />
            </div>
        )
    }

    return (
        <div className="pb-24">
            <div className="px-4 space-y-8">
                {/* ── Library ── */}
                <section>
                    <SectionHeader icon={Images} title="Library" />
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                        <AlbumCard
                            icon={Images}
                            title="All Media"
                            subtitle={`${(stats?.total_files ?? total).toLocaleString()} items`}
                            count={stats?.total_files ?? total}
                            coverId={covers["all"]}
                            onClick={() =>
                                goLibraryWith({
                                    type: null,
                                    camera: null,
                                    date_from: null,
                                    date_to: null,
                                    min_rating: null,
                                    sort: "date_taken",
                                    order: "desc",
                                    search: null,
                                    lat: null,
                                    lon: null,
                                    radius: null,
                                }, "All Media")
                            }
                        />
                        {(typeDist.photo ?? 0) > 0 && (
                            <AlbumCard
                                icon={Image}
                                title="Photos"
                                count={typeDist.photo}
                                coverId={covers["photo"]}
                                onClick={() => goLibraryWith({ type: "photo" }, "Photos")}
                            />
                        )}
                        {(typeDist.video ?? 0) > 0 && (
                            <AlbumCard
                                icon={Film}
                                title="Videos"
                                count={typeDist.video}
                                coverId={covers["video"]}
                                onClick={() => goLibraryWith({ type: "video" }, "Videos")}
                            />
                        )}
                        <AlbumCard
                            icon={Star}
                            title="Favorites"
                            subtitle="★4 and above"
                            coverId={covers["fav"]}
                            onClick={() =>
                                goLibraryWith({
                                    min_rating: 4,
                                    sort: "rating",
                                    order: "desc",
                                }, "Favorites")
                            }
                            color="bg-amber-500/5"
                        />
                        {trashCount > 0 && (
                            <AlbumCard
                                icon={Trash2}
                                title="Recently Deleted"
                                count={trashCount}
                                coverId={trashCoverId}
                                onClick={() =>
                                    goLibraryWith({
                                        deleted: true,
                                        sort: "date_taken",
                                        order: "desc",
                                    }, "Recently Deleted")
                                }
                                color="bg-destructive/5"
                            />
                        )}
                    </div>
                </section>

                {/* ── By Camera ── */}
                {cameras.length > 0 && (
                    <section>
                        <SectionHeader
                            icon={Camera}
                            title="Cameras"
                            count={cameras.length}
                        />
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                            {cameras.slice(0, 9).map((cam) => {
                                const label = cam.model || cam.make || "Unknown"
                                return (
                                    <AlbumCard
                                        key={`${cam.make}-${cam.model}`}
                                        icon={Camera}
                                        title={label}
                                        subtitle={
                                            cam.make && cam.model ? cam.make : undefined
                                        }
                                        count={cam.count}
                                        coverId={covers[`cam-${label}`]}
                                        onClick={() => {
                                            setFilter("camera", label)
                                            setActiveLabel(label, ["camera"])
                                            navigate("/")
                                        }}
                                    />
                                )
                            })}
                        </div>
                    </section>
                )}

                {/* ── By Year ── */}
                {years.length > 0 && (
                    <section>
                        <SectionHeader
                            icon={Calendar}
                            title="Years"
                            count={years.length}
                        />
                        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2.5">
                            {years.map((yr) => (
                                <button
                                    key={yr.year}
                                    onClick={() =>
                                        goLibraryWith({
                                            date_from: `${yr.year}-01-01`,
                                            date_to: `${yr.year}-12-31`,
                                            sort: "date_taken",
                                            order: "desc",
                                        }, yr.year)
                                    }
                                    className="group relative rounded-2xl overflow-hidden bg-secondary/30 border border-border/60 hover:border-border transition-all duration-200 text-left"
                                >
                                    {covers[`yr-${yr.year}`] ? (
                                        <div className="aspect-[4/3] relative">
                                            <AuthImage
                                                apiSrc={`/media/${covers[`yr-${yr.year}`]}/thumbnail?size=md`}
                                                alt=""
                                                loading="lazy"
                                                className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                                            />
                                            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
                                            <div className="absolute bottom-0 left-0 right-0 p-2.5">
                                                <p className="text-base font-bold text-white tracking-tight">
                                                    {yr.year}
                                                </p>
                                                <p className="text-[10px] text-white/50">
                                                    {yr.count.toLocaleString()} items
                                                </p>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="p-3">
                                            <p className="text-lg font-bold text-foreground tracking-tight">
                                                {yr.year}
                                            </p>
                                            <p className="text-[10px] text-muted-foreground/50 mt-0.5">
                                                {yr.count.toLocaleString()} items
                                            </p>
                                        </div>
                                    )}
                                </button>
                            ))}
                            {unknownDateCount > 0 && (
                                <button
                                    onClick={() =>
                                        goLibraryWith({
                                            sort: "filename",
                                            order: "asc",
                                            date_from: null,
                                            date_to: null,
                                            no_date: true,
                                        }, "No Date")
                                    }
                                    className="group relative rounded-2xl bg-secondary/30 border border-border/60 hover:border-border p-3 text-left transition-all duration-200"
                                >
                                    <div className="flex items-center gap-1.5">
                                        <HelpCircle className="h-3.5 w-3.5 text-muted-foreground/30" />
                                        <p className="text-sm font-semibold text-muted-foreground/60">
                                            No Date
                                        </p>
                                    </div>
                                    <p className="text-[10px] text-muted-foreground/40 mt-1">
                                        {unknownDateCount.toLocaleString()} items
                                    </p>
                                </button>
                            )}
                        </div>
                    </section>
                )}

                {/* ── By Location ── */}
                {locations.length > 0 && (
                    <section>
                        <SectionHeader
                            icon={MapPin}
                            title="Places"
                            count={locations.length}
                        />
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                            {locations.slice(0, 6).map((loc) => (
                                <AlbumCard
                                    key={`${loc.lat}-${loc.lon}`}
                                    icon={MapPin}
                                    title={loc.name}
                                    count={loc.count}
                                    coverId={loc.sampleId}
                                    onClick={() => {
                                        setFilters({
                                            lat: loc.lat,
                                            lon: loc.lon,
                                            radius: LOCATION_RADIUS_KM,
                                        })
                                        setActiveLabel(loc.name, ["lat", "lon", "radius"])
                                        navigate("/")
                                    }}
                                    color="bg-emerald-500/5"
                                />
                            ))}
                        </div>
                    </section>
                )}

            </div>
        </div>
    )
}
