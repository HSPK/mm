import Foundation

/// Per-camera count from `GET /api/stats/cameras` (and inside `LibraryStats`).
struct CameraStat: Decodable, Hashable, Sendable, Identifiable {
    let make: String
    let model: String
    let count: Int

    var id: String { "\(make)|\(model)" }

    var displayName: String {
        let parts = [make, model].filter { !$0.isEmpty }
        let combined = parts.joined(separator: " ")
        return combined.isEmpty ? "Unknown" : combined
    }
}

struct TagStat: Decodable, Hashable, Sendable {
    let id: Int
    let name: String
    let count: Int
}

struct TypeDistribution: Decodable, Hashable, Sendable {
    let photo: Int
    let video: Int
    let audio: Int
}

struct LibraryStats: Decodable, Sendable {
    let totalFiles: Int
    let totalSize: Int
    let typeDistribution: TypeDistribution
    let tags: [TagStat]
    let cameras: [CameraStat]

    enum CodingKeys: String, CodingKey {
        case tags, cameras
        case totalFiles = "total_files"
        case totalSize = "total_size"
        case typeDistribution = "type_distribution"
    }
}

/// One bucket in `GET /api/timeline` (year-month or year).
struct TimelineEntry: Decodable, Hashable, Sendable {
    let period: String
    let count: Int
}
