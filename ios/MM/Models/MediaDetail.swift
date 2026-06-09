import Foundation

/// Detail payload from `GET /api/media/{id}` (`serialize_media`).
struct MediaDetail: Decodable, Sendable {
    let id: Int
    let path: String
    let filename: String
    let extension_: String
    let mediaType: String
    let fileSize: Int
    let fileHash: String
    let rating: Int
    let scannedAt: String?
    let metadata: MediaMetadata?
    let tags: [MediaTag]

    enum CodingKeys: String, CodingKey {
        case id, path, filename, rating, metadata, tags
        case extension_ = "extension"
        case mediaType = "media_type"
        case fileSize = "file_size"
        case fileHash = "file_hash"
        case scannedAt = "scanned_at"
    }
}

struct MediaMetadata: Decodable, Sendable {
    let dateTaken: String?
    let cameraMake: String?
    let cameraModel: String?
    let lensModel: String?
    let focalLength: Double?
    let aperture: Double?
    let shutterSpeed: String?
    let iso: Int?
    let width: Int?
    let height: Int?
    let duration: Double?
    let gpsLat: Double?
    let gpsLon: Double?
    let orientation: Int?
    let locationLabel: String?
    let locationCountry: String?
    let locationCity: String?

    enum CodingKeys: String, CodingKey {
        case aperture, iso, width, height, duration, orientation
        case dateTaken = "date_taken"
        case cameraMake = "camera_make"
        case cameraModel = "camera_model"
        case lensModel = "lens_model"
        case focalLength = "focal_length"
        case shutterSpeed = "shutter_speed"
        case gpsLat = "gps_lat"
        case gpsLon = "gps_lon"
        case locationLabel = "location_label"
        case locationCountry = "location_country"
        case locationCity = "location_city"
    }
}

struct MediaTag: Decodable, Hashable, Sendable {
    let name: String
    let source: String
    let confidence: Double?
}
