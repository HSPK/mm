import { Calendar, Camera, FileText, MapPin } from "lucide-react"
import type { MediaDetail } from "@/api/types"

function ExifChip({ children }: { children: React.ReactNode }) {
    return (
        <span className="rounded-md border border-border/60 bg-secondary/45 px-2 py-[3px] text-[11px] font-mono text-muted-foreground">
            {children}
        </span>
    )
}

interface MetadataViewProps {
    detail: MediaDetail
    onApplyLocationFilter: (lat: number, lon: number) => void
}

export function MetadataView({ detail, onApplyLocationFilter }: MetadataViewProps) {
    const md = detail.metadata
    const placeName = md?.location_label || md?.location_city || null

    return (
        <div className="py-4 space-y-4">
            {md?.date_taken && (
                <div className="flex gap-3">
                    <Calendar className="h-[15px] w-[15px] text-muted-foreground mt-[3px] shrink-0" />
                    <div>
                        <div className="text-foreground/85 text-[13px] font-medium select-text">
                            {new Date(md.date_taken).toLocaleDateString(undefined, {
                                weekday: "short", year: "numeric", month: "long", day: "numeric",
                            })}
                        </div>
                        <div className="text-muted-foreground text-xs mt-0.5 select-text">
                            {new Date(md.date_taken).toLocaleTimeString(undefined, {
                                hour: "2-digit", minute: "2-digit",
                            })}
                        </div>
                    </div>
                </div>
            )}

            {(md?.camera_model || md?.lens_model) && (
                <div className="flex gap-3">
                    <Camera className="h-[15px] w-[15px] text-muted-foreground mt-[3px] shrink-0" />
                    <div className="min-w-0">
                        {md.camera_make && (
                            <div className="text-muted-foreground text-[10px] uppercase tracking-wider">
                                {md.camera_make}
                            </div>
                        )}
                        {md.camera_model && (
                            <div className="text-foreground/85 text-[13px] font-medium">
                                {md.camera_model}
                            </div>
                        )}
                        {md.lens_model && (
                            <div className="text-muted-foreground text-xs mt-0.5">{md.lens_model}</div>
                        )}
                        <div className="flex flex-wrap gap-1.5 mt-2">
                            {md.focal_length && <ExifChip>{md.focal_length}mm</ExifChip>}
                            {md.aperture && <ExifChip>ƒ/{md.aperture}</ExifChip>}
                            {md.iso && <ExifChip>ISO {md.iso}</ExifChip>}
                            {md.shutter_speed && <ExifChip>{md.shutter_speed}s</ExifChip>}
                        </div>
                    </div>
                </div>
            )}

            {(md?.gps_lat != null && md?.gps_lon != null) && (
                <div className="flex gap-4 items-start">
                    <div className="mt-1">
                        <MapPin className="h-4 w-4 text-primary/70 shrink-0" />
                    </div>
                    <div className="flex flex-col gap-0.5 min-w-0">
                        <button
                            type="button"
                            title="Filter by this location"
                            className="w-fit rounded-sm text-left text-foreground/90 text-[13px] font-medium leading-tight hover:text-primary focus:outline-none focus:ring-1 focus:ring-primary/50 transition-colors hover:underline decoration-primary/30 underline-offset-4"
                            onClick={() => {
                                if (md.gps_lat == null || md.gps_lon == null) return
                                onApplyLocationFilter(md.gps_lat, md.gps_lon)
                            }}
                        >
                            {placeName || md.location_city || "Unknown Location"}
                        </button>

                        {(md.location_city || md.location_country) && (
                            <div className="text-muted-foreground text-[11px] font-medium tracking-wide">
                                {[
                                    (md.location_city !== placeName ? md.location_city : null),
                                    (md.location_country !== placeName ? md.location_country : null),
                                ].filter(Boolean).join(", ")}
                            </div>
                        )}

                        <a
                            href={`https://uri.amap.com/marker?position=${md.gps_lon},${md.gps_lat}&name=${encodeURIComponent(md.location_label || "Location")}&coordinate=wgs84`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] font-mono text-muted-foreground bg-secondary/35 px-1.5 py-0.5 rounded border border-border/60 hover:bg-secondary hover:text-foreground transition-colors w-fit block mt-1.5"
                            title="Open in Amap"
                        >
                            {md.gps_lat.toFixed(5)}, {md.gps_lon.toFixed(5)}
                        </a>
                    </div>
                </div>
            )}

            <div className="flex gap-3">
                <FileText className="h-[15px] w-[15px] text-muted-foreground mt-[3px] shrink-0" />
                <div className="text-muted-foreground text-[11px] font-mono break-all select-all leading-relaxed bg-secondary/35 px-2 py-1.5 rounded-lg min-w-0 flex-1">
                    {detail.path}
                </div>
            </div>
        </div>
    )
}
