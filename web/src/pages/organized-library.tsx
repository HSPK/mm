import axios from "axios"
import { useCallback, useEffect, useMemo, useState } from "react"
import { CalendarDays, Clapperboard, Film, Music, Sparkles, Tv } from "lucide-react"
import {
    organizerRepo,
    type OrganizerLibrary,
    type OrganizerLibraryEntry,
} from "@/api/organizer"
import { MusicLibraryPage } from "@/components/music/music-library-page"
import { AuthImage } from "@/components/auth-image"
import { EmptyState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"

type LibraryKind = "movies" | "tv" | "music"

const labels: Record<LibraryKind, string> = {
    movies: "Movies",
    tv: "TV Series",
    music: "Music",
}

const icons = {
    movies: Film,
    tv: Tv,
    music: Music,
}

const emptyDescriptions: Record<LibraryKind, string> = {
    movies: "Organized movies will appear here once filenames can be identified.",
    tv: "Organized shows and seasons will appear here once episodes are identified.",
    music: "Organized albums will appear here once tracks are identified.",
}

const heroCopy: Record<LibraryKind, string> = {
    movies: "A poster-first view for matched movies and local film files.",
    tv: "Shows grouped from identified seasons and episodes.",
    music: "Albums grouped from audio tracks and music metadata.",
}

export function OrganizedLibraryPage({ kind }: { kind: LibraryKind }) {
    const [data, setData] = useState<OrganizerLibrary | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const Icon = icons[kind]
    const title = labels[kind]

    const load = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            setData(await organizerRepo.library())
        } catch (err) {
            setError(organizerErrorMessage(err, title))
        } finally {
            setLoading(false)
        }
    }, [title])

    useEffect(() => {
        const id = window.setTimeout(() => { void load() }, 0)
        return () => window.clearTimeout(id)
    }, [load])

    const entries = useMemo(() => (data ? data[kind] : []), [data, kind])
    const featured = entries[0] ?? null
    const secondary = entries.slice(1, 7)
    const rest = entries.slice(featured ? 7 : 0)
    const totalItems = entries.reduce((sum, entry) => sum + entry.count, 0)
    const topSubtitle = featured?.subtitle || emptyDescriptions[kind]

    return (
        <div className="min-h-screen pb-24">
            <PageHeader title={title} back />
            <div className="space-y-6 px-4 pt-5 sm:px-6 sm:pt-7">
                {loading && !data && <div className="flex justify-center py-16"><Spinner /></div>}
                {!loading && error && !data && (
                    <EmptyState
                        icon={Icon}
                        title={`Couldn’t load ${title.toLowerCase()}`}
                        description={error}
                        action={{ label: "Retry", onClick: () => void load(), variant: "primary" }}
                    />
                )}
                {!loading && !error && entries.length === 0 && (
                    <EmptyState
                        icon={Icon}
                        title={`No ${title.toLowerCase()} yet`}
                        description={emptyDescriptions[kind]}
                    />
                )}
                {entries.length > 0 && (
                    <>
                        <LibraryHero
                            kind={kind}
                            title={title}
                            subtitle={topSubtitle}
                            totalGroups={entries.length}
                            totalItems={totalItems}
                            featured={featured}
                            icon={Icon}
                        />
                        {secondary.length > 0 && (
                            <Shelf title="Featured" entries={secondary} icon={Icon} large />
                        )}
                        {rest.length > 0 && (
                            <Shelf title={`All ${title}`} entries={rest} icon={Icon} />
                        )}
                    </>
                )}
            </div>
        </div>
    )
}

function LibraryHero({
    kind,
    title,
    subtitle,
    totalGroups,
    totalItems,
    featured,
    icon: Icon,
}: {
    kind: LibraryKind
    title: string
    subtitle: string
    totalGroups: number
    totalItems: number
    featured: OrganizerLibraryEntry | null
    icon: typeof Film
}) {
    return (
        <section className="relative overflow-hidden rounded-[2rem] bg-card elevation-2">
            <div className={cn(
                "absolute inset-0 opacity-60",
                kind === "movies" && "bg-gradient-to-br from-blue-500/25 via-fuchsia-500/10 to-transparent",
                kind === "tv" && "bg-gradient-to-br from-orange-500/25 via-amber-500/10 to-transparent",
                kind === "music" && "bg-gradient-to-br from-emerald-500/25 via-cyan-500/10 to-transparent",
            )} />
            {featured?.cover_id && (
                <div className="absolute inset-y-0 right-0 hidden w-1/2 md:block">
                    <AuthImage
                        apiSrc={`/media/${featured.cover_id}/thumbnail?size=lg`}
                        alt=""
                        className="h-full w-full object-cover opacity-30 blur-[1px] saturate-125"
                    />
                    <div className="absolute inset-0 bg-gradient-to-r from-card via-card/65 to-card/10" />
                </div>
            )}
            <div className="relative grid gap-6 p-6 md:grid-cols-[1fr_15rem] md:p-8">
                <div className="flex min-h-52 flex-col justify-between">
                    <div>
                        <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/15 text-primary">
                            <Icon className="h-6 w-6" />
                        </div>
                        <p className="text-[12px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                            Organized library
                        </p>
                        <h1 className="mt-2 text-4xl font-bold tracking-tight md:text-5xl">{title}</h1>
                        <p className="mt-3 max-w-xl text-[15px] leading-6 text-muted-foreground">
                            {heroCopy[kind]} {subtitle}
                        </p>
                    </div>
                    <div className="mt-8 flex flex-wrap gap-3">
                        <StatPill icon={Sparkles} label="Groups" value={totalGroups.toLocaleString()} />
                        <StatPill
                            icon={Clapperboard}
                            label={kind === "music" ? "Tracks" : "Items"}
                            value={totalItems.toLocaleString()}
                        />
                        {featured?.year && (
                            <StatPill icon={CalendarDays} label="Latest year" value={String(featured.year)} />
                        )}
                    </div>
                </div>
                <div className="hidden md:block">
                    <CoverCard entry={featured} icon={Icon} oversized />
                </div>
            </div>
        </section>
    )
}

function StatPill({
    icon: Icon,
    label,
    value,
}: {
    icon: typeof Sparkles
    label: string
    value: string
}) {
    return (
        <div className="flex items-center gap-2 rounded-full bg-background/70 px-3 py-2">
            <Icon className="h-4 w-4 text-primary" />
            <span className="text-[12px] text-muted-foreground">{label}</span>
            <span className="text-sm font-semibold tabular-nums">{value}</span>
        </div>
    )
}

function Shelf({
    title,
    entries,
    icon,
    large,
}: {
    title: string
    entries: OrganizerLibraryEntry[]
    icon: typeof Film
    large?: boolean
}) {
    return (
        <section>
            <div className="mb-3 flex items-baseline justify-between px-1">
                <h2 className="text-[22px] font-bold tracking-tight">{title}</h2>
                <span className="text-sm text-muted-foreground">{entries.length}</span>
            </div>
            <div className={cn(
                "grid gap-4",
                large
                    ? "grid-cols-2 sm:grid-cols-3 lg:grid-cols-6"
                    : "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-7",
            )}>
                {entries.map((entry) => (
                    <CoverCard key={entry.key} entry={entry} icon={icon} />
                ))}
            </div>
        </section>
    )
}

function CoverCard({
    entry,
    icon: Icon,
    oversized,
}: {
    entry: OrganizerLibraryEntry | null
    icon: typeof Film
    oversized?: boolean
}) {
    if (!entry) {
        return (
            <div className="flex aspect-[2/3] items-center justify-center rounded-[1.75rem] bg-secondary/50">
                <Icon className="h-10 w-10 text-muted-foreground/40" />
            </div>
        )
    }
    return (
        <button type="button" className="group text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <div className={cn(
                "relative overflow-hidden rounded-[1.35rem] bg-secondary/50 shadow-lg shadow-black/10 transition-transform duration-300 group-hover:-translate-y-0.5",
                oversized ? "aspect-[2/3]" : "aspect-[2/3]",
            )}>
                {entry.cover_id ? (
                    <AuthImage
                        apiSrc={`/media/${entry.cover_id}/thumbnail?size=lg`}
                        alt=""
                        className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
                        fallback={<FallbackCover icon={Icon} />}
                    />
                ) : (
                    <FallbackCover icon={Icon} />
                )}
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-3">
                    <div className="text-xs font-semibold text-white/90">{entry.count.toLocaleString()}</div>
                </div>
            </div>
            <div className="mt-2 px-1">
                <h3 className="truncate text-[15px] font-semibold">{entry.title}</h3>
                {entry.subtitle && (
                    <p className="mt-0.5 truncate text-[13px] text-muted-foreground">{entry.subtitle}</p>
                )}
            </div>
        </button>
    )
}

function FallbackCover({ icon: Icon }: { icon: typeof Film }) {
    return (
        <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-secondary to-muted">
            <Icon className="h-10 w-10 text-muted-foreground/35" />
        </div>
    )
}

export function MoviesPage() {
    return <OrganizedLibraryPage kind="movies" />
}

export function TvSeriesPage() {
    return <OrganizedLibraryPage kind="tv" />
}

export function MusicPage() {
    return <MusicLibraryPage />
}

function organizerErrorMessage(err: unknown, title: string) {
    if (axios.isAxiosError<{ detail?: string }>(err)) {
        return err.response?.data?.detail ?? err.message
    }
    return err instanceof Error ? err.message : `Could not load ${title.toLowerCase()}`
}
