import Foundation

/// App-wide configuration. The API base URL is overridable via:
///   1. `MM_API_BASE_URL` environment variable (set in Xcode scheme)
///   2. User-edited value persisted to UserDefaults (`mm.apiBaseURL`)
///   3. Fallback to `http://localhost:8000/api`
enum AppConfig {
    static let defaultAPIBase = URL(string: "http://localhost:8000/api")!

    private static let userDefaultsKey = "mm.apiBaseURL"

    /// Reads the API base URL from env → defaults → fallback.
    static var apiBaseURL: URL {
        if let env = ProcessInfo.processInfo.environment["MM_API_BASE_URL"],
           let url = URL(string: env) {
            return url
        }
        if let stored = UserDefaults.standard.string(forKey: userDefaultsKey),
           let url = URL(string: stored) {
            return url
        }
        return defaultAPIBase
    }

    static func setAPIBaseURL(_ url: URL) {
        UserDefaults.standard.set(url.absoluteString, forKey: userDefaultsKey)
    }
}
