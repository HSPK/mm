import axios, { type AxiosInstance } from "axios"
import { config } from "@/lib/config"
import { browserTokenStorage, type TokenStorage } from "@/lib/token-storage"

export type UnauthorizedHandler = () => void

export interface ApiClientOptions {
    baseUrl?: string
    tokenStorage?: TokenStorage
    onUnauthorized?: UnauthorizedHandler
}

const defaultUnauthorized: UnauthorizedHandler = () => {
    browserTokenStorage.clear()
    window.location.hash = "#/login"
}

/**
 * Build a configured axios instance. Each piece (base URL, token provider,
 * 401 policy) is injected so the same client shape works in production,
 * tests, or alternative deployments.
 */
export function createApiClient(opts: ApiClientOptions = {}): AxiosInstance {
    const baseURL = opts.baseUrl ?? config.apiBaseUrl
    const tokenStorage = opts.tokenStorage ?? browserTokenStorage
    const onUnauthorized = opts.onUnauthorized ?? defaultUnauthorized

    const instance = axios.create({ baseURL })

    instance.interceptors.request.use((req) => {
        const token = tokenStorage.get()
        if (token) {
            req.headers.Authorization = `Bearer ${token}`
        }
        return req
    })

    instance.interceptors.response.use(
        (res) => res,
        (err) => {
            if (err.response?.status === 401) {
                onUnauthorized()
            }
            return Promise.reject(err)
        },
    )

    return instance
}

export const api: AxiosInstance = createApiClient()
