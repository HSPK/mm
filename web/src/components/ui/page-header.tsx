import { useEffect, useMemo, type ReactNode } from "react"
import { useLocation } from "react-router-dom"
import { useHeaderRegistration } from "@/components/navigation/header-context"

interface PageHeaderProps {
    title: string
    back?: boolean | (() => void)
    backLabel?: string
    actions?: ReactNode
}

/**
 * Compact page toolbar for back buttons and page-local actions. The visible
 * title lives in the global app header so routed pages do not duplicate it.
 */
export function PageHeader({ title, back, backLabel, actions }: PageHeaderProps) {
    const location = useLocation()
    const register = useHeaderRegistration()
    const locationKey = `${location.pathname}?${location.search}`
    const config = useMemo(
        () => ({ locationKey, title, back, backLabel, actions }),
        [actions, back, backLabel, locationKey, title],
    )

    useEffect(() => register(config), [config, register])

    return null
}
