import { describe, expect, it } from "vitest"
import { previewImportTemplate } from "./use-import-template"

describe("previewImportTemplate", () => {
    it("substitutes all known variables", () => {
        const out = previewImportTemplate("{year}/{month:02d}-{day:02d}/{original_name}{ext}")
        expect(out).toBe("2024/03-15/DSC_0001.jpg")
    })

    it("leaves unknown tokens alone", () => {
        expect(previewImportTemplate("{foo}/{year}")).toBe("{foo}/2024")
    })

    it("handles empty template", () => {
        expect(previewImportTemplate("")).toBe("")
    })

    it("substitutes camera + type tokens", () => {
        expect(previewImportTemplate("{type}/{camera}")).toBe("photo/Sony A7IV")
    })
})
