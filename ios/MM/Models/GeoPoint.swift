import Foundation

/// Compact GPS-tagged media row from `GET /api/geo` — used by MapView so it
/// can render thousands of pins from one fast request instead of paginating.
struct GeoPoint: Decodable, Identifiable, Hashable, Sendable {
    let id: Int
    let filename: String
    let mediaType: String
    let lat: Double
    let lon: Double
    let date: String?
    let city: String?

    enum CodingKeys: String, CodingKey {
        case id, filename, lat, lon, date, city
        case mediaType = "media_type"
    }
}
