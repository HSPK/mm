import Foundation

/// User-facing toggle for grouping the LibraryView grid by date.
enum DateGroupMode: String, CaseIterable, Identifiable, Sendable {
    case none
    case month
    case day

    var id: String { rawValue }

    var label: String {
        switch self {
        case .none: return "No grouping"
        case .month: return "By month"
        case .day: return "By day"
        }
    }

    var systemImage: String {
        switch self {
        case .none: return "square.grid.2x2"
        case .month: return "calendar"
        case .day: return "calendar.day.timeline.left"
        }
    }
}

/// One group of media items + a stable header label.
struct MediaDateGroup: Identifiable {
    let id: String
    let title: String
    let items: [Media]
}

enum MediaGrouper {
    private static let isoDate: DateFormatter = {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .iso8601)
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone.current
        return f
    }()

    private static let isoDateTime: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    private static let monthHeader: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "MMMM yyyy"
        return f
    }()

    private static let dayHeader: DateFormatter = {
        let f = DateFormatter()
        f.dateStyle = .full
        f.timeStyle = .none
        return f
    }()

    /// Parses an ISO8601 string from the server (handles seconds and
    /// fractional seconds).
    static func parseDate(_ s: String) -> Date? {
        if let d = isoDateTime.date(from: s) { return d }
        let f = ISO8601DateFormatter()
        if let d = f.date(from: s) { return d }
        isoDate.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        if let d = isoDate.date(from: s) { return d }
        isoDate.dateFormat = "yyyy-MM-dd"
        return isoDate.date(from: s)
    }

    static func group(_ items: [Media], mode: DateGroupMode) -> [MediaDateGroup] {
        switch mode {
        case .none:
            return [MediaDateGroup(id: "all", title: "", items: items)]
        case .month, .day:
            var keyTitles: [(key: String, title: String)] = []
            var bucket: [String: [Media]] = [:]
            for item in items {
                let (key, title) = bucketKey(for: item, mode: mode)
                if bucket[key] == nil {
                    bucket[key] = []
                    keyTitles.append((key, title))
                }
                bucket[key]?.append(item)
            }
            return keyTitles.map { MediaDateGroup(id: $0.key, title: $0.title, items: bucket[$0.key] ?? []) }
        }
    }

    private static func bucketKey(for item: Media, mode: DateGroupMode) -> (String, String) {
        let date = item.dateTaken.flatMap(parseDate)
        guard let d = date else { return ("unknown", "Unknown date") }
        let cal = Calendar.current
        switch mode {
        case .month:
            let comps = cal.dateComponents([.year, .month], from: d)
            let key = String(format: "%04d-%02d", comps.year ?? 0, comps.month ?? 0)
            return (key, monthHeader.string(from: d))
        case .day:
            let comps = cal.dateComponents([.year, .month, .day], from: d)
            let key = String(format: "%04d-%02d-%02d", comps.year ?? 0, comps.month ?? 0, comps.day ?? 0)
            return (key, dayHeader.string(from: d))
        case .none:
            return ("all", "")
        }
    }
}
