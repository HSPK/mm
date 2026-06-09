import SwiftUI

struct LibraryView: View {
    @State private var store = MediaQueryStore()
    @State private var selection = SelectionStore()
    @State private var selectedItem: Media?
    @State private var showFilterSheet = false
    @State private var showSearch = false
    @State private var searchDraft = ""
    @State private var showDeleteConfirm = false
    @State private var deletingBatch = false
    @State private var showAlbumPicker = false
    @State private var actionError: String?
    @State private var contextMenuAlbumForId: Int?
    @AppStorage("library.dateGroup") private var dateGroupRaw: String = DateGroupMode.none.rawValue

    private var dateGroup: DateGroupMode {
        DateGroupMode(rawValue: dateGroupRaw) ?? .none
    }

    private let columns = [GridItem(.adaptive(minimum: 100), spacing: 2)]

    var body: some View {
        ZStack(alignment: .bottom) {
            ScrollView {
                ActiveFilterTags(filters: $store.filters)
                    .padding(.horizontal, 12)
                    .padding(.top, 4)
                    .animation(.easeInOut(duration: 0.15), value: store.filters)

                content
                    .padding(.bottom, selection.isActive ? 70 : 0)
            }
            .refreshable { store.reload() }
            .task {
                if store.items.isEmpty { store.reload() }
            }

            if selection.isActive {
                SelectionActionBar(
                    count: selection.count,
                    inTrash: store.filters.deleted,
                    deleting: deletingBatch,
                    onCancel: { selection.exit() },
                    onSelectAll: { selection.selectAll(in: store.items.map(\.id)) },
                    onDelete: { showDeleteConfirm = true },
                    onAddToAlbum: { showAlbumPicker = true },
                )
                .padding(.horizontal, 12).padding(.bottom, 12)
                .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .animation(.easeInOut(duration: 0.18), value: selection.isActive)
        .navigationTitle(title)
        .toolbar { toolbarItems }
        #if os(iOS)
        .searchable(text: $searchDraft, isPresented: $showSearch, placement: .navigationBarDrawer(displayMode: .always), prompt: "Search media")
        #else
        .searchable(text: $searchDraft, prompt: "Search media")
        #endif
        .onSubmit(of: .search) {
            store.filters.search = searchDraft.isEmpty ? nil : searchDraft
        }
        .onChange(of: showSearch) { _, isOn in
            if !isOn && searchDraft.isEmpty {
                store.filters.search = nil
            }
        }
        .sheet(isPresented: $showFilterSheet) {
            FilterSheet(filters: $store.filters)
                #if os(iOS)
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
                .presentationBackground(.thickMaterial)
                #endif
        }
        .sheet(isPresented: $showAlbumPicker) {
            AlbumPickerSheet(mediaIds: Array(selection.selected)) { _ in
                selection.exit()
                showAlbumPicker = false
            }
            #if os(iOS)
            .presentationDetents([.medium, .large])
            .presentationDragIndicator(.visible)
            .presentationBackground(.thickMaterial)
            #endif
        }
        .sheet(item: Binding(
            get: { contextMenuAlbumForId.map { CtxItem(id: $0) } },
            set: { contextMenuAlbumForId = $0?.id },
        )) { ctx in
            AlbumPickerSheet(mediaIds: [ctx.id]) { _ in
                contextMenuAlbumForId = nil
            }
            #if os(iOS)
            .presentationDetents([.medium, .large])
            .presentationDragIndicator(.visible)
            .presentationBackground(.thickMaterial)
            #endif
        }
        .confirmationDialog(
            store.filters.deleted ? "Permanently delete \(selection.count) item(s)?" : "Move \(selection.count) item(s) to trash?",
            isPresented: $showDeleteConfirm,
            titleVisibility: .visible,
        ) {
            Button(store.filters.deleted ? "Delete permanently" : "Move to trash", role: .destructive) {
                Task { await deleteSelection() }
            }
            Button("Cancel", role: .cancel) {}
        }
        .fullScreenCoverIfAvailable(item: $selectedItem) { item in
            MediaDetailView(
                store: store,
                startId: item.id,
                onClose: { selectedItem = nil },
                onDelete: { id in
                    store.remove(id: id)
                    selectedItem = nil
                },
            )
        }
        .overlay(alignment: .top) {
            if let actionError {
                Label(actionError, systemImage: "exclamationmark.triangle.fill")
                    .padding(.horizontal, 14).padding(.vertical, 10)
                    .background(.regularMaterial, in: .capsule)
                    .padding(.top, 8)
                    .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
    }

    private var title: String {
        if selection.isActive {
            return "\(selection.count) selected"
        }
        if store.filters.deleted { return "Recently Deleted" }
        return "Library"
    }

    @ToolbarContentBuilder
    private var toolbarItems: some ToolbarContent {
        ToolbarItemGroup(placement: .primaryAction) {
            if selection.isActive {
                EmptyView()
            } else if store.filters.deleted {
                Menu {
                    Button(role: .destructive) {
                        Task { await emptyTrash() }
                    } label: {
                        Label("Empty trash", systemImage: "trash.slash")
                    }
                    Button("Done") { store.filters.deleted = false }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
            } else {
                Menu {
                    Button { showFilterSheet = true } label: {
                        Label("Filters", systemImage: "slider.horizontal.3")
                    }
                    Menu {
                        ForEach(DateGroupMode.allCases) { mode in
                            Button {
                                dateGroupRaw = mode.rawValue
                            } label: {
                                if dateGroup == mode {
                                    Label(mode.label, systemImage: "checkmark")
                                } else {
                                    Text(mode.label)
                                }
                            }
                        }
                    } label: {
                        Label("Group by date", systemImage: dateGroup.systemImage)
                    }
                    Button {
                        selection.selectAll(in: store.items.map(\.id))
                    } label: {
                        Label("Select", systemImage: "checkmark.circle")
                    }
                    .disabled(store.items.isEmpty)
                    Button {
                        var f = store.filters
                        f.deleted = true
                        store.filters = f
                    } label: {
                        Label("Recently Deleted", systemImage: "trash")
                    }
                    if store.filters.hasActive {
                        Divider()
                        Button(role: .destructive) {
                            var cleared = Filters()
                            cleared.sort = store.filters.sort
                            cleared.order = store.filters.order
                            store.filters = cleared
                        } label: {
                            Label("Clear filters", systemImage: "xmark.circle")
                        }
                    }
                } label: {
                    Image(systemName: store.filters.hasActive ? "line.3.horizontal.decrease.circle.fill" : "line.3.horizontal.decrease.circle")
                }
            }
        }
    }

    @ViewBuilder
    private var content: some View {
        if store.items.isEmpty && store.loading {
            LoadingGridPlaceholder()
                .padding(.horizontal, 6)
        } else if store.items.isEmpty, let error = store.error {
            EmptyState(
                systemImage: "exclamationmark.triangle",
                title: "Couldn’t load media",
                message: error,
                actionLabel: "Retry",
                action: store.reload,
            )
            .padding(.top, 64)
        } else if store.items.isEmpty {
            EmptyState(
                systemImage: store.filters.deleted ? "trash" : "photo.on.rectangle.angled",
                title: store.filters.deleted ? "Trash is empty" : (store.filters.hasActive ? "No matches" : "No media yet"),
                message: store.filters.hasActive
                    ? "Try adjusting or clearing filters."
                    : "Import photos and videos from the server to see them here.",
                actionLabel: store.filters.hasActive ? "Clear filters" : nil,
                action: store.filters.hasActive ? { store.filters = Filters() } : nil,
            )
            .padding(.top, 64)
        } else {
            let groups = MediaGrouper.group(store.items, mode: dateGroup)
            let pinned: PinnedScrollableViews = dateGroup == .none ? [] : [.sectionHeaders]
            LazyVStack(alignment: .leading, spacing: 8, pinnedViews: pinned) {
                ForEach(groups) { group in
                    Section {
                        LazyVGrid(columns: columns, spacing: 2) {
                            ForEach(group.items) { item in
                                MediaTile(
                                    item: item,
                                    selectionMode: selection.isActive,
                                    selected: selection.selected.contains(item.id),
                                )
                                .onTapGesture {
                                    if selection.isActive { selection.toggle(item.id) }
                                    else { selectedItem = item }
                                }
                                .onLongPressGesture(minimumDuration: 0.35) {
                                    if !selection.isActive { selection.enter(with: item.id) }
                                }
                                .contextMenu {
                                    tileContextMenu(for: item)
                                } preview: {
                                    AuthAsyncImage(url: MediaRepository.shared.thumbnailURL(for: item.id, size: "xl"))
                                        .frame(width: 240, height: 240)
                                }
                                .onAppear { store.loadMoreIfNeeded(currentItem: item) }
                            }
                        }
                        .padding(.horizontal, 6)
                    } header: {
                        if dateGroup != .none {
                            DateGroupHeader(title: group.title, count: group.items.count)
                        }
                    }
                }
            }

            if store.loading {
                ProgressView().padding(.vertical, 24)
            }
            if !store.hasMore && !store.items.isEmpty {
                Text("End")
                    .font(.caption2)
                    .foregroundStyle(.secondary.opacity(0.6))
                    .padding(.vertical, 16)
                    .textCase(.uppercase)
                    .tracking(2)
            }
        }
    }

    // MARK: - Actions

    private func deleteSelection() async {
        let ids = Array(selection.selected)
        guard !ids.isEmpty else { return }
        deletingBatch = true
        defer { deletingBatch = false }
        let repo = MediaRepository.shared
        do {
            if store.filters.deleted {
                // Permanent delete — no batch endpoint, do them in parallel.
                try await withThrowingTaskGroup(of: Void.self) { group in
                    for id in ids {
                        group.addTask { try await repo.delete(id: id, permanent: true) }
                    }
                    for try await _ in group {}
                }
            } else {
                _ = try await repo.batchDelete(ids: ids)
            }
            for id in ids { store.remove(id: id) }
            selection.exit()
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
            try? await Task.sleep(for: .seconds(2.6))
            withAnimation { actionError = nil }
        }
    }

    // MARK: - Context menu

    @ViewBuilder
    private func tileContextMenu(for item: Media) -> some View {
        if store.filters.deleted {
            Button {
                Task { await restore(item.id) }
            } label: {
                Label("Restore", systemImage: "arrow.uturn.backward")
            }
            Button(role: .destructive) {
                Task { await deletePermanently(item.id) }
            } label: {
                Label("Delete permanently", systemImage: "trash")
            }
        } else {
            Button {
                selectedItem = item
            } label: {
                Label("Open", systemImage: "arrow.up.right.square")
            }
            Button {
                contextMenuAlbumForId = item.id
            } label: {
                Label("Add to album…", systemImage: "rectangle.stack.badge.plus")
            }
            Divider()
            Section("Rate") {
                ForEach((0...5).reversed(), id: \.self) { stars in
                    Button {
                        Task { await rate(item.id, stars: stars) }
                    } label: {
                        Label(stars == 0 ? "No rating" : String(repeating: "★", count: stars),
                              systemImage: stars == item.rating ? "checkmark" : "")
                    }
                }
            }
            Divider()
            Button(role: .destructive) {
                Task { await trash(item.id) }
            } label: {
                Label("Move to trash", systemImage: "trash")
            }
        }
    }

    // MARK: - Single-item actions

    private func rate(_ id: Int, stars: Int) async {
        do {
            let res = try await MediaRepository.shared.setRating(id: id, rating: stars)
            store.update(id: id) { item in
                Media(
                    id: item.id, filename: item.filename, extension_: item.extension_,
                    mediaType: item.mediaType, fileSize: item.fileSize, rating: res.rating,
                    width: item.width, height: item.height, dateTaken: item.dateTaken,
                    cameraModel: item.cameraModel, duration: item.duration,
                    gpsLat: item.gpsLat, gpsLon: item.gpsLon,
                    locationLabel: item.locationLabel, locationCity: item.locationCity,
                    locationCountry: item.locationCountry, deletedAt: item.deletedAt,
                )
            }
        } catch {
            flashError(error.localizedDescription)
        }
    }

    private func trash(_ id: Int) async {
        do {
            try await MediaRepository.shared.delete(id: id)
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

    private func restore(_ id: Int) async {
        do {
            try await MediaRepository.shared.restore(id: id)
            store.remove(id: id) // disappears from trash view
        } catch {
            flashError(error.localizedDescription)
        }
    }
}

/// Wrapper so we can drive a `.sheet(item:)` from a `Int?` state.
private struct CtxItem: Identifiable, Hashable {
    let id: Int
}

// MARK: - Date group section header

struct DateGroupHeader: View {
    let title: String
    let count: Int

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title.isEmpty ? "Unknown" : title)
                .font(.headline)
            Spacer()
            Text("\(count)")
                .font(.caption.monospacedDigit())
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.regularMaterial)
    }
}

// MARK: - Active filter chips

struct ActiveFilterTags: View {
    @Binding var filters: Filters

    var body: some View {
        if filters.hasActive {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(tags) { tag in
                        TagChip(label: tag.label, color: tag.color) { tag.onRemove() }
                    }
                }
                .padding(.vertical, 4)
            }
        }
    }

    private struct ChipModel: Identifiable {
        let id: String
        let label: String
        let color: Color
        let onRemove: () -> Void
    }

    private var tags: [ChipModel] {
        var result: [ChipModel] = []
        if let t = filters.type {
            result.append(.init(id: "type", label: t.label, color: .blue) {
                filters.type = nil
            })
        }
        if let tag = filters.tag, !tag.isEmpty {
            result.append(.init(id: "tag", label: "#\(tag)", color: .purple) {
                filters.tag = nil
            })
        }
        if let cam = filters.camera, !cam.isEmpty {
            result.append(.init(id: "camera", label: cam, color: .indigo) {
                filters.camera = nil
            })
        }
        if filters.dateFrom != nil || filters.dateTo != nil {
            let f = DateFormatter()
            f.dateFormat = "yy/MM/dd"
            let from = filters.dateFrom.map { f.string(from: $0) } ?? ""
            let to = filters.dateTo.map { f.string(from: $0) } ?? ""
            let label = from.isEmpty ? "→ \(to)" : (to.isEmpty ? "\(from) →" : "\(from) → \(to)")
            result.append(.init(id: "date", label: label, color: .gray) {
                filters.dateFrom = nil
                filters.dateTo = nil
            })
        }
        if let r = filters.minRating, r > 0 {
            result.append(.init(id: "rating", label: "★ ≥ \(r)", color: .yellow) {
                filters.minRating = nil
            })
        }
        if filters.favoritesOnly {
            result.append(.init(id: "fav", label: "Favorites", color: .yellow) {
                filters.favoritesOnly = false
            })
        }
        if let s = filters.search, !s.isEmpty {
            result.append(.init(id: "search", label: "“\(s)”", color: .gray) {
                filters.search = nil
            })
        }
        return result
    }
}

private struct TagChip: View {
    let label: String
    let color: Color
    let onRemove: () -> Void

    var body: some View {
        HStack(spacing: 4) {
            Text(label)
                .font(.caption.weight(.medium))
                .lineLimit(1)
            Button(action: onRemove) {
                Image(systemName: "xmark")
                    .font(.caption2.weight(.bold))
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 10).padding(.vertical, 5)
        .background(color.opacity(0.15), in: .capsule)
        .overlay(Capsule().stroke(color.opacity(0.35), lineWidth: 1))
        .foregroundStyle(color)
    }
}

// MARK: - Selection action bar

private struct SelectionActionBar: View {
    let count: Int
    let inTrash: Bool
    let deleting: Bool
    let onCancel: () -> Void
    let onSelectAll: () -> Void
    let onDelete: () -> Void
    let onAddToAlbum: () -> Void

    var body: some View {
        HStack(spacing: 4) {
            BarButton(systemImage: "xmark", label: "Cancel", action: onCancel)
            Text(count.formatted(.number))
                .font(.callout.weight(.semibold))
                .padding(.horizontal, 8)
            BarButton(systemImage: "checkmark.circle", label: "All", action: onSelectAll)
            Spacer()
            if !inTrash {
                BarButton(systemImage: "folder.badge.plus", label: "Album", action: onAddToAlbum)
            }
            BarButton(
                systemImage: deleting ? "" : "trash",
                label: inTrash ? "Delete" : "Trash",
                destructive: true,
                loading: deleting,
                action: onDelete,
            )
        }
        .padding(.horizontal, 8).padding(.vertical, 6)
        .background(.regularMaterial, in: .capsule)
        .shadow(color: .black.opacity(0.25), radius: 10, y: 4)
    }
}

private struct BarButton: View {
    let systemImage: String
    let label: String
    var destructive: Bool = false
    var loading: Bool = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 4) {
                if loading {
                    ProgressView().controlSize(.small)
                } else {
                    Image(systemName: systemImage)
                }
                Text(label).font(.caption.weight(.semibold))
            }
            .padding(.horizontal, 10).padding(.vertical, 8)
            .foregroundStyle(destructive ? .red : .primary)
        }
        .buttonStyle(.plain)
        .disabled(loading)
    }
}

// MARK: - Helpers

private struct LoadingGridPlaceholder: View {
    private let columns = [GridItem(.adaptive(minimum: 100), spacing: 2)]
    var body: some View {
        LazyVGrid(columns: columns, spacing: 2) {
            ForEach(0..<18, id: \.self) { _ in
                ShimmerPlaceholder()
                    .aspectRatio(1, contentMode: .fill)
                    .clipShape(.rect(cornerRadius: 4))
            }
        }
    }
}

struct EmptyState: View {
    let systemImage: String
    let title: String
    let message: String
    let actionLabel: String?
    let action: (() -> Void)?

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: systemImage)
                .font(.system(size: 36))
                .foregroundStyle(.secondary)
                .padding(12)
                .background(.secondary.opacity(0.1), in: .circle)
            Text(title)
                .font(.headline)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
            if let actionLabel, let action {
                Button(actionLabel, action: action)
                    .buttonStyle(.bordered)
            }
        }
        .frame(maxWidth: .infinity)
    }
}

// macOS doesn't have fullScreenCover; fall back to sheet.
extension View {
    @ViewBuilder
    func fullScreenCoverIfAvailable<Item: Identifiable, Content: View>(
        item: Binding<Item?>,
        @ViewBuilder content: @escaping (Item) -> Content,
    ) -> some View {
        #if os(macOS)
        sheet(item: item, content: content)
        #else
        fullScreenCover(item: item, content: content)
        #endif
    }
}