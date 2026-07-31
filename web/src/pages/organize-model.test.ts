import { describe, expect, it } from "vitest"
import type { OrganizerItem } from "@/api/organizer"
import {
    buildRows,
    filterAndSortRows,
    metadataPatchRequests,
    type MediaRow,
} from "./organize-model"
import { visibleRangeKeys } from "./organize-selection"

function item(overrides: Partial<OrganizerItem>): OrganizerItem {
    return {
        path: "/media/unknown.mkv",
        media_type: "tv",
        title: "Untitled",
        confidence: 0,
        is_new: false,
        metadata: false,
        images: false,
        subtitles: false,
        lyrics: false,
        ...overrides,
    }
}

describe("organizer row identity and selection", () => {
    it("keeps identically titled TV series in different source roots separate", () => {
        const rows = buildRows([
            item({ item_uid: "a", title: "The Office", path: "/media/us/The Office/Season 01/one.mkv", year: 2005 }),
            item({ item_uid: "b", title: "The Office", path: "/media/uk/The Office/Season 01/one.mkv", year: 2001 }),
        ], [], {}, "tv", [])

        expect(rows).toHaveLength(2)
        expect(new Set(rows.map((row) => row.key)).size).toBe(2)
    })

    it("groups the complete catalog before filtering TV series", () => {
        const rows = buildRows([
            item({
                item_uid: "episode-1",
                title: "Pilot",
                metadata_show_title: "Example Show",
                path: "/media/Example Show/Season 01/episode-1.mkv",
            }),
            item({
                item_uid: "episode-2",
                title: "Finale",
                metadata_show_title: "Example Show",
                path: "/media/Example Show/Season 01/episode-2.mkv",
            }),
        ], [], {}, "tv", [])

        const filtered = filterAndSortRows(rows, "finale", "name")

        expect(filtered).toHaveLength(1)
        expect(filtered[0].title).toBe("Example Show")
        expect(filtered[0].files).toHaveLength(2)
    })

    it("shift selects rows in the displayed table", () => {
        const rows = ["one", "two", "three", "four", "five"].map((key) => ({ key }))
        expect(visibleRangeKeys(
            rows as unknown as MediaRow[],
            "two",
            "four",
        )).toEqual(["two", "three", "four"])
    })

    it("maps every editable metadata field into the projection patch", () => {
        const row = buildRows([
            item({
                item_uid: "movie-1",
                revision: 4,
                media_type: "movie",
                path: "/media/movie.mkv",
                title: "Movie",
            }),
        ], [], {}, "movies", [])[0]

        expect(metadataPatchRequests(row, {
            title: "New title",
            originalTitle: "Original",
            year: 2024,
            rating: 8.5,
            premiered: "2024-01-01",
            certification: "PG",
            runtime: 120,
            genres: "Drama, Mystery",
            status: "Released",
            studios: "Studio A",
            countries: "US",
            tagline: "Tagline",
            plot: "Plot",
            tags: "tag1,tag2",
            cast: "Actor A, Actor B",
            writeNfo: true,
        })[0]).toMatchObject({
            item_uid: "movie-1",
            revision: 4,
            metadata_original_title: "Original",
            metadata_premiered: "2024-01-01",
            metadata_certification: "PG",
            metadata_runtime: 120,
            metadata_genres: ["Drama", "Mystery"],
            metadata_status: "Released",
            metadata_studios: ["Studio A"],
            metadata_countries: ["US"],
            metadata_tagline: "Tagline",
            metadata_plot: "Plot",
            metadata_tags: ["tag1", "tag2"],
            metadata_cast: ["Actor A", "Actor B"],
            metadata_rating: 8.5,
            write_nfo: true,
        })
    })
})
