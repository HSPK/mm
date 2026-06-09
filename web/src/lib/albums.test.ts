import { describe, expect, it, vi } from "vitest"
import type { SmartAlbumsResponse } from "@/api/types"
import { bindAlbumItem, buildAlbumItems, getAlbumSections, registerAlbumSection } from "./albums"

const empty: SmartAlbumsResponse = {
    library: [],
    tags: [],
    cameras: [],
    festivals: [],
    years: [],
    places: [],
}

describe("bindAlbumItem", () => {
    it("wires onClick to call openAlbum with the album's filters + title", () => {
        const openAlbum = vi.fn()
        const item = bindAlbumItem(
            {
                key: "tag:cat",
                title: "Cat",
                subtitle: "",
                color: "",
                filters: { tag: "cat" },
                search_text: "Cat photos",
                icon: "tag",
            },
            openAlbum,
        )
        item.onClick()
        expect(openAlbum).toHaveBeenCalledWith({ tag: "cat" }, "Cat")
        expect(item.searchText).toBe("Cat photos")
    })

    it("defaults searchText to title when search_text missing", () => {
        const item = bindAlbumItem(
            { key: "k", title: "Title", subtitle: "", color: "", filters: {} },
            vi.fn(),
        )
        expect(item.searchText).toBe("Title")
    })
})

describe("buildAlbumItems", () => {
    it("returns empty arrays for null data", () => {
        const { libraryItems, sections } = buildAlbumItems(null, vi.fn())
        expect(libraryItems).toEqual([])
        expect(sections).toEqual([])
    })

    it("drops sections that have no items", () => {
        const data: SmartAlbumsResponse = {
            ...empty,
            tags: [{ key: "tag:cat", title: "Cat", subtitle: "", color: "", filters: {} }],
        }
        const { sections } = buildAlbumItems(data, vi.fn())
        expect(sections.map((s) => s.id)).toEqual(["tags"])
    })
})

describe("section registry", () => {
    it("exposes built-in sections in stable order", () => {
        expect(getAlbumSections().map((s) => s.id)).toEqual([
            "tags",
            "cameras",
            "festivals",
            "years",
            "places",
        ])
    })

    it("supports overriding a section without replacing the list", () => {
        const before = getAlbumSections().length
        registerAlbumSection({
            id: "tags",
            key: "tags",
            icon: getAlbumSections()[0].icon,
            title: "Hashtags",
            previewCount: 12,
        })
        expect(getAlbumSections()).toHaveLength(before)
        expect(getAlbumSections().find((s) => s.id === "tags")?.title).toBe("Hashtags")
        // restore
        registerAlbumSection({
            id: "tags",
            key: "tags",
            icon: getAlbumSections()[0].icon,
            title: "Tags",
            previewCount: 8,
        })
    })
})
