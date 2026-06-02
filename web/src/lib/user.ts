import type { User } from "@/api/types"

export function getUserDisplayName(user: User | null | undefined) {
    return user?.display_name || user?.username || "User"
}

export function getUserInitial(user: User | null | undefined) {
    return getUserDisplayName(user).slice(0, 1).toUpperCase() || "U"
}
