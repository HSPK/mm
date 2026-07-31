import { config } from "./config"

export interface TokenStorage {
    get(): string | null
    set(token: string): void
    clear(): void
}

export function createBrowserTokenStorage(opts?: {
    storageKey?: string
}): TokenStorage {
    const storageKey = opts?.storageKey ?? config.tokenStorageKey
    return {
        get: () => localStorage.getItem(storageKey),
        set: (token) => {
            localStorage.setItem(storageKey, token)
        },
        clear: () => {
            localStorage.removeItem(storageKey)
        },
    }
}

// In-memory implementation for tests.
export function createMemoryTokenStorage(initial: string | null = null): TokenStorage {
    let current = initial
    return {
        get: () => current,
        set: (token) => {
            current = token
        },
        clear: () => {
            current = null
        },
    }
}

export const browserTokenStorage = createBrowserTokenStorage()
