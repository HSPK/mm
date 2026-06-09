/**
 * Insert `id` into a set while keeping the size at most `limit` by evicting
 * the oldest entry (insertion order, since Set preserves it). Returns the
 * original Set unchanged if `id` is already present (cheap no-op for React).
 */
export function addBoundedId(prev: Set<number>, id: number, limit = 32): Set<number> {
    if (prev.has(id)) return prev
    const next = new Set(prev)
    next.add(id)
    while (next.size > limit) {
        const oldest = next.values().next().value
        if (oldest === undefined) break
        next.delete(oldest)
    }
    return next
}
