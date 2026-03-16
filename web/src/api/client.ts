import axios from "axios"

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
})

// Attach auth token to every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem("mm_token")
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// Auto-logout on 401
api.interceptors.response.use(
    (res) => res,
    (err) => {
        if (err.response?.status === 401) {
            localStorage.removeItem("mm_token")
            window.location.hash = "#/login"
        }
        return Promise.reject(err)
    },
)

export { api }
