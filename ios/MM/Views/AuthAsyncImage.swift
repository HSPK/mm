import SwiftUI

#if os(macOS)
import AppKit
typealias PlatformImage = NSImage
#else
import UIKit
typealias PlatformImage = UIImage
#endif

/// Disk-backed URLCache + tuned URLSession for image traffic only. Honors
/// the server's `Cache-Control` and `ETag` headers (set by `_serve_thumb`),
/// so revisited thumbnails are served from disk without re-downloading and
/// changed thumbnails get a conditional 304 round-trip.
enum ImageNetworking {
    static let session: URLSession = {
        let cache = URLCache(
            memoryCapacity: 32 * 1024 * 1024,   // 32 MB RAM
            diskCapacity: 512 * 1024 * 1024,    // 512 MB disk
            diskPath: "mm-image-cache",
        )
        let cfg = URLSessionConfiguration.default
        cfg.urlCache = cache
        cfg.requestCachePolicy = .useProtocolCachePolicy
        cfg.httpMaximumConnectionsPerHost = 6
        return URLSession(configuration: cfg)
    }()
}

/// Two-tier image cache shared across every `AuthAsyncImage` instance.
/// - **Memory**: NSCache with byte-cost limit (~80 MB) — lives as long as
///   the process and evicts least-used entries automatically on memory pressure.
/// - **Disk**: URLCache on a dedicated URLSession (~512 MB), survives app
///   restarts. The server's `ETag` enables 304 short-circuits.
/// - **Inflight**: dedupes concurrent fetches for the same URL so a
///   fast-scrolling grid only kicks off one network request per thumbnail.
@MainActor
final class ImageCache {
    static let shared = ImageCache()

    private let cache: NSCache<NSURL, PlatformImage> = {
        let c = NSCache<NSURL, PlatformImage>()
        c.totalCostLimit = 80 * 1024 * 1024 // ~80 MB of decoded pixels
        return c
    }()
    private var inflight: [URL: Task<PlatformImage?, Error>] = [:]

    func cached(for url: URL) -> PlatformImage? {
        cache.object(forKey: url as NSURL)
    }

    func image(for url: URL) async throws -> PlatformImage? {
        if let hit = cache.object(forKey: url as NSURL) {
            return hit
        }
        if let task = inflight[url] {
            return try await task.value
        }
        let task = Task<PlatformImage?, Error> { [weak self] in
            defer { Task { @MainActor in self?.inflight[url] = nil } }
            var req = URLRequest(url: url)
            if let token = TokenStore.read() {
                req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }
            let (data, _) = try await ImageNetworking.session.data(for: req)
            guard let img = PlatformImage(data: data) else { return nil }
            await MainActor.run {
                self?.cache.setObject(img, forKey: url as NSURL, cost: data.count)
            }
            return img
        }
        inflight[url] = task
        return try await task.value
    }

    /// Fire-and-forget warm up. Used by LibraryView to start loading the
    /// thumbnails of items a couple of scroll positions ahead.
    func prefetch(_ urls: [URL]) {
        for url in urls {
            if cache.object(forKey: url as NSURL) != nil { continue }
            if inflight[url] != nil { continue }
            Task { [weak self] in try? await self?.image(for: url) }
        }
    }
}

/// An async image that injects the Bearer token from Keychain so it can hit
/// authenticated server endpoints. Built around URLSession instead of
/// SwiftUI's AsyncImage so we control headers + share decode work between
/// equal URLs.
struct AuthAsyncImage<Placeholder: View, Failure: View>: View {
    let url: URL?
    var transaction: Transaction = Transaction(animation: .easeOut(duration: 0.18))
    @ViewBuilder var placeholder: () -> Placeholder
    @ViewBuilder var failure: () -> Failure

    @State private var phase: Phase = .empty

    private enum Phase: Equatable {
        case empty
        case loading
        case success(image: PlatformImage)
        case failure
    }

    var body: some View {
        ZStack {
            switch phase {
            case .empty, .loading:
                placeholder()
            case .success(let image):
                #if os(macOS)
                Image(nsImage: image)
                    .resizable()
                #else
                Image(uiImage: image)
                    .resizable()
                #endif
            case .failure:
                failure()
            }
        }
        .task(id: url) { await load() }
    }

    private func load() async {
        guard let url else {
            withTransaction(transaction) { phase = .empty }
            return
        }
        // Synchronous cache hit — no flash of placeholder, no animation.
        if let hit = ImageCache.shared.cached(for: url) {
            phase = .success(image: hit)
            return
        }
        withTransaction(transaction) { phase = .loading }
        do {
            guard let img = try await ImageCache.shared.image(for: url) else {
                if Task.isCancelled { return }
                withTransaction(transaction) { phase = .failure }
                return
            }
            if Task.isCancelled { return }
            withTransaction(transaction) { phase = .success(image: img) }
        } catch {
            if Task.isCancelled { return }
            withTransaction(transaction) { phase = .failure }
        }
    }
}

extension AuthAsyncImage where Placeholder == ShimmerPlaceholder, Failure == ImageFailurePlaceholder {
    init(url: URL?) {
        self.init(
            url: url,
            placeholder: { ShimmerPlaceholder() },
            failure: { ImageFailurePlaceholder() },
        )
    }
}

struct ShimmerPlaceholder: View {
    @State private var on = false
    var body: some View {
        Rectangle()
            .fill(Color.secondary.opacity(0.18))
            .overlay(
                LinearGradient(
                    colors: [.clear, .white.opacity(0.06), .clear],
                    startPoint: .leading,
                    endPoint: .trailing,
                )
                .offset(x: on ? 200 : -200)
                .blendMode(.overlay)
                .clipped()
            )
            .onAppear { withAnimation(.linear(duration: 1.4).repeatForever(autoreverses: false)) { on = true } }
    }
}

struct ImageFailurePlaceholder: View {
    var body: some View {
        ZStack {
            Color.secondary.opacity(0.12)
            Image(systemName: "photo")
                .foregroundStyle(.secondary)
                .imageScale(.large)
        }
    }
}

extension AuthAsyncImage where Placeholder == ShimmerPlaceholder, Failure == ImageFailurePlaceholder {
    init(url: URL?) {
        self.init(
            url: url,
            placeholder: { ShimmerPlaceholder() },
            failure: { ImageFailurePlaceholder() },
        )
    }
}

struct ShimmerPlaceholder: View {
    @State private var on = false
    var body: some View {
        Rectangle()
            .fill(Color.secondary.opacity(0.18))
            .overlay(
                LinearGradient(
                    colors: [.clear, .white.opacity(0.06), .clear],
                    startPoint: .leading,
                    endPoint: .trailing,
                )
                .offset(x: on ? 200 : -200)
                .blendMode(.overlay)
                .clipped()
            )
            .onAppear { withAnimation(.linear(duration: 1.4).repeatForever(autoreverses: false)) { on = true } }
    }
}

struct ImageFailurePlaceholder: View {
    var body: some View {
        ZStack {
            Color.secondary.opacity(0.12)
            Image(systemName: "photo")
                .foregroundStyle(.secondary)
                .imageScale(.large)
        }
    }
}
