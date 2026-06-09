import SwiftUI

/// Top-level Albums screen. Lists library albums + smart-album sections from
/// `/api/smart-albums`. Tapping a card opens the library tab pre-filtered to
/// match.
struct AlbumsView: View {
    @State private var data: SmartAlbumsResponse?
    @State private var loading = false
    @State private var error: String?
    @State private var openedAlbum: OpenedAlbum?

    private let columns = [GridItem(.adaptive(minimum: 140), spacing: 12)]

    var body: some View {
        ScrollView {
            if loading {
                ProgressView().controlSize(.large).padding(.top, 64)
            } else if let error {
                EmptyState(
                    systemImage: "exclamationmark.triangle",
                    title: "Couldn’t load albums",
                    message: error,
                    actionLabel: "Retry",
                    action: { Task { await load() } },
                )
                .padding(.top, 64)
            } else if let data {
                VStack(alignment: .leading, spacing: 28) {
                    section(title: "Library", icon: "rectangle.stack", albums: data.library)
                    section(title: "Tags", icon: "tag", albums: data.tags)
                    section(title: "Cameras", icon: "camera", albums: data.cameras)
                    section(title: "Festivals", icon: "sparkles", albums: data.festivals)
                    section(title: "Years", icon: "calendar", albums: data.years)
                    section(title: "Places", icon: "mappin.and.ellipse", albums: data.places)
                }
                .padding(16)
            }
        }
        .navigationTitle("Albums")
        .task {
            if data == nil { await load() }
        }
        .refreshable { await load() }
        .fullScreenCoverIfAvailable(item: $openedAlbum) { opened in
            FilteredLibrarySheet(filters: opened.filters, title: opened.title)
        }
    }

    @ViewBuilder
    private func section(title: String, icon: String, albums: [SmartAlbum]) -> some View {
        if !albums.isEmpty {
            VStack(alignment: .leading, spacing: 10) {
                Label(title, systemImage: icon)
                    .font(.headline)
                LazyVGrid(columns: columns, spacing: 12) {
                    ForEach(albums) { album in
                        AlbumCard(album: album)
                            .onTapGesture {
                                openedAlbum = OpenedAlbum(
                                    title: album.title,
                                    filters: album.filters.toFilters(),
                                )
                            }
                    }
                }
            }
        }
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            data = try await CatalogRepository.shared.listSmartAlbums()
        } catch {
            self.error = error.localizedDescription
        }
    }
}

private struct OpenedAlbum: Identifiable {
    let title: String
    let filters: Filters
    var id: String { title }
}

/// Reusable presentation: hosts a `LibraryView`-like screen pre-loaded with
/// the given filters. Wraps in NavigationStack so it has a title/back button.
struct FilteredLibrarySheet: View {
    let filters: Filters
    let title: String
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            FilteredLibraryGrid(filters: filters)
                .navigationTitle(title)
                #if os(iOS)
                .navigationBarTitleDisplayMode(.inline)
                #endif
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Close") { dismiss() }
                    }
                }
        }
    }
}

/// Standalone grid bound to its own MediaQueryStore — used by FilteredLibrarySheet.
private struct FilteredLibraryGrid: View {
    let filters: Filters
    @State private var store = MediaQueryStore()
    @State private var selected: Media?
    private let columns = [GridItem(.adaptive(minimum: 100), spacing: 2)]

    var body: some View {
        ScrollView {
            if store.items.isEmpty && store.loading {
                ProgressView().padding(.top, 80)
            } else if store.items.isEmpty {
                EmptyState(
                    systemImage: "photo",
                    title: "No matching media",
                    message: "This album is currently empty.",
                    actionLabel: nil,
                    action: nil,
                )
                .padding(.top, 60)
            } else {
                LazyVGrid(columns: columns, spacing: 2) {
                    ForEach(store.items) { item in
                        MediaTile(item: item)
                            .onTapGesture { selected = item }
                            .onAppear { store.loadMoreIfNeeded(currentItem: item) }
                    }
                }
                .padding(.horizontal, 6)
                if store.loading {
                    ProgressView().padding(.vertical, 16)
                }
            }
        }
        .task {
            store.filters = filters
        }
        .fullScreenCoverIfAvailable(item: $selected) { item in
            MediaDetailView(
                store: store,
                startId: item.id,
                onClose: { selected = nil },
                onDelete: { id in
                    store.remove(id: id)
                    selected = nil
                },
            )
        }
    }
}

// MARK: - Album card

struct AlbumCard: View {
    let album: SmartAlbum
    private let repo = MediaRepository.shared

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ZStack(alignment: .topTrailing) {
                Group {
                    if let cover = album.coverId {
                        AuthAsyncImage(url: repo.thumbnailURL(for: cover, size: "lg"))
                    } else {
                        ZStack {
                            Color.secondary.opacity(0.12)
                            Image(systemName: iconName)
                                .font(.system(size: 32))
                                .foregroundStyle(.secondary.opacity(0.5))
                        }
                    }
                }
                .aspectRatio(4.0/3.0, contentMode: .fill)
                .clipped()
                .clipShape(.rect(cornerRadius: 14))
                .overlay(
                    LinearGradient(colors: [.clear, .black.opacity(0.55)], startPoint: .top, endPoint: .bottom)
                        .clipShape(.rect(cornerRadius: 14))
                )

                if let count = album.count {
                    Text(count.formatted(.number))
                        .font(.caption2.weight(.semibold))
                        .padding(.horizontal, 8).padding(.vertical, 2)
                        .background(.black.opacity(0.55), in: .capsule)
                        .foregroundStyle(.white)
                        .padding(8)
                }
            }
            .overlay(alignment: .bottomLeading) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(album.title)
                        .font(.subheadline.weight(.semibold))
                        .lineLimit(1)
                        .foregroundStyle(.white)
                    if let subtitle = album.subtitle, !subtitle.isEmpty {
                        Text(subtitle)
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.75))
                            .lineLimit(1)
                    }
                }
                .padding(10)
            }
        }
    }

    private var iconName: String {
        switch album.icon {
        case "tag": return "tag"
        case "camera": return "camera"
        case "sparkles": return "sparkles"
        case "calendar": return "calendar"
        case "map-pin", "places": return "mappin.and.ellipse"
        case "star": return "star"
        case "trash-2", "trash": return "trash"
        case "film": return "film"
        default: return "photo.on.rectangle"
        }
    }
}
