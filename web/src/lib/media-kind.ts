// Read-only catalogues used to decide whether the original media file can be
// shown by the browser or must go through the server-side preview pipeline.

export const RAW_LOWER_EXTENSIONS = new Set([
    ".heic",
    ".heif",
    ".cr2",
    ".cr3",
    ".nef",
    ".arw",
    ".dng",
    ".raf",
    ".orf",
    ".rw2",
    ".pef",
    ".srw",
])

export const RAW_BADGE_EXTENSIONS = new Set([
    "CR2",
    "CR3",
    "ARW",
    "NEF",
    "DNG",
    "RAF",
    "ORF",
    "RW2",
    "PEF",
    "SRW",
    "NRW",
    "3FR",
    "IIQ",
    "ERF",
    "MEF",
    "MOS",
])

export const NATIVE_IMAGE_EXTENSIONS = new Set([
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".avif",
])

export function isRawExtension(ext: string): boolean {
    return RAW_LOWER_EXTENSIONS.has(ext.toLowerCase())
}

export function isRawBadgeExtension(extUpper: string): boolean {
    return RAW_BADGE_EXTENSIONS.has(extUpper.toUpperCase())
}

export function canDisplayOriginalImage(item: { extension: string }): boolean {
    return NATIVE_IMAGE_EXTENSIONS.has(item.extension.toLowerCase())
}
