import SwiftUI

/// Library statistics: total counts, type distribution, and per-camera
/// breakdown. Backed by `GET /api/stats` (one request, cached).
struct StatsView: View {
    @State private var stats: LibraryStats?
    @State private var loading = false
    @State private var error: String?

    private let repo = StatsRepository.shared

    var body: some View {
        Group {
            if let stats {
                content(stats: stats)
            } else if loading {
                ProgressView().controlSize(.large)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let error {
                EmptyState(
                    systemImage: "exclamationmark.triangle",
                    title: "Couldn’t load stats",
                    message: error,
                    actionLabel: "Retry",
                    action: { Task { await load() } },
                )
            }
        }
        .navigationTitle("Stats")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { Task { await load() } } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .disabled(loading)
            }
        }
        .task { if stats == nil { await load() } }
    }

    @ViewBuilder
    private func content(stats: LibraryStats) -> some View {
        List {
            Section("Overview") {
                LabeledContent("Total files") { Text("\(stats.totalFiles)").monospacedDigit() }
                LabeledContent("Total size") { Text(humanSize(stats.totalSize)) }
            }
            Section("By type") {
                TypeBar(label: "Photos", count: stats.typeDistribution.photo, total: stats.totalFiles, color: .blue)
                TypeBar(label: "Videos", count: stats.typeDistribution.video, total: stats.totalFiles, color: .orange)
                if stats.typeDistribution.audio > 0 {
                    TypeBar(label: "Audio", count: stats.typeDistribution.audio, total: stats.totalFiles, color: .purple)
                }
            }
            if !stats.cameras.isEmpty {
                Section("Top cameras") {
                    let maxCount = stats.cameras.map(\.count).max() ?? 1
                    ForEach(stats.cameras.prefix(20)) { cam in
                        CameraRow(camera: cam, maxCount: maxCount)
                    }
                }
            }
            if !stats.tags.isEmpty {
                Section("Top tags") {
                    ForEach(stats.tags.prefix(20), id: \.name) { tag in
                        LabeledContent(tag.name) {
                            Text("\(tag.count)").monospacedDigit().foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
    }

    private func load() async {
        loading = true
        defer { loading = false }
        error = nil
        do {
            stats = try await repo.overview()
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func humanSize(_ bytes: Int) -> String {
        let f = ByteCountFormatter()
        f.allowedUnits = [.useAll]
        f.countStyle = .file
        return f.string(fromByteCount: Int64(bytes))
    }
}

private struct TypeBar: View {
    let label: String
    let count: Int
    let total: Int
    let color: Color

    private var ratio: Double { total > 0 ? Double(count) / Double(total) : 0 }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(label)
                Spacer()
                Text("\(count)").monospacedDigit().foregroundStyle(.secondary)
            }
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(color.opacity(0.18)).frame(height: 6)
                    Capsule().fill(color).frame(width: geo.size.width * ratio, height: 6)
                }
            }
            .frame(height: 6)
        }
        .padding(.vertical, 2)
    }
}

private struct CameraRow: View {
    let camera: CameraStat
    let maxCount: Int

    private var ratio: Double { maxCount > 0 ? Double(camera.count) / Double(maxCount) : 0 }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(camera.displayName).lineLimit(1)
                Spacer()
                Text("\(camera.count)").monospacedDigit().foregroundStyle(.secondary)
            }
            GeometryReader { geo in
                Capsule().fill(.tint).frame(width: geo.size.width * ratio, height: 4)
            }
            .frame(height: 4)
        }
        .padding(.vertical, 2)
    }
}
