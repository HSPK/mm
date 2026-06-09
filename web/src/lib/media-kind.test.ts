import { describe, expect, it } from "vitest"
import {
    canDisplayOriginalImage,
    isRawBadgeExtension,
    isRawExtension,
} from "./media-kind"

describe("isRawExtension", () => {
    it("matches known raw extensions case-insensitively", () => {
        expect(isRawExtension(".CR2")).toBe(true)
        expect(isRawExtension(".dng")).toBe(true)
        expect(isRawExtension(".heic")).toBe(true)
    })

    it("rejects native image extensions", () => {
        expect(isRawExtension(".jpg")).toBe(false)
        expect(isRawExtension(".png")).toBe(false)
    })
})

describe("isRawBadgeExtension", () => {
    it("accepts upper-case raw codes", () => {
        expect(isRawBadgeExtension("CR2")).toBe(true)
        expect(isRawBadgeExtension("cr2")).toBe(true)
    })

    it("rejects unknown codes", () => {
        expect(isRawBadgeExtension("JPG")).toBe(false)
    })
})

describe("canDisplayOriginalImage", () => {
    it("accepts browser-renderable formats", () => {
        expect(canDisplayOriginalImage({ extension: ".jpg" })).toBe(true)
        expect(canDisplayOriginalImage({ extension: ".WEBP" })).toBe(true)
    })

    it("rejects raw and unknown formats", () => {
        expect(canDisplayOriginalImage({ extension: ".cr2" })).toBe(false)
        expect(canDisplayOriginalImage({ extension: ".xyz" })).toBe(false)
    })
})
