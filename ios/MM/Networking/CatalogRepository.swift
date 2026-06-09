import Foundation

/// Maps to the web `api/catalog.ts` repository.
@MainActor
struct CatalogRepository {
    static let shared = CatalogRepository()
    private let client = APIClient.shared

    func listCameras() async throws -> [CameraInfo] {
        try await client.get("/cameras")
    }

    func listSmartAlbums() async throws -> SmartAlbumsResponse {
        try await client.get("/smart-albums")
    }
}
