import { render } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { Skeleton } from "./skeleton"
import { Spinner } from "./spinner"

describe("Spinner", () => {
    it("uses status role and an aria-label by default", () => {
        const { getByRole } = render(<Spinner />)
        const el = getByRole("status")
        expect(el.getAttribute("aria-label")).toBe("Loading")
    })

    it("applies size class", () => {
        const { getByRole } = render(<Spinner size="lg" />)
        expect(getByRole("status").classList.contains("h-7")).toBe(true)
    })

    it("respects custom label", () => {
        const { getByRole } = render(<Spinner label="Fetching media" />)
        expect(getByRole("status").getAttribute("aria-label")).toBe("Fetching media")
    })
})

describe("Skeleton", () => {
    it("renders a hidden block by default", () => {
        const { container } = render(<Skeleton className="h-10 w-20" />)
        const el = container.firstElementChild
        expect(el?.getAttribute("aria-hidden")).toBe("true")
        expect(el?.className).toContain("h-10")
        expect(el?.className).toContain("w-20")
    })
})
