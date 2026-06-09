import { type ButtonHTMLAttributes, forwardRef } from "react"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    /**
     * Apple HIG-aligned button styles:
     *  - `filled` (default): solid primary
     *  - `tinted`: low-emphasis primary on a subtle wash
     *  - `secondary`: neutral filled (e.g. cancel)
     *  - `plain`: tappable text-only (toolbar actions)
     *  - `destructive`: red filled
     *  - `bordered`: outline only (rare)
     *  - `outline`/`ghost`/`default`: kept as aliases for back-compat
     */
    variant?:
        | "filled"
        | "tinted"
        | "secondary"
        | "plain"
        | "destructive"
        | "bordered"
        | "default"
        | "ghost"
        | "outline"
    size?: "default" | "sm" | "lg" | "icon"
    loading?: boolean
}

const variants: Record<string, string> = {
    filled:
        "bg-primary text-primary-foreground hover:opacity-90 active:opacity-80 shadow-sm",
    tinted:
        "bg-primary/15 text-primary hover:bg-primary/20 active:bg-primary/25",
    secondary:
        "bg-secondary text-secondary-foreground hover:bg-secondary/80 active:bg-secondary/70",
    plain:
        "text-primary hover:bg-secondary/40 active:bg-secondary/60",
    destructive:
        "bg-destructive text-destructive-foreground hover:opacity-90 active:opacity-80 shadow-sm",
    bordered:
        "border border-border bg-transparent text-primary hover:bg-secondary/40 active:bg-secondary/60",
    // back-compat aliases
    default: "bg-primary text-primary-foreground hover:opacity-90 active:opacity-80 shadow-sm",
    ghost: "text-foreground hover:bg-secondary/40 active:bg-secondary/60",
    outline:
        "border border-border bg-transparent text-foreground hover:bg-secondary/40 active:bg-secondary/60",
}

const sizes: Record<string, string> = {
    // Apple's default control height is 32–44pt; web baseline at 36/40.
    default: "h-10 px-5 text-[15px] rounded-full",
    sm: "h-8 px-3.5 text-[13px] rounded-full",
    lg: "h-12 px-7 text-[17px] rounded-full",
    // 44px = WCAG 2.5.5 touch-target minimum
    icon: "h-11 w-11 rounded-full",
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = "filled", size = "default", loading, disabled, children, ...props }, ref) => (
        <button
            ref={ref}
            className={cn(
                "inline-flex items-center justify-center gap-2 font-medium transition-all duration-150",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                "disabled:pointer-events-none disabled:opacity-50",
                "cursor-pointer select-none",
                variants[variant],
                sizes[size],
                className,
            )}
            disabled={disabled || loading}
            aria-busy={loading || undefined}
            {...props}
        >
            {loading && <Spinner size="sm" label="" />}
            {children}
        </button>
    ),
)
Button.displayName = "Button"
