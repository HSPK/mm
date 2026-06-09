import MockAdapter from "axios-mock-adapter"
import { describe, expect, it, vi } from "vitest"
import { createMemoryTokenStorage } from "@/lib/token-storage"
import { createApiClient } from "./client"

describe("createApiClient", () => {
    it("attaches the Bearer token from storage", async () => {
        const tokenStorage = createMemoryTokenStorage("tok-123")
        const client = createApiClient({ baseUrl: "/api", tokenStorage, onUnauthorized: vi.fn() })
        const mock = new MockAdapter(client)
        mock.onGet("/ping").reply((config) => {
            expect(config.headers?.Authorization).toBe("Bearer tok-123")
            return [200, { ok: true }]
        })

        await client.get("/ping")
    })

    it("omits Authorization when no token is set", async () => {
        const client = createApiClient({
            baseUrl: "/api",
            tokenStorage: createMemoryTokenStorage(),
            onUnauthorized: vi.fn(),
        })
        const mock = new MockAdapter(client)
        mock.onGet("/ping").reply((config) => {
            expect(config.headers?.Authorization).toBeUndefined()
            return [200, {}]
        })

        await client.get("/ping")
    })

    it("invokes the unauthorized handler on 401 and rethrows", async () => {
        const onUnauthorized = vi.fn()
        const client = createApiClient({
            baseUrl: "/api",
            tokenStorage: createMemoryTokenStorage("tok"),
            onUnauthorized,
        })
        const mock = new MockAdapter(client)
        mock.onGet("/secret").reply(401)

        await expect(client.get("/secret")).rejects.toThrow()
        expect(onUnauthorized).toHaveBeenCalledOnce()
    })

    it("does not invoke unauthorized handler on other errors", async () => {
        const onUnauthorized = vi.fn()
        const client = createApiClient({
            baseUrl: "/api",
            tokenStorage: createMemoryTokenStorage("tok"),
            onUnauthorized,
        })
        const mock = new MockAdapter(client)
        mock.onGet("/boom").reply(500)

        await expect(client.get("/boom")).rejects.toThrow()
        expect(onUnauthorized).not.toHaveBeenCalled()
    })
})
