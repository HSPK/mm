import AVKit
import SwiftUI

struct MediaDetailView: View {
    let store: MediaQueryStore
    let startId: Int
    let onClose: () -> Void
    let onDelete: (Int) -> Void

    @State private var currentIndex: Int
    @State private var showShare = false
    @State private var showInfo = false
    @State private var shareURL: URL?
    @State private var preparingShare = false
    @State private var deleting = false
    @State private var restoring = false
    @State private var error: String?

    private let repo = MediaRepository.shared

    init(store: MediaQueryStore, startId: Int, onClose: @escaping () -> Void, onDelete: @escaping (Int) -> Void) {
        self.store = store
        self.startId = startId
        self.onClose = onClose
        self.onDelete = onDelete
        self._currentIndex = State(
            initialValue: max(store.items.firstIndex(where: { $0.id == startId }) ?? 0, 0),
        )
    }

    private var items: [Media] { store.items }
    private var currentItem: Media? {
        guard currentIndex >= 0 && currentIndex < items.count else { return nil }
        return items[currentIndex]
    }
    private var inTrash: Bool { currentItem?.deletedAt != nil || store.filters.deleted }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            if let item = currentItem {
                #if os(macOS)
                PageContent(item: item)
                    .id(item.id)
                    .onAppear { store.loadMoreIfNeeded(currentItem: item) }
                #else
                TabView(selection: $currentIndex) {
                    ForEach(items.indices, id: \.self) { idx in
                        let m = items[idx]
                        PageContent(item: m)
                            .tag(idx)
                            .onAppear { store.loadMoreIfNeeded(currentItem: m) }
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: .never))
                #endif

                VStack {
                    Chrome(
                        item: item,
                        inTrash: inTrash,
                        preparingShare: preparingShare,
                        deleting: deleting,
                        restoring: restoring,
                        onClose: onClose,
                        onShare: { Task { await prepareShare() } },
                        onInfo: { showInfo = true },
                        onRestore: { Task { await restoreCurrent() } },
                        onDelete: { Task { await deleteCurrent() } },
                    )
                    Spacer()
                    Footer(item: item, index: currentIndex, total: items.count)
                }
                .padding(.horizontal, 12)
            }

            if let error {
                VStack {
                    Spacer()
                    Label(error, systemImage: "exclamationmark.triangle.fill")
                        .padding(.horizontal, 14).padding(.vertical, 10)
                        .background(.regularMaterial, in: .capsule)
                        .padding(.bottom, 32)
                }
            }
        }
        #if os(iOS)
        .statusBarHidden(true)
        .persistentSystemOverlays(.hidden)
        #endif
        #if os(macOS)
        .onMoveCommand { direction in
            switch direction {
            case .left: moveCurrent(by: -1)
            case .right: moveCurrent(by: 1)
            default: break
            }
        }
        #endif
        .sheet(isPresented: $showShare, onDismiss: cleanupShareURL) {
            if let shareURL {
                ShareSheet(items: [shareURL])
                    #if os(macOS)
                    .frame(minWidth: 320, minHeight: 200)
                    #endif
                    #if os(iOS)
                    .presentationDetents([.medium])
                    .presentationDragIndicator(.visible)
                    #endif
            }
        }
        .sheet(isPresented: $showInfo) {
            if let item = currentItem {
                MediaInfoSheet(mediaId: item.id, store: store)
                    #if os(macOS)
                    .frame(minWidth: 420, minHeight: 540)
                    #endif
                    #if os(iOS)
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
                    .presentationBackground(.thickMaterial)
                    #endif
            }
        }
    }

    private func prepareShare() async {
        guard let item = currentItem, !preparingShare else { return }
        preparingShare = true
        defer { preparingShare = false }
        do {
            shareURL = try await repo.downloadFile(for: item)
            showShare = true
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func cleanupShareURL() {
        guard let shareURL else { return }
        self.shareURL = nil
        do {
            try FileManager.default.removeItem(at: shareURL.deletingLastPathComponent())
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func moveCurrent(by delta: Int) {
        guard !items.isEmpty else { return }
        currentIndex = min(max(currentIndex + delta, 0), items.count - 1)
    }

    private func deleteCurrent() async {
        guard let item = currentItem, !deleting else { return }
        deleting = true
        defer { deleting = false }
        do {
            try await repo.delete(id: item.id, permanent: inTrash)
            onDelete(item.id)
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func restoreCurrent() async {
        guard let item = currentItem, !restoring else { return }
        restoring = true
        defer { restoring = false }
        do {
            try await repo.restore(id: item.id)
            // Remove from the trash view list
            onDelete(item.id)
        } catch {
            self.error = error.localizedDescription
        }
    }
}

// MARK: - Per-item content (photo vs video)

private struct PageContent: View {
    let item: Media

    var body: some View {
        if item.isVideo {
            VideoPageContent(item: item)
        } else {
            ZoomableImage(url: MediaRepository.shared.previewURL(for: item.id))
        }
    }
}

private struct VideoPageContent: View {
    let item: Media
    @State private var player: AVPlayer

    init(item: Media) {
        self.item = item
        self._player = State(initialValue: AVPlayer(url: MediaRepository.shared.fileURL(for: item.id)))
    }

    var body: some View {
        VideoPlayer(player: player)
            .ignoresSafeArea()
            .onDisappear { player.pause() }
    }
}

private struct ZoomableImage: View {
    let url: URL
    @State private var scale: CGFloat = 1
    @State private var lastScale: CGFloat = 1
    @State private var offset: CGSize = .zero
    @State private var lastOffset: CGSize = .zero

    var body: some View {
        AuthAsyncImage(url: url)
            .aspectRatio(contentMode: .fit)
            .scaleEffect(scale)
            .offset(offset)
            .gesture(
                MagnifyGesture()
                    .onChanged { value in
                        scale = max(1, min(8, lastScale * value.magnification))
                    }
                    .onEnded { _ in
                        lastScale = scale
                        if scale <= 1 {
                            withAnimation(.spring) { offset = .zero; lastOffset = .zero }
                        }
                    },
            )
            .simultaneousGesture(
                DragGesture()
                    .onChanged { value in
                        guard scale > 1 else { return }
                        offset = CGSize(
                            width: lastOffset.width + value.translation.width,
                            height: lastOffset.height + value.translation.height,
                        )
                    }
                    .onEnded { _ in lastOffset = offset },
            )
            .onTapGesture(count: 2) {
                withAnimation(.spring) {
                    if scale > 1 {
                        scale = 1; lastScale = 1
                        offset = .zero; lastOffset = .zero
                    } else {
                        scale = 2.5; lastScale = 2.5
                    }
                }
            }
    }
}

// MARK: - Chrome + Footer

private struct Chrome: View {
    let item: Media
    let inTrash: Bool
    let preparingShare: Bool
    let deleting: Bool
    let restoring: Bool
    let onClose: () -> Void
    let onShare: () -> Void
    let onInfo: () -> Void
    let onRestore: () -> Void
    let onDelete: () -> Void

    var body: some View {
        HStack {
            CircleButton(systemImage: "chevron.backward", action: onClose, label: "Back", prominent: true)
            Spacer()
            HStack(spacing: 8) {
                CircleButton(systemImage: "info.circle", action: onInfo, label: "Info")
                CircleButton(systemImage: "square.and.arrow.up", action: onShare, label: "Share", loading: preparingShare)
                if inTrash {
                    CircleButton(systemImage: "arrow.uturn.backward.circle", action: onRestore, label: "Restore", loading: restoring)
                }
                CircleButton(
                    systemImage: inTrash ? "trash.slash" : "trash",
                    action: onDelete,
                    label: inTrash ? "Delete permanently" : "Move to trash",
                    loading: deleting,
                    destructive: true,
                )
            }
        }
        .padding(.top, 12)
    }
}

private struct CircleButton: View {
    let systemImage: String
    let action: () -> Void
    let label: String
    var loading: Bool = false
    var destructive: Bool = false
    var prominent: Bool = false

    var body: some View {
        Button(action: action) {
            ZStack {
                if loading {
                    ProgressView().controlSize(.small).tint(.white)
                } else {
                    Image(systemName: systemImage)
                        .font(prominent ? .title3.weight(.semibold) : .body.weight(.medium))
                        .foregroundStyle(destructive ? .red : .white)
                }
            }
            .frame(width: 44, height: 44)
            .background(.black.opacity(prominent ? 0.45 : 0.4), in: .circle)
        }
        .accessibilityLabel(label)
        .disabled(loading)
    }
}

private struct Footer: View {
    let item: Media
    let index: Int
    let total: Int

    var body: some View {
        VStack(spacing: 4) {
            Text(item.filename)
                .lineLimit(1)
                .font(.callout.weight(.medium))
                .foregroundStyle(.white)
            if let meta = metadataLine {
                Text(meta)
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.7))
            }
            Text("\(index + 1) / \(total)")
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.45))
                .tracking(2)
                .textCase(.uppercase)
        }
        .padding(.horizontal, 16).padding(.vertical, 10)
        .background(LinearGradient(colors: [.clear, .black.opacity(0.55)], startPoint: .top, endPoint: .bottom))
    }

    private var metadataLine: String? {
        var parts: [String] = []
        if let date = item.dateTaken, let d = DetailFormatters.iso.date(from: date) ?? DetailFormatters.loose.date(from: date) {
            parts.append(DetailFormatters.footerDate.string(from: d))
        }
        if let camera = item.cameraModel, !camera.isEmpty { parts.append(camera) }
        if let w = item.width, let h = item.height, w > 0 && h > 0 {
            parts.append("\(w)×\(h)")
        }
        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }
}

private enum DetailFormatters {
    static let iso = ISO8601DateFormatter()
    static let loose: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter
    }()
    static let footerDate: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d, yyyy"
        return formatter
    }()
}

// MARK: - Share sheet bridges

#if os(iOS)
import UIKit
private struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }
    func updateUIViewController(_ vc: UIActivityViewController, context: Context) {}
}
#else
import AppKit
private struct ShareSheet: View {
    let items: [Any]
    var body: some View {
        VStack(spacing: 12) {
            Text("Share").font(.headline)
            ForEach(items.indices, id: \.self) { idx in
                if let url = items[idx] as? URL {
                    Link(url.absoluteString, destination: url)
                        .lineLimit(1)
                }
            }
            Button("Copy URL") {
                if let url = items.first as? URL {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(url.absoluteString, forType: .string)
                }
            }
        }
        .padding(20)
    }
}
#endif
