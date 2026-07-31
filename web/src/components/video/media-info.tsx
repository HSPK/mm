import type { VideoMediaInfo } from "@/api/player"
import { cn } from "@/lib/utils"

export function MediaInfoChips({
    info,
    className,
    variant = "overlay",
}: {
    info: VideoMediaInfo
    className?: string
    variant?: "overlay" | "inline"
}) {
    const chips: { label: string; tone?: "hdr" }[] = []
    const res = resolutionLabel(info.width, info.height)
    if (res) chips.push({ label: res })
    if (info.video_codec) chips.push({ label: codecLabel(info.video_codec) })
    if (info.hdr) chips.push({ label: info.hdr, tone: "hdr" })
    else if (info.bit_depth && info.bit_depth > 8) chips.push({ label: `${info.bit_depth}-bit` })
    if (info.audio_codec) chips.push({ label: codecLabel(info.audio_codec) })
    if (info.frame_rate) chips.push({ label: `${Math.round(info.frame_rate)} fps` })
    if (chips.length === 0) return null
    const baseTone = variant === "inline" ? "bg-secondary text-muted-foreground" : "bg-white/10 text-white/75"
    const hdrTone = variant === "inline"
        ? "bg-amber-500/20 text-amber-700 dark:text-amber-300"
        : "bg-amber-400/20 text-amber-300"
    return (
        <div className={cn("flex flex-wrap items-center gap-1.5", className)}>
            {chips.map((chip) => (
                <span
                    key={chip.label}
                    className={cn(
                        "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
                        chip.tone === "hdr" ? hdrTone : baseTone,
                    )}
                >
                    {chip.label}
                </span>
            ))}
        </div>
    )
}

function resolutionLabel(width?: number | null, height?: number | null) {
    if (!width || !height) return ""
    if (height >= 2000 || width >= 3800) return "4K"
    if (height >= 1400 || width >= 2560) return "1440p"
    if (height >= 1000 || width >= 1900) return "1080p"
    if (height >= 700 || width >= 1200) return "720p"
    return `${width}×${height}`
}

function codecLabel(codec: string) {
    const map: Record<string, string> = {
        h264: "H.264",
        avc: "H.264",
        avc1: "H.264",
        hevc: "HEVC",
        h265: "HEVC",
        av1: "AV1",
        vp9: "VP9",
        vp8: "VP8",
        mpeg2video: "MPEG-2",
        mpeg4: "MPEG-4",
        vc1: "VC-1",
        aac: "AAC",
        ac3: "AC-3",
        eac3: "E-AC-3",
        dts: "DTS",
        truehd: "TrueHD",
        flac: "FLAC",
        mp3: "MP3",
        opus: "Opus",
        vorbis: "Vorbis",
        pcm_s16le: "PCM",
    }
    return map[codec] || codec.toUpperCase()
}
