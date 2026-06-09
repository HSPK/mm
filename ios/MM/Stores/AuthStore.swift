import Foundation
import Observation

/// Source of truth for "is the user signed in?". Wires up the APIClient's
/// onUnauthorized callback so a stale token surfaces immediately.
@MainActor
@Observable
final class AuthStore {
    private(set) var user: User?
    private(set) var isAuthenticated: Bool = TokenStore.read() != nil
    private(set) var loading: Bool = false
    private(set) var error: String?

    private let repo = AuthRepository.shared

    init() {
        APIClient.shared.onUnauthorized = { [weak self] in
            Task { @MainActor in
                self?.signOutLocally()
            }
        }
        if isAuthenticated {
            Task { await refreshUser() }
        }
    }

    func signIn(username: String, password: String) async -> Bool {
        loading = true
        error = nil
        defer { loading = false }
        do {
            let res = try await repo.login(username: username, password: password)
            TokenStore.write(res.token)
            user = res.user
            isAuthenticated = true
            return true
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    func refreshUser() async {
        guard isAuthenticated else { return }
        do {
            user = try await repo.me()
        } catch {
            signOutLocally()
        }
    }

    func signOut() {
        signOutLocally()
    }

    private func signOutLocally() {
        TokenStore.clear()
        user = nil
        isAuthenticated = false
    }
}
