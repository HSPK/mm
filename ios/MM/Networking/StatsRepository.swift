import Foundation

/// Maps to `/api/stats`, `/api/cameras`, `/api/timeline`, `/api/geo`.
@MainActor
struct StatsRepository {
    static let shared = StatsRepository()
    private let client = APIClient.shared

    func overview() async throws -> LibraryStats {
        try await client.get("/stats")
    }

    func listCameras() async throws -> [CameraStat] {
        try await client.get("/cameras")
    }

    func timeline() async throws -> [TimelineEntry] {
        try await client.get("/timeline")
    }

    func geo(limit: Int = 2000) async throws -> [GeoPoint] {
        try await client.get("/geo", query: ["limit": String(limit)])
    }
}
