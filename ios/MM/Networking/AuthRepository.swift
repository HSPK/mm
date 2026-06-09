import Foundation

/// Maps to the web `api/auth.ts` repository.
@MainActor
struct AuthRepository {
    static let shared = AuthRepository()
    private let client = APIClient.shared

    func login(username: String, password: String) async throws -> LoginResponse {
        try await client.post(
            "/auth/login",
            body: LoginRequest(username: username, password: password),
        )
    }

    func me() async throws -> User {
        try await client.get("/auth/me")
    }
}
