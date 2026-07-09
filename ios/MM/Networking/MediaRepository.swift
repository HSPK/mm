import Foundation

/// Maps to the web `api/media.ts` repository.
@MainActor
struct MediaRepository {
    static let shared = MediaRepository()
    private let client = APIClient.shared

    func list(page: Int, perPage: Int = 60, filters: Filters = Filters(), extraQuery: [String: String] = [:]) async throws -> PaginatedMedia {
        var q = filters.queryItems(page: page, perPage: perPage)
        for (k, v) in extraQuery { q[k] = v }
        return try await client.get("/media", query: q)
    }

    func get(id: Int) async throws -> MediaDetail {
        try await client.get("/media/\(id)")
    }

    func setRating(id: Int, rating: Int) async throws -> RatingResponse {
        try await client.put("/media/\(id)/rating", body: ["rating": rating])
    }

    func updateMetadata(id: Int, patch: MetadataPatch) async throws -> MediaDetail {
        try await client.patch("/media/\(id)/metadata", body: patch)
    }

    func addTags(id: Int, tags: [String]) async throws {
        struct Body: Encodable { let tags: [String] }
        let _: EmptyResponse = try await client.post("/media/\(id)/tags", body: Body(tags: tags))
    }

    func removeTag(id: Int, name: String) async throws {
        let encoded = name.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? name
        try await client.delete("/media/\(id)/tags/\(encoded)")
    }

    func delete(id: Int, permanent: Bool = false) async throws {
        try await client.delete(
            "/media/\(id)",
            query: permanent ? ["permanent": "true"] : [:],
        )
    }

    func restore(id: Int) async throws {
        let _: EmptyResponse = try await client.post("/media/\(id)/restore", body: EmptyBody())
    }

    func batchDelete(ids: [Int]) async throws -> BatchAffectedResponse {
        struct Body: Encodable { let media_ids: [Int] }
        return try await client.post("/batch/delete", body: Body(media_ids: ids))
    }

    func batchDeletePermanently(ids: [Int]) async throws -> BatchAffectedResponse {
        struct Body: Encodable { let media_ids: [Int] }
        return try await client.post("/batch/delete/permanent", body: Body(media_ids: ids))
    }

    func batchRestore(ids: [Int]) async throws -> BatchAffectedResponse {
        struct Body: Encodable { let media_ids: [Int] }
        return try await client.post("/batch/restore", body: Body(media_ids: ids))
    }

    func batchSetRating(ids: [Int], rating: Int) async throws -> BatchAffectedResponse {
        struct Body: Encodable { let media_ids: [Int]; let rating: Int }
        return try await client.post("/batch/rating", body: Body(media_ids: ids, rating: rating))
    }

    func batchAddTags(ids: [Int], tags: [String]) async throws -> BatchAffectedResponse {
        struct Body: Encodable { let media_ids: [Int]; let tags: [String] }
        return try await client.post("/batch/tags", body: Body(media_ids: ids, tags: tags))
    }

    func batchRemoveTags(ids: [Int], tags: [String]) async throws -> BatchAffectedResponse {
        struct Body: Encodable { let media_ids: [Int]; let tags: [String] }
        return try await client.post("/batch/tags/remove", body: Body(media_ids: ids, tags: tags))
    }

    func listTrash() async throws -> [Media] {
        try await client.get("/media/trash")
    }

    func emptyTrash() async throws {
        try await client.delete("/media/trash")
    }

    func downloadFile(for item: Media) async throws -> URL {
        try await client.download("/media/\(item.id)/file", suggestedFilename: item.filename)
    }

    // MARK: - URL helpers

    func fileURL(for id: Int) -> URL {
        client.absoluteURL(forPath: "media/\(id)/file", includeToken: true)
    }

    func previewURL(for id: Int) -> URL {
        client.absoluteURL(forPath: "media/\(id)/preview")
    }

    func thumbnailURL(for id: Int, size: String = "md") -> URL {
        client.absoluteURL(
            forPath: "media/\(id)/thumbnail",
            query: ["size": size],
        )
    }
}

struct RatingResponse: Decodable, Sendable {
    let rating: Int
}

struct BatchAffectedResponse: Decodable, Sendable {
    let affected: Int
}

private struct EmptyBody: Encodable {}
