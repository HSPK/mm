import "@testing-library/jest-dom/vitest"
import { afterEach } from "vitest"
import { cleanup } from "@testing-library/react"

afterEach(() => {
    cleanup()
    localStorage.clear()
    sessionStorage.clear()
    document.cookie.split(";").forEach((c) => {
        const name = c.split("=")[0].trim()
        if (name) {
            document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`
        }
    })
})
