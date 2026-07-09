import { useCallback, useMemo, useState, type ReactNode } from "react"
import {
    HeaderConfigContext,
    HeaderRegistrationContext,
    type HeaderConfig,
} from "@/components/navigation/header-context"

export function HeaderProvider({ children }: { children: ReactNode }) {
    const [config, setConfig] = useState<HeaderConfig | null>(null)

    const register = useCallback((next: HeaderConfig) => {
        setConfig(next)
        return () => {
            setConfig((current) => (current === next ? null : current))
        }
    }, [])

    const registrationValue = useMemo(() => register, [register])

    return (
        <HeaderRegistrationContext.Provider value={registrationValue}>
            <HeaderConfigContext.Provider value={config}>
                {children}
            </HeaderConfigContext.Provider>
        </HeaderRegistrationContext.Provider>
    )
}
