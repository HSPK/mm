import Foundation

struct User: Codable, Sendable, Equatable {
    let id: Int
    let username: String
    let displayName: String
    let isAdmin: Bool

    enum CodingKeys: String, CodingKey {
        case id, username
        case displayName = "display_name"
        case isAdmin = "is_admin"
    }

    var initial: String {
        let name = displayName.isEmpty ? username : displayName
        return name.first.map { String($0).uppercased() } ?? "?"
    }
}

struct LoginRequest: Encodable, Sendable {
    let username: String
    let password: String
}

struct LoginResponse: Decodable, Sendable {
    let token: String
    let user: User
}
