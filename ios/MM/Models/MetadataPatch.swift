import Foundation

/// Partial-update body for `PATCH /api/media/{id}/metadata`. Mirrors the
/// server `UpdateMetadataBody`. All fields are optional; only non-nil fields
/// are serialized so users can clear values explicitly via `NSNull`-style
/// sentinels (not needed in practice — to clear, send empty string for text
/// or 0 for numerics where the server already treats those as "unset").
struct MetadataPatch: Encodable, Sendable {
    var dateTaken: Date?
    var gpsLat: Double?
    var gpsLon: Double?
    var locationLabel: String?
    var locationCity: String?
    var locationCountry: String?
    var cameraMake: String?
    var cameraModel: String?
    var lensModel: String?
    var aperture: Double?
    var shutterSpeed: String?
    var iso: Int?
    var focalLength: Double?

    enum CodingKeys: String, CodingKey {
        case aperture, iso
        case dateTaken = "date_taken"
        case gpsLat = "gps_lat"
        case gpsLon = "gps_lon"
        case locationLabel = "location_label"
        case locationCity = "location_city"
        case locationCountry = "location_country"
        case cameraMake = "camera_make"
        case cameraModel = "camera_model"
        case lensModel = "lens_model"
        case shutterSpeed = "shutter_speed"
        case focalLength = "focal_length"
    }

    private static let isoFormatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        if let d = dateTaken {
            try c.encode(Self.isoFormatter.string(from: d), forKey: .dateTaken)
        }
        try c.encodeIfPresent(gpsLat, forKey: .gpsLat)
        try c.encodeIfPresent(gpsLon, forKey: .gpsLon)
        try c.encodeIfPresent(locationLabel, forKey: .locationLabel)
        try c.encodeIfPresent(locationCity, forKey: .locationCity)
        try c.encodeIfPresent(locationCountry, forKey: .locationCountry)
        try c.encodeIfPresent(cameraMake, forKey: .cameraMake)
        try c.encodeIfPresent(cameraModel, forKey: .cameraModel)
        try c.encodeIfPresent(lensModel, forKey: .lensModel)
        try c.encodeIfPresent(aperture, forKey: .aperture)
        try c.encodeIfPresent(shutterSpeed, forKey: .shutterSpeed)
        try c.encodeIfPresent(iso, forKey: .iso)
        try c.encodeIfPresent(focalLength, forKey: .focalLength)
    }

    var isEmpty: Bool {
        dateTaken == nil && gpsLat == nil && gpsLon == nil
            && locationLabel == nil && locationCity == nil && locationCountry == nil
            && cameraMake == nil && cameraModel == nil && lensModel == nil
            && aperture == nil && shutterSpeed == nil && iso == nil && focalLength == nil
    }
}
