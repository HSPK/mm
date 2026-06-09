import { config } from "./config"

export interface TokenStorage {
    get(): string | null
    set(token: string): void
    clear(): void
}

// localStorage + cookie mirror. The cookie lets the server validate websocket /
// streaming requests where Authorization headers aren't easily added.
function writeCookie(name: string, value: string) {
    document.cookie = `${name}=${value}; path=/; SameSite=Strict`
}

function clearCookie(name: string) {
    document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`
}

export function createBrowserTokenStorage(opts?: {
    storageKey?: string
    cookieName?: string
}): TokenStorage {
    const storageKey = opts?.storageKey ?? config.tokenStorageKey
    const cookieName = opts?.cookieName ?? config.tokenCookieName
    return {
        get: () => localStorage.getItem(storageKey),
        set: (token) => {
            localStorage.setItem(storageKey, token)
            writeCookie(cookieName, token)
        },
        clear: () => {
            localStorage.removeItem(storageKey)
            clearCookie(cookieName)
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
