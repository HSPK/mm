import { useCallback } from "react"
import { useNavigate } from "react-router-dom"

import { useAuthStore } from "@/stores/auth"

export function useLogoutRedirect() {
    const navigate = useNavigate()
    const logout = useAuthStore((s) => s.logout)

    return useCallback(() => {
        logout()
        navigate("/login", { replace: true })
    }, [logout, navigate])
}
