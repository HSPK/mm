import Foundation
import Observation

/// Paginated photo grid state. Mirrors the responsibilities of the web
/// `stores/media-query.ts` (just the read/refresh path — selection mode is
/// handled by SelectionStore).
@MainActor
@Observable
final class MediaQueryStore {
    private(set) var items: [Media] = []
    private(set) var page: Int = 1
    private(set) var total: Int = 0
    private(set) var hasMore: Bool = true
    private(set) var loading: Bool = false
    private(set) var error: String?

    var filters = Filters() {
        didSet {
            if oldValue != filters { reload() }
        }
    }

    private let repo = MediaRepository.shared
    private var fetchTask: Task<Void, Never>?

    /// Loads the first page, cancelling any in-flight fetch.
    func reload() {
        fetchTask?.cancel()
        items = []
        page = 1
        hasMore = true
        fetch(reset: true)
    }

    /// Loads the next page if available and not currently loading.
    func loadMoreIfNeeded(currentItem item: Media?) {
        guard let item, !loading, hasMore else { return }
        let triggerIndex = max(items.count - 5, 0)
        guard let idx = items.firstIndex(of: item), idx >= triggerIndex else { return }
        fetch(reset: false)
    }

    func remove(id: Int) {
        items.removeAll { $0.id == id }
        total = max(0, total - 1)
    }

    /// Replaces the entire item set in-place. Used when a view (e.g. MapView)
    /// wants to feed a custom, externally-filtered list to MediaDetailView
    /// without performing a normal page-by-page fetch.
    func replace(with items: [Media]) {
        fetchTask?.cancel()
        self.items = items
        total = items.count
        page = 1
        hasMore = false
        loading = false
        error = nil
    }

    func update(id: Int, transform: (Media) -> Media) {
        guard let idx = items.firstIndex(where: { $0.id == id }) else { return }
        items[idx] = transform(items[idx])
    }

    private func fetch(reset: Bool) {
        fetchTask?.cancel()
        loading = true
        error = nil
        let nextPage = reset ? 1 : page
        let snapshot = filters
        fetchTask = Task { [repo] in
            do {
                let res = try await repo.list(page: nextPage, filters: snapshot)
                if Task.isCancelled { return }
                if reset {
                    items = res.items
                    page = 2
                } else {
                    items.append(contentsOf: res.items)
                    page += 1
                }
                total = res.total
                hasMore = nextPage < res.pages
                loading = false
                // Warm the image cache for the freshly-arrived rows so the
                // grid renders instantly once they appear on screen.
                ImageCache.shared.prefetch(
                    res.items.map { MediaRepository.shared.thumbnailURL(for: $0.id, size: "md") }
                )
            } catch is CancellationError {
                // navigated away; leave state alone
            } catch {
                self.error = error.localizedDescription
                self.loading = false
            }
        }
    }
}
