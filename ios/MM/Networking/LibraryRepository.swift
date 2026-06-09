import Foundation

struct LibraryInfo: Decodable, Identifiable, Hashable, Sendable {
    let dbPath: String
    let name: String

    var id: String { dbPath }

    enum CodingKeys: String, CodingKey {
        case name
        case dbPath = "db_path"
    }
}

struct LibrarySwitchResponse: Decodable, Sendable {
    let dbPath: String
    let name: String
    let message: String

    enum CodingKeys: String, CodingKey {
        case name, message
        case dbPath = "db_path"
    }
}

/// Maps to the web `api/library.ts` repository.
@MainActor
struct LibraryRepository {
    static let shared = LibraryRepository()
    private let client = APIClient.shared

    func current() async throws -> LibraryInfo {
        try await client.get("/library")
    }

    func recent() async throws -> [LibraryInfo] {
        try await client.get("/library/recent")
    }

    func switchTo(dbPath: String) async throws -> LibrarySwitchResponse {
        struct Body: Encodable { let db_path: String }
        return try await client.post("/library/switch", body: Body(db_path: dbPath))
    }
}
