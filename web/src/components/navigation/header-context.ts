import { createContext, useContext, type ReactNode } from "react"

export interface HeaderConfig {
    locationKey: string
    title: string
    back?: boolean | (() => void)
    backLabel?: string
    search?: ReactNode
    actions?: ReactNode
    immersive?: boolean
}

export const HeaderConfigContext = createContext<HeaderConfig | null>(null)
export const HeaderRegistrationContext = createContext<((config: HeaderConfig) => () => void) | null>(null)

export function useHeaderConfig() {
    return useContext(HeaderConfigContext)
}

export function useHeaderRegistration() {
    const register = useContext(HeaderRegistrationContext)
    if (!register) {
        throw new Error("useHeaderRegistration must be used within HeaderProvider")
    }
    return register
}
