#if os(macOS)
import AppKit

actor MacImagePipeline {
    static let shared = MacImagePipeline()

    private let cache: NSCache<NSURL, NSImage> = {
        let cache = NSCache<NSURL, NSImage>()
        cache.totalCostLimit = 120 * 1024 * 1024
        return cache
    }()

    private let session: URLSession = {
        let cfg = URLSessionConfiguration.default
        cfg.urlCache = URLCache(
            memoryCapacity: 48 * 1024 * 1024,
            diskCapacity: 1024 * 1024 * 1024,
            diskPath: "mm-native-image-cache",
        )
        cfg.requestCachePolicy = .useProtocolCachePolicy
        cfg.httpMaximumConnectionsPerHost = 6
        return URLSession(configuration: cfg)
    }()

    private var inflight: [URL: Task<NSImage?, Error>] = [:]

    func cachedImage(for url: URL) -> NSImage? {
        cache.object(forKey: url as NSURL)
    }

    func image(for url: URL) async throws -> NSImage? {
        if let hit = cache.object(forKey: url as NSURL) {
            return hit
        }
        if let task = inflight[url] {
            let image = try await task.value
            if let image, cache.object(forKey: url as NSURL) == nil {
                cache.setObject(image, forKey: url as NSURL, cost: max(1, dataCost(for: image)))
            }
            return image
        }

        let task = fetchTask(for: url, priority: .utility)
        inflight[url] = task

        do {
            let image = try await task.value
            if let image {
                cache.setObject(image, forKey: url as NSURL, cost: max(1, dataCost(for: image)))
            }
            inflight[url] = nil
            return image
        } catch {
            inflight[url] = nil
            throw error
        }
    }

    func prefetch(_ urls: [URL]) {
        for url in urls where cache.object(forKey: url as NSURL) == nil && inflight[url] == nil {
            let task = fetchTask(for: url, priority: .background)
            inflight[url] = task
            Task {
                do {
                    let image = try await task.value
                    await completePrefetch(url: url, image: image)
                } catch {
                    await clearInflight(url: url)
                }
            }
        }
    }

    private func fetchTask(for url: URL, priority: TaskPriority) -> Task<NSImage?, Error> {
        let session = session
        return Task.detached(priority: priority) {
            var request = URLRequest(url: url)
            if let token = TokenStore.read() {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                return nil
            }
            return NSImage(data: data)
        }
    }

    private func completePrefetch(url: URL, image: NSImage?) {
        if let image {
            cache.setObject(image, forKey: url as NSURL, cost: max(1, dataCost(for: image)))
        }
        inflight[url] = nil
    }

    private func clearInflight(url: URL) {
        inflight[url] = nil
    }

    private func dataCost(for image: NSImage) -> Int {
        let width = max(1, Int(image.size.width))
        let height = max(1, Int(image.size.height))
        return width * height * 4
    }
}
#endif
