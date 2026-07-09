#if os(macOS)
import SwiftUI

struct MacLibraryView: View {
    @State private var store = MediaQueryStore()
    @State private var selectedItem: Media?
    @State private var showFilterSheet = false
    @State private var albumPickerItem: MacAlbumPickerItem?
    @State private var actionError: String?
    @State private var searchDraft = ""
    @AppStorage("library.dateGroup") private var dateGroupRaw: String = DateGroupMode.none.rawValue

    private var dateGroup: DateGroupMode {
        DateGroupMode(rawValue: dateGroupRaw) ?? .none
    }

    var body: some View {
        mainContent
            .background(Color(nsColor: .windowBackgroundColor))
            .navigationTitle(title)
            .toolbar { toolbarContent }
            .searchable(text: $searchDraft, prompt: "Search")
            .onSubmit(of: .search) {
                store.filters.search = searchDraft.trimmingCharacters(in: .whitespacesAndNewlines).nilIfEmpty
            }
            .task {
                if store.items.isEmpty { store.reload() }
            }
            .sheet(isPresented: $showFilterSheet) {
                FilterSheet(filters: $store.filters)
                    .frame(minWidth: 420, minHeight: 520)
            }
            .sheet(item: $albumPickerItem) { item in
                AlbumPickerSheet(mediaIds: [item.id]) { _ in
                    albumPickerItem = nil
                }
                .frame(minWidth: 420, minHeight: 520)
            }
            .sheet(item: $selectedItem) { item in
                MediaDetailView(
                    store: store,
                    startId: item.id,
                    onClose: { selectedItem = nil },
                    onDelete: { id in
                        store.remove(id: id)
                        selectedItem = nil
                    },
                )
                .frame(minWidth: 980, minHeight: 680)
            }
            .overlay(alignment: .top) {
                if let actionError {
                    Label(actionError, systemImage: "exclamationmark.triangle.fill")
                        .padding(.horizontal, 14)
                        .padding(.vertical, 9)
                        .background(.regularMaterial, in: Capsule())
                        .padding(.top, 10)
                        .transition(.opacity)
                }
            }
    }

    private var mainContent: some View {
        VStack(alignment: .leading, spacing: 10) {
            summary

            ActiveFilterTags(filters: $store.filters)
                .padding(.horizontal, 18)

            content
        }
        .padding(.top, 10)
    }

    private var title: String {
        store.filters.deleted ? "Recently Deleted" : "All Photos"
    }

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .principal) {
            Picker("View", selection: $dateGroupRaw) {
                ForEach([DateGroupMode.none]) { mode in
                    Text(mode.label).tag(mode.rawValue)
                }
            }
            .pickerStyle(.segmented)
            .frame(width: 120)
        }

        ToolbarItemGroup(placement: .primaryAction) {
            Button {
                store.reload()
            } label: {
                Label("Refresh", systemImage: "arrow.clockwise")
            }

            Button {
                showFilterSheet = true
            } label: {
                Label("Filters", systemImage: store.filters.hasActive ? "line.3.horizontal.decrease.circle.fill" : "line.3.horizontal.decrease.circle")
            }

            if store.filters.deleted {
                Button("Done") { store.filters.deleted = false }
                Menu {
                    Button(role: .destructive) {
                        Task { await emptyTrash() }
                    } label: {
                        Label("Empty Trash", systemImage: "trash.slash")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
            } else {
                Button {
                    var next = store.filters
                    next.deleted = true
                    store.filters = next
                } label: {
                    Label("Trash", systemImage: "trash")
                }
            }
        }
    }

    private var summary: some View {
        HStack {
            Text(store.loading && store.items.isEmpty ? "Loading..." : "\(store.total.formatted(.number)) items")
                .font(.caption)
                .foregroundStyle(.secondary)
            Spacer()
        }
        .padding(.horizontal, 18)
    }

    @ViewBuilder
    private var content: some View {
        if store.items.isEmpty && store.loading {
            loadingGrid
                .padding(.horizontal, 18)
                .frame(maxHeight: .infinity, alignment: .top)
        } else if store.items.isEmpty, let error = store.error {
            EmptyState(
                systemImage: "exclamationmark.triangle",
                title: "Couldn’t load media",
                message: error,
                actionLabel: "Retry",
                action: store.reload,
            )
            .padding(.top, 80)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        } else if store.items.isEmpty {
            EmptyState(
                systemImage: store.filters.deleted ? "trash" : "photo.on.rectangle.angled",
                title: store.filters.deleted ? "Trash is empty" : "No media",
                message: store.filters.hasActive ? "Try clearing filters." : "Import photos and videos to see them here.",
                actionLabel: store.filters.hasActive ? "Clear filters" : nil,
                action: store.filters.hasActive ? clearFilters : nil,
            )
            .padding(.top, 80)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        } else {
            MacPhotoWallView(
                items: store.items,
                inTrash: store.filters.deleted,
                onOpen: { selectedItem = $0 },
                onLoadMore: { store.loadMoreIfNeeded(currentItem: $0) },
                onAddToAlbum: { albumPickerItem = MacAlbumPickerItem(id: $0.id) },
                onMoveToTrash: { item in Task { await trash(item.id) } },
                onRestore: { item in Task { await restore(item.id) } },
                onDeletePermanently: { item in Task { await deletePermanently(item.id) } },
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private var loadingGrid: some View {
        LazyVGrid(columns: placeholderColumns, spacing: 2) {
            ForEach(0..<42, id: \.self) { _ in
                ShimmerPlaceholder()
                    .aspectRatio(1, contentMode: .fit)
            }
        }
    }

    private var placeholderColumns: [GridItem] {
        [GridItem(.adaptive(minimum: 112, maximum: 140), spacing: 2)]
    }

    private func clearFilters() {
        var cleared = Filters()
        cleared.sort = store.filters.sort
        cleared.order = store.filters.order
        store.filters = cleared
    }

    private func trash(_ id: Int) async {
        do {
            try await MediaRepository.shared.delete(id: id)
            store.remove(id: id)
        } catch {
            flashError(error.localizedDescription)
        }
    }

    private func restore(_ id: Int) async {
        do {
            try await MediaRepository.shared.restore(id: id)
            store.remove(id: id)
        } catch {
            flashError(error.localizedDescription)
        }
    }

    private func deletePermanently(_ id: Int) async {
        do {
            try await MediaRepository.shared.delete(id: id, permanent: true)
            store.remove(id: id)
        } catch {
            flashError(error.localizedDescription)
        }
    }

    private func emptyTrash() async {
        do {
            try await MediaRepository.shared.emptyTrash()
            store.filters.deleted = false
        } catch {
            flashError(error.localizedDescription)
        }
    }

    private func flashError(_ message: String) {
        withAnimation { actionError = message }
        Task {
            try? await Task.sleep(for: .seconds(2.5))
            withAnimation { actionError = nil }
        }
    }
}

private struct MacAlbumPickerItem: Identifiable {
    let id: Int
}

private extension String {
    var nilIfEmpty: String? {
        isEmpty ? nil : self
    }
}
#endif
