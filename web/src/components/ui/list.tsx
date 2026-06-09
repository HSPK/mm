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
        <section className={cn("space-y-2", className)}>
            {label && (
                <h3 className="px-4 text-[13px] uppercase tracking-wider text-muted-foreground/80 font-medium">
                    {label}
                </h3>
            )}
            <div className="bg-card rounded-2xl overflow-hidden elevation-1">
                <ul className="divide-y divide-border">{children}</ul>
            </div>
            {footer && (
                <p className="px-4 text-[12px] text-muted-foreground/70 leading-snug">
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
                className="flex h-7 w-7 items-center justify-center rounded-[7px] text-white shrink-0"
                style={{ background: (icon as RowIcon).tint ?? "var(--color-primary)" }}
            >
                {(icon as RowIcon).icon}
            </span>
        )
        : (
            <span className="flex h-7 w-7 items-center justify-center text-muted-foreground/80 shrink-0">
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
                    "w-full flex items-center gap-3 px-4 py-3 text-left",
                    "text-[15px] leading-tight",
                    isInteractive && "hover:bg-secondary/40 active:bg-secondary/60 transition-colors cursor-pointer",
                    destructive ? "text-destructive" : "text-foreground",
                    disabled && "opacity-50 pointer-events-none",
                    className,
                )}
            >
                {iconNode}
                <div className="flex-1 min-w-0">
                    <div className="truncate">{label}</div>
                    {sublabel && (
                        <div className="text-[13px] text-muted-foreground/70 truncate mt-0.5">
                            {sublabel}
                        </div>
                    )}
                </div>
                {trailing != null && (
                    <div className="text-muted-foreground text-[15px] flex items-center gap-2 shrink-0">
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
    return <div className={cn("max-w-2xl mx-auto p-4 sm:p-6 space-y-7", className)} {...props} />
}
