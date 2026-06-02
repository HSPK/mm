const FOCUSABLE_SELECTOR = [
    "button:not([disabled])",
    "input:not([disabled])",
    "textarea:not([disabled])",
    "select:not([disabled])",
    "video[controls]",
    "a[href]",
    '[tabindex]:not([tabindex="-1"])',
].join(", ")

export function getFocusableElements(root: HTMLElement | null) {
    return Array.from(root?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR) ?? [])
        .filter((el) => el.offsetParent !== null && !el.closest('[aria-hidden="true"], [inert]'))
}

export function trapFocus(e: KeyboardEvent, root: HTMLElement | null) {
    if (e.key !== "Tab") return false

    const focusable = getFocusableElements(root)
    if (focusable.length === 0) {
        e.preventDefault()
        root?.focus()
        return true
    }

    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    const active = document.activeElement

    if (e.shiftKey && active === first) {
        e.preventDefault()
        last.focus()
    } else if (!e.shiftKey && active === last) {
        e.preventDefault()
        first.focus()
    }

    return true
}
