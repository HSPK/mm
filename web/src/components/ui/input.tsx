import {
    forwardRef,
    useId,
    type InputHTMLAttributes,
    type ReactNode,
} from "react"
import { cn } from "@/lib/utils"

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
    label?: string
    error?: string
    leftIcon?: ReactNode
    rightIcon?: ReactNode
    /** Wrapper className; use `className` for the underlying <input>. */
    wrapperClassName?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
    (
        {
            className,
            wrapperClassName,
            type = "text",
            label,
            error,
            leftIcon,
            rightIcon,
            id: providedId,
            ...props
        },
        ref,
    ) => {
        const autoId = useId()
        const id = providedId ?? autoId
        const errorId = error ? `${id}-error` : undefined

        const inputEl = (
            <div className={cn("relative", wrapperClassName)}>
                {leftIcon && (
                    <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60">
                        {leftIcon}
                    </span>
                )}
                <input
                    ref={ref}
                    id={id}
                    type={type}
                    aria-invalid={error ? true : undefined}
                    aria-describedby={errorId}
                    className={cn(
                        "flex h-11 w-full rounded-xl bg-secondary/60 text-[15px]",
                        "px-3.5 py-2",
                        leftIcon && "pl-10",
                        rightIcon && "pr-10",
                        "placeholder:text-muted-foreground/70",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:bg-card",
                        "disabled:cursor-not-allowed disabled:opacity-50",
                        "transition-colors",
                        error && "ring-2 ring-destructive/50 focus-visible:ring-destructive",
                        className,
                    )}
                    {...props}
                />
                {rightIcon && (
                    <span className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60">
                        {rightIcon}
                    </span>
                )}
            </div>
        )

        if (!label && !error) return inputEl

        return (
            <div className="space-y-1.5">
                {label && (
                    <label htmlFor={id} className="text-[13px] font-medium text-muted-foreground/90 px-1 uppercase tracking-wider">
                        {label}
                    </label>
                )}
                {inputEl}
                {error && (
                    <p id={errorId} className="text-[12px] text-destructive px-1">{error}</p>
                )}
            </div>
        )
    },
)
Input.displayName = "Input"
