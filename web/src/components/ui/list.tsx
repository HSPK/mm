import { ChevronRight } from "lucide-react"
import type { HTMLAttributes, ReactNode } from "react"
import { cn } from "@/lib/utils"

/**
 * Apple grouped inset list — used throughout Settings, Profile, and other
 * forms-like pages. Mirrors `UITableView` style `.insetGrouped`.
 *
 * Structure:
 *   <ListGroup label="Section">
 *     <ListRow icon={...} label="Setting" trailing="Value" onClick={...} />
 *     <ListRow ... />
 *   </ListGroup>
 *
 * Rows are visually joined by hairline separators inside a single rounded
 * card surface; first/last rows get the rounded corners.
 */

interface ListGroupProps {
    label?: string
    footer?: string
    children: ReactNode
    className?: string
}

export function ListGroup({ label, footer, children, className }: ListGroupProps) {
    return (
        <section className={cn("space-y-2.5", className)}>
            {label && (
                <h3 className="px-1 text-[12px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/55 sm:px-2">
                    {label}
                </h3>
            )}
            <div className="overflow-hidden rounded-3xl border border-border/60 bg-card shadow-sm">
                <ul className="divide-y divide-border/50">{children}</ul>
            </div>
            {footer && (
                <p className="px-1 text-[12px] leading-snug text-muted-foreground/65 sm:px-2">
                    {footer}
                </p>
            )}
        </section>
    )
}

export type RowIcon = { icon: ReactNode; tint?: string }

interface ListRowProps {
    icon?: ReactNode | RowIcon
    label: string
    sublabel?: string
    trailing?: ReactNode
    /** Adds a chevron disclosure indicator on the right. */
    chevron?: boolean
    /** Marks the row destructive (red text). */
    destructive?: boolean
    onClick?: () => void
    disabled?: boolean
    href?: string
    className?: string
}

export function ListRow({
    icon,
    label,
    sublabel,
    trailing,
    chevron,
    destructive,
    onClick,
    disabled,
    href,
    className,
}: ListRowProps) {
    const isInteractive = !!onClick || !!href
    const Element = href ? "a" : isInteractive ? "button" : "div"

    const iconNode = icon != null && (typeof icon === "object" && "icon" in icon && (icon as RowIcon).icon != null
        ? (
            <span
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl text-white shadow-sm"
                style={{ background: (icon as RowIcon).tint ?? "var(--color-primary)" }}
            >
                {(icon as RowIcon).icon}
            </span>
        )
        : (
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-secondary/45 text-muted-foreground">
                {icon as ReactNode}
            </span>
        )
    )

    return (
        <li className="list-none">
            <Element
                {...(href ? { href } : { type: "button" })}
                onClick={onClick}
                disabled={disabled}
                className={cn(
                    "flex w-full items-center gap-3.5 px-4 py-3.5 text-left",
                    "text-[15px] leading-tight",
                    isInteractive && "cursor-pointer transition-colors hover:bg-secondary/45 active:bg-secondary/65",
                    destructive ? "text-destructive" : "text-foreground",
                    disabled && "opacity-50 pointer-events-none",
                    className,
                )}
            >
                {iconNode}
                <div className="flex-1 min-w-0">
                    <div className="truncate font-medium">{label}</div>
                    {sublabel && (
                        <div className="mt-1 truncate text-[13px] leading-snug text-muted-foreground/65">
                            {sublabel}
                        </div>
                    )}
                </div>
                {trailing != null && (
                    <div className="flex shrink-0 items-center gap-2 text-[14px] text-muted-foreground">
                        {trailing}
                    </div>
                )}
                {chevron && (
                    <ChevronRight className="h-4 w-4 text-muted-foreground/40 shrink-0 stroke-[2.5]" />
                )}
            </Element>
        </li>
    )
}

/** Page container that places sections on the secondary system background. */
export function ListPage({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
    return <div className={cn("mx-auto max-w-3xl space-y-7 p-4 sm:p-6", className)} {...props} />
}
