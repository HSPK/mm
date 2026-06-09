import Foundation

/// Errors surfaced from the API client.
enum APIError: LocalizedError {
    case http(status: Int, body: String?)
    case decoding(Error)
    case transport(Error)
    case unauthorized

    var errorDescription: String? {
        switch self {
        case .unauthorized: return "Not signed in"
        case .http(let status, let body):
            if let body, !body.isEmpty { return "HTTP \(status): \(body)" }
            return "HTTP \(status)"
        case .decoding(let err): return "Response decoding failed: \(err.localizedDescription)"
        case .transport(let err): return err.localizedDescription
        }
    }
}

/// A lightweight URLSession-based HTTP client. Adds Bearer auth + a single
/// retry-on-401 hook so a stale token surfaces a fresh login attempt.
@MainActor
final class APIClient {
    static let shared = APIClient()

    /// Invoked when the server responds 401. Default implementation clears the
    /// token; the AuthStore replaces this to also flip the signed-in flag.
    var onUnauthorized: @Sendable () -> Void = { TokenStore.clear() }

    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        // Server emits ISO8601 strings; let callers `Date`-decode case-by-case
        // since some fields are nullable strings, not Dates.
        d.keyDecodingStrategy = .useDefaultKeys
        return d
    }()

    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .useDefaultKeys
        return e
    }()

    nonisolated private let session: URLSession

    private init() {
        let cfg = URLSessionConfiguration.default
        cfg.requestCachePolicy = .reloadIgnoringLocalCacheData
        cfg.httpAdditionalHeaders = ["Accept": "application/json"]
        self.session = URLSession(configuration: cfg)
    }

    // MARK: - High-level

    func get<T: Decodable>(_ path: String, query: [String: String] = [:]) async throws -> T {
        try await request(path: path, method: "GET", query: query, body: nil)
    }

    func post<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        try await request(path: path, method: "POST", query: [:], body: try encoder.encode(body))
    }

    func put<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        try await request(path: path, method: "PUT", query: [:], body: try encoder.encode(body))
    }

    func patch<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        try await request(path: path, method: "PATCH", query: [:], body: try encoder.encode(body))
    }

    func delete(_ path: String, query: [String: String] = [:]) async throws {
        let _: EmptyResponse = try await request(path: path, method: "DELETE", query: query, body: nil)
    }

    func data(_ path: String) async throws -> Data {
        let url = buildURL(path: path, query: [:])
        let (data, response) = try await dispatch(URLRequest(url: url))
        try ensureSuccess(response: response, data: data)
        return data
    }

    /// Returns an absolute URL for a server path (e.g. `/media/1/file`). Used
    /// by AuthAsyncImage and Share to point at the server's raw file endpoint.
    func absoluteURL(forPath path: String) -> URL {
        URL(string: path, relativeTo: AppConfig.apiBaseURL)?.absoluteURL
            ?? AppConfig.apiBaseURL.appendingPathComponent(path)
    }

    // MARK: - Core

    private func request<T: Decodable>(
        path: String,
        method: String,
        query: [String: String],
        body: Data?,
    ) async throws -> T {
        let url = buildURL(path: path, query: query)
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.httpBody = body
        if body != nil {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let (data, response) = try await dispatch(req)
        try ensureSuccess(response: response, data: data)

        if T.self == EmptyResponse.self { return EmptyResponse() as! T }

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    private func dispatch(_ original: URLRequest) async throws -> (Data, URLResponse) {
        var req = original
        if let token = TokenStore.read() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        do {
            return try await session.data(for: req)
        } catch {
            throw APIError.transport(error)
        }
    }

    private func ensureSuccess(response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else {
            throw APIError.http(status: 0, body: nil)
        }
        if http.statusCode == 401 {
            onUnauthorized()
            throw APIError.unauthorized
        }
        if !(200..<300).contains(http.statusCode) {
            let body = String(data: data, encoding: .utf8)
            throw APIError.http(status: http.statusCode, body: body)
        }
    }

    private func buildURL(path: String, query: [String: String]) -> URL {
        var base = AppConfig.apiBaseURL
        if !path.isEmpty {
            let trimmed = path.hasPrefix("/") ? String(path.dropFirst()) : path
            base = base.appendingPathComponent(trimmed)
        }
        guard !query.isEmpty,
              var components = URLComponents(url: base, resolvingAgainstBaseURL: false) else {
            return base
        }
        components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        return components.url ?? base
    }
}

struct EmptyResponse: Decodable {}
