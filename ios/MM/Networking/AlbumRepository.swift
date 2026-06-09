import Foundation

struct AlbumSummary: Identifiable, Decodable, Hashable, Sendable {
    let id: Int
    let name: String
}

/// Maps to the web `api/albums.ts` repository.
@MainActor
struct AlbumRepository {
    static let shared = AlbumRepository()
    private let client = APIClient.shared

    func list() async throws -> [AlbumSummary] {
        try await client.get("/albums")
    }

    func create(name: String) async throws -> CreatedAlbum {
        struct Body: Encodable { let name: String }
        return try await client.post("/albums", body: Body(name: name))
    }

    func addMedia(albumId: Int, mediaIds: [Int]) async throws {
        struct Body: Encodable { let media_ids: [Int] }
        let _: EmptyResponse = try await client.post("/albums/\(albumId)/media", body: Body(media_ids: mediaIds))
    }
}

struct CreatedAlbum: Decodable, Sendable {
    let id: Int
}
