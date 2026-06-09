import Foundation

struct CameraInfo: Decodable, Hashable, Sendable {
    let make: String
    let model: String
    let count: Int

    var displayName: String {
        let parts = [make, model].filter { !$0.isEmpty }
        return parts.joined(separator: " ")
    }
}

struct TagInfo: Decodable, Hashable, Sendable {
    let name: String
    let count: Int
}

/// Smart-album payload from `/api/smart-albums`. Each section's entries are
/// little manifests the server uses to navigate to a pre-filtered library.
struct SmartAlbum: Decodable, Identifiable, Hashable, Sendable {
    let key: String
    let title: String
    let subtitle: String?
    let count: Int?
    let coverId: Int?
    let icon: String?
    let color: String?
    let filters: SmartAlbumFilters
    let searchText: String?
    let festivalId: String?

    var id: String { key }

    enum CodingKeys: String, CodingKey {
        case key, title, subtitle, count, icon, color, filters
        case coverId = "cover_id"
        case searchText = "search_text"
        case festivalId = "festival_id"
    }
}

/// Loosely-typed filter blob — the server emits e.g. `{ "tag": "cat" }` or
/// `{ "date_from": "2024-01-01", "date_to": "2024-12-31" }`. We decode the
/// known keys into a struct of optionals; unknown ones are ignored.
struct SmartAlbumFilters: Decodable, Hashable, Sendable {
    let type: String?
    let tag: String?
    let camera: String?
    let dateFrom: String?
    let dateTo: String?
    let minRating: Int?

    enum CodingKeys: String, CodingKey {
        case type, tag, camera
        case dateFrom = "date_from"
        case dateTo = "date_to"
        case minRating = "min_rating"
    }

    /// Convert to the iOS Filters type used by MediaQueryStore. Keeps `sort`
    /// at the default (date_taken desc).
    func toFilters() -> Filters {
        var f = Filters()
        if let t = type, let kind = Filters.MediaTypeFilter(rawValue: t) {
            f.type = kind
        }
        f.tag = tag
        f.camera = camera
        f.dateFrom = dateFrom.flatMap(Self.parseDate)
        f.dateTo = dateTo.flatMap(Self.parseDate)
        f.minRating = minRating
        return f
    }

    private static let dateFormatter: DateFormatter = {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .iso8601)
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(secondsFromGMT: 0)
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()

    private static func parseDate(_ s: String) -> Date? { dateFormatter.date(from: s) }
}

struct SmartAlbumsResponse: Decodable, Sendable {
    let library: [SmartAlbum]
    let tags: [SmartAlbum]
    let cameras: [SmartAlbum]
    let festivals: [SmartAlbum]
    let years: [SmartAlbum]
    let places: [SmartAlbum]
}
