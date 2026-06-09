import Foundation

/// Mirrors the brief media payload returned by `GET /api/media` (the
/// `serialize_media_brief` Python function).
struct Media: Identifiable, Codable, Hashable, Sendable {
    let id: Int
    let filename: String
    let extension_: String
    let mediaType: String
    let fileSize: Int
    let rating: Int
    let width: Int?
    let height: Int?
    let dateTaken: String?
    let cameraModel: String?
    let duration: Double?
    let gpsLat: Double?
    let gpsLon: Double?
    let locationLabel: String?
    let locationCity: String?
    let locationCountry: String?
    let deletedAt: String?

    enum CodingKeys: String, CodingKey {
        case id, filename, rating, width, height, duration
        case extension_ = "extension"
        case mediaType = "media_type"
        case fileSize = "file_size"
        case dateTaken = "date_taken"
        case cameraModel = "camera_model"
        case gpsLat = "gps_lat"
        case gpsLon = "gps_lon"
        case locationLabel = "location_label"
        case locationCity = "location_city"
        case locationCountry = "location_country"
        case deletedAt = "deleted_at"
    }

    var isVideo: Bool { mediaType == "video" }
}

struct PaginatedMedia: Decodable, Sendable {
    let items: [Media]
    let total: Int
    let page: Int
    let perPage: Int
    let pages: Int

    enum CodingKeys: String, CodingKey {
        case items, total, page, pages
        case perPage = "per_page"
    }
}
