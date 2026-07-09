import type { ReactNode } from "react"
import { Input } from "@/components/ui/input"

export function LabeledSearchInput({
    label,
    value,
    onChange,
}: {
    label: string
    value: string
    onChange: (value: string) => void
}) {
    return (
        <label className="space-y-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                {label}
            </span>
            <Input value={value} onChange={(event) => onChange(event.target.value)} />
        </label>
    )
}

export function LabeledScrapeInput({
    label,
    value,
    onChange,
    onEnter,
    inputMode,
}: {
    label: string
    value: string
    onChange: (value: string) => void
    onEnter: () => Promise<void>
    inputMode?: "numeric" | "text"
}) {
    return (
        <label className="space-y-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</span>
            <input
                value={value}
                onChange={(event) => onChange(event.target.value)}
                onKeyDown={(event) => {
                    if (event.key === "Enter") void onEnter()
                }}
                inputMode={inputMode}
                className="h-9 w-full rounded-xl bg-secondary/60 px-3 text-sm outline-none"
            />
        </label>
    )
}

export function LabeledSelect({
    label,
    value,
    onChange,
    children,
}: {
    label: string
    value: string
    onChange: (value: string) => void
    children: ReactNode
}) {
    return (
        <label className="space-y-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</span>
            <select
                value={value}
                onChange={(event) => onChange(event.target.value)}
                className="h-9 w-full rounded-xl bg-secondary/60 px-2 text-sm outline-none"
            >
                {children}
            </select>
        </label>
    )
}
