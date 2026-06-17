export interface ImageTransform {
    scale: number
    x: number
    y: number
}

export interface ViewportSize {
    width: number
    height: number
}

export interface ViewportPoint {
    x: number
    y: number
}

export const MIN_IMAGE_SCALE = 1
export const MAX_IMAGE_SCALE = 8

export function clampImageScale(scale: number, min = MIN_IMAGE_SCALE, max = MAX_IMAGE_SCALE): number {
    if (!Number.isFinite(scale)) return min
    return Math.min(max, Math.max(min, scale))
}

export function wheelDeltaToScale(scale: number, deltaY: number): number {
    return scale * Math.exp(-deltaY * 0.0022)
}

export function zoomAt(
    transform: ImageTransform,
    focal: ViewportPoint,
    nextScale: number,
    viewport: ViewportSize,
): ImageTransform {
    const scale = clampImageScale(nextScale)
    if (scale <= MIN_IMAGE_SCALE) return { scale: MIN_IMAGE_SCALE, x: 0, y: 0 }

    const ratio = scale / Math.max(transform.scale, MIN_IMAGE_SCALE)
    return clampImagePan({
        scale,
        x: focal.x - (focal.x - transform.x) * ratio,
        y: focal.y - (focal.y - transform.y) * ratio,
    }, viewport)
}

export function clampImagePan(transform: ImageTransform, viewport: ViewportSize): ImageTransform {
    if (transform.scale <= MIN_IMAGE_SCALE || viewport.width <= 0 || viewport.height <= 0) {
        return { scale: MIN_IMAGE_SCALE, x: 0, y: 0 }
    }
    const maxX = viewport.width * (transform.scale - 1) / 2
    const maxY = viewport.height * (transform.scale - 1) / 2
    return {
        scale: transform.scale,
        x: Math.min(maxX, Math.max(-maxX, transform.x)),
        y: Math.min(maxY, Math.max(-maxY, transform.y)),
    }
}

export function distance(a: ViewportPoint, b: ViewportPoint): number {
    return Math.hypot(a.x - b.x, a.y - b.y)
}

export function midpoint(a: ViewportPoint, b: ViewportPoint): ViewportPoint {
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
}
