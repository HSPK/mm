import Foundation

/// Query parameters mirrored from the web `lib/filter-types.ts`. Only the
/// fields the iOS UI exposes are populated; the rest are nil/false so
/// `serialize()` drops them.
struct Filters: Equatable, Sendable {
    var type: MediaTypeFilter? = nil
    var tag: String? = nil
    var camera: String? = nil
    var dateFrom: Date? = nil
    var dateTo: Date? = nil
    var minRating: Int? = nil
    var favoritesOnly: Bool = false
    var search: String? = nil
    var sort: SortKey = .dateTaken
    var order: SortOrder = .descending
    var deleted: Bool = false

    enum MediaTypeFilter: String, CaseIterable, Identifiable, Sendable {
        case photo, video
        var id: String { rawValue }
        var label: String {
            switch self {
            case .photo: return "Photos"
            case .video: return "Videos"
            }
        }
    }

    enum SortKey: String, CaseIterable, Identifiable, Sendable {
        case dateTaken = "date_taken"
        case filename
        case rating
        case size
        var id: String { rawValue }
        var label: String {
            switch self {
            case .dateTaken: return "Date"
            case .filename: return "Name"
            case .rating: return "Rating"
            case .size: return "Size"
            }
        }
    }

    enum SortOrder: String, CaseIterable, Identifiable, Sendable {
        case ascending = "asc"
        case descending = "desc"
        var id: String { rawValue }
    }

    /// True if any non-default filter is active (i.e. would yield a tag chip).
    var hasActive: Bool {
        type != nil || tag != nil || camera != nil
            || dateFrom != nil || dateTo != nil
            || minRating != nil || favoritesOnly
            || (search?.isEmpty == false)
    }

    /// Encodes this filter set as `[String: String]` query parameters.
    func queryItems(page: Int, perPage: Int) -> [String: String] {
        var q: [String: String] = [
            "page": String(page),
            "per_page": String(perPage),
            "sort": sort.rawValue,
            "order": order.rawValue,
        ]
        if let t = type { q["type"] = t.rawValue }
        if let t = tag, !t.isEmpty { q["tag"] = t }
        if let c = camera, !c.isEmpty { q["camera"] = c }
        if let d = dateFrom { q["date_from"] = Self.iso8601Date(d) }
        if let d = dateTo { q["date_to"] = Self.iso8601Date(d) }
        if let r = minRating, r > 0 { q["min_rating"] = String(r) }
        if favoritesOnly { q["favorites_only"] = "true" }
        if let s = search, !s.isEmpty { q["search"] = s }
        if deleted { q["deleted"] = "true" }
        return q
    }

    private static let dateFormatter: DateFormatter = {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .iso8601)
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(secondsFromGMT: 0)
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()

    private static func iso8601Date(_ d: Date) -> String { dateFormatter.string(from: d) }
}
