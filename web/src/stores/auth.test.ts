import { beforeEach, describe, expect, it, vi } from "vitest"
import type { AuthRepository } from "@/api/auth"
import { createMemoryTokenStorage } from "@/lib/token-storage"
import { createAuthStore } from "./auth"

function makeRepo(overrides: Partial<AuthRepository> = {}): AuthRepository {
    return {
        login: vi.fn(async () => ({
            token: "tok-1",
            user: { id: 1, username: "u", display_name: "User", is_admin: false },
        })),
        me: vi.fn(async () => ({ id: 1, username: "u", display_name: "User", is_admin: false })),
        ...overrides,
    }
}

let store: ReturnType<typeof createAuthStore>
let storage: ReturnType<typeof createMemoryTokenStorage>

beforeEach(() => {
    storage = createMemoryTokenStorage()
    store = createAuthStore({ repo: makeRepo(), tokenStorage: storage })
})

describe("createAuthStore", () => {
    it("seeds token from storage on construction", () => {
        const seeded = createMemoryTokenStorage("seed-token")
        const s = createAuthStore({ repo: makeRepo(), tokenStorage: seeded })
        expect(s.getState().token).toBe("seed-token")
        expect(s.getState().isAuthenticated).toBe(true)
    })

    it("login stores token then fetches the user", async () => {
        const ok = await store.getState().login("u", "p")
        expect(ok).toBe(true)
        const s = store.getState()
        expect(s.token).toBe("tok-1")
        expect(s.user?.username).toBe("u")
        expect(storage.get()).toBe("tok-1")
    })

    it("login returns false and sets error on failure", async () => {
        store = createAuthStore({
            repo: makeRepo({
                login: vi.fn(async () => {
                    throw new Error("nope")
                }),
            }),
            tokenStorage: storage,
        })
        const ok = await store.getState().login("u", "p")
        expect(ok).toBe(false)
        expect(store.getState().error).toBe("Login failed")
        expect(store.getState().token).toBeNull()
    })

    it("logout clears storage and state", () => {
        store.setState({ token: "tok-1", user: { id: 1, username: "u", display_name: "U", is_admin: false } })
        storage.set("tok-1")
        store.getState().logout()
        const s = store.getState()
        expect(s.token).toBeNull()
        expect(s.user).toBeNull()
        expect(storage.get()).toBeNull()
    })

    it("fetchUser logs out on failure", async () => {
        const failRepo = makeRepo({ me: vi.fn(async () => { throw new Error("401") }) })
        store = createAuthStore({ repo: failRepo, tokenStorage: storage })
        store.setState({ token: "tok-1" })
        storage.set("tok-1")
        await store.getState().fetchUser()
        expect(store.getState().token).toBeNull()
    })
})
